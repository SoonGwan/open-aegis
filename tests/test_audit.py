import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import pytest
from aegis.audit import AuditIntegrityError, initialize_chain
from aegis.store import Store
from aegis.backups import backup_database, validate_backup, restore_database, InvalidBackup


def test_chain_atomic_concurrent_and_external_prefix(tmp_path):
    path = tmp_path/'audit.db'
    stores = [Store(path) for _ in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i: stores[i%8].event(None,'감사 '+str(i),detail={'index':i}),range(80)))
    store = stores[0]
    result = store.audit_integrity()
    assert result['events'] == 80
    checkpoint = result['checkpoint']
    store.event('task','new event',detail={'한글':'value'})
    assert store.audit_integrity(checkpoint)['events'] == 81
    with store.connect() as db:
        db.execute("CREATE TRIGGER fail_hash BEFORE INSERT ON event_hashes BEGIN SELECT RAISE(ABORT,'hash failure'); END")
    with pytest.raises(sqlite3.IntegrityError,match='hash failure'):
        store.event(None,'must rollback')
    assert store.audit_integrity()['events'] == 81
    assert all(e['message'] != 'must rollback' for e in store.events())


@pytest.mark.parametrize('change',[
    "UPDATE events SET message='changed' WHERE seq=2",
    'DELETE FROM events WHERE seq=2',
    'DELETE FROM events WHERE seq=3',
    'DELETE FROM event_hashes WHERE seq=2',
    "INSERT INTO events(ts,message,detail) VALUES(0,'unsealed','{}')",
])
def test_tamper_delete_and_unsealed_append_detected(tmp_path,change):
    store = Store(tmp_path/'audit.db')
    for i in range(3): store.event(None,str(i))
    with sqlite3.connect(store.path) as db: db.execute(change)
    with pytest.raises(AuditIntegrityError): store.audit_integrity()
    with pytest.raises(InvalidBackup,match='감사'): validate_backup(store.path)


def test_rewritten_database_needs_external_checkpoint_and_migration_is_once(tmp_path):
    store = Store(tmp_path/'audit.db')
    store.event(None,'original')
    checkpoint = store.audit_integrity()['checkpoint']
    with sqlite3.connect(store.path) as db:
        db.execute('DROP TABLE event_hashes')
        db.execute('DROP TABLE audit_state')
        db.execute("UPDATE events SET message='forged'")
        initialize_chain(db)
    assert store.audit_integrity()['valid']
    with pytest.raises(AuditIntegrityError,match='ID'): store.audit_integrity(checkpoint)
    with sqlite3.connect(store.path) as db:
        db.execute('UPDATE audit_state SET chain_id=?', (checkpoint['chain_id'],))
    with pytest.raises(AuditIntegrityError,match='체크포인트'): store.audit_integrity(checkpoint)
    # Ordinary open never reseals a current-schema database.
    before = store.audit_integrity()['checkpoint']
    assert Store(store.path).audit_integrity()['checkpoint'] == before


def test_schema_one_sealing_backup_and_restore(tmp_path):
    path=tmp_path/'old.db'
    store=Store(path)
    store.event(None,'legacy')
    with sqlite3.connect(path) as db:
        db.execute('DROP TABLE event_hashes'); db.execute('DROP TABLE audit_state'); db.execute('PRAGMA user_version=1')
    migrated=Store(path)
    result=migrated.audit_integrity()
    assert result['events']==1 and result['sealed_legacy_until']==1
    backups=list(tmp_path.glob('old.db.pre-schema2-*.db'))
    assert len(backups)==1
    with sqlite3.connect(backups[0]) as db:
        assert db.execute('SELECT message FROM events').fetchone()[0] == 'legacy'
        assert db.execute("SELECT name FROM sqlite_master WHERE name='event_hashes'").fetchone() is None
    assert validate_backup(backups[0])['schema_version']==1
    output=tmp_path/'backup.db'
    assert backup_database(path,output)['schema_version']==2
    destination=tmp_path/'restored'/'aegis.db'
    restore_database(output,destination)
    assert Store(destination).audit_integrity(result['checkpoint'])['events']==1


def test_readonly_cli_checkpoint_export_and_compare(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    store=Store(tmp_path/'audit.db')
    store.event(None,'checkpoint fixture')
    checkpoint=tmp_path/'trusted.json'
    command=[sys.executable,str(root/'scripts/verify_audit.py'),'--source',str(store.path)]
    exported=subprocess.run([*command,'--output',str(checkpoint)],capture_output=True,text=True)
    assert exported.returncode==0,exported.stderr
    assert json.loads(exported.stdout)['events']==1
    original=checkpoint.read_bytes()
    assert checkpoint.stat().st_mode & 0o777 == 0o600
    store.event(None,'after checkpoint')
    compared=subprocess.run([*command,'--checkpoint',str(checkpoint)],capture_output=True,text=True)
    assert compared.returncode==0 and json.loads(compared.stdout)['events']==2
    overwrite=subprocess.run([*command,'--output',str(checkpoint)],capture_output=True,text=True)
    assert overwrite.returncode==2 and checkpoint.read_bytes()==original
    with sqlite3.connect(store.path) as db: db.execute("UPDATE events SET message='changed' WHERE seq=1")
    invalid=subprocess.run([*command,'--checkpoint',str(checkpoint)],capture_output=True,text=True)
    assert invalid.returncode==2 and 'seq=1' in invalid.stderr


@pytest.mark.parametrize('sequence', [0, -1])
def test_invalid_sequence_cannot_be_sealed_as_valid(tmp_path, sequence):
    store = Store(tmp_path/'audit.db')
    with sqlite3.connect(store.path) as db:
        db.execute('DROP TABLE event_hashes')
        db.execute('DROP TABLE audit_state')
        db.execute("INSERT INTO events(seq,ts,message,detail) VALUES (?,0,'invalid','{}')", (sequence,))
        with pytest.raises(AuditIntegrityError, match='seq'):
            initialize_chain(db)


@pytest.mark.parametrize('change', [
    "UPDATE audit_state SET chain_id=''",
    "UPDATE audit_state SET last_seq='invalid'",
    'UPDATE audit_state SET sealed_legacy_until=-1',
    'UPDATE audit_state SET sealed_legacy_until=99',
    "UPDATE events SET detail=x'ff' WHERE seq=1",
    "UPDATE events SET ts='invalid' WHERE seq=1",
])
def test_invalid_audit_data_is_a_controlled_rejection(tmp_path, change):
    store = Store(tmp_path/'audit.db')
    store.event(None, 'fixture')
    with sqlite3.connect(store.path) as db:
        db.execute(change)
    with pytest.raises(AuditIntegrityError):
        store.audit_integrity()
    with pytest.raises(InvalidBackup, match='감사'):
        validate_backup(store.path)


@pytest.mark.parametrize('change', [
    "UPDATE events SET message='tail tampered' WHERE seq=1",
    "UPDATE event_hashes SET previous_hash='bad' WHERE seq=1",
])
def test_append_refuses_corrupt_tail_without_creating_an_event(tmp_path, change):
    store = Store(tmp_path/'audit.db')
    store.event(None, 'fixture')
    with sqlite3.connect(store.path) as db:
        db.execute(change)
    with pytest.raises(AuditIntegrityError):
        store.event(None, 'must not append')
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 1
        assert db.execute('SELECT last_seq FROM audit_state').fetchone()[0] == 1


def test_invalid_legacy_migration_rolls_back_and_preserves_preflight_backup(tmp_path):
    path = tmp_path/'legacy.db'
    store = Store(path)
    store.put('notes', {'id':'preserved', 'title':'legacy fixture'})
    with sqlite3.connect(path) as db:
        db.execute('DROP TABLE event_hashes')
        db.execute('DROP TABLE audit_state')
        db.execute('PRAGMA user_version=1')
        db.execute("INSERT INTO events(seq,ts,message,detail) VALUES (0,0,'invalid legacy','{}')")
    with pytest.raises(AuditIntegrityError, match='seq'):
        Store(path)
    for preserved in [path, *tmp_path.glob('legacy.db.pre-schema2-*.db')]:
        with sqlite3.connect(preserved) as db:
            assert db.execute('PRAGMA user_version').fetchone()[0] == 1
            assert db.execute("SELECT name FROM sqlite_master WHERE name='audit_state'").fetchone() is None
            assert db.execute('SELECT seq FROM events').fetchone()[0] == 0
            assert db.execute('SELECT COUNT(*) FROM records').fetchone()[0] == 1
    assert len(list(tmp_path.glob('legacy.db.pre-schema2-*.db'))) == 1


def test_sealed_legacy_boundary_must_exist_but_sequence_gaps_are_valid(tmp_path):
    store = Store(tmp_path/'audit.db')
    with sqlite3.connect(store.path) as db:
        db.execute('DROP TABLE event_hashes')
        db.execute('DROP TABLE audit_state')
        for seq in (1, 3):
            db.execute("INSERT INTO events(seq,ts,message,detail) VALUES (?,0,'legacy gap','{}')", (seq,))
        initialize_chain(db)
    assert store.audit_integrity()['sealed_legacy_until'] == 3
    store.event(None, 'new')
    with sqlite3.connect(store.path) as db:
        db.execute('UPDATE audit_state SET sealed_legacy_until=2')
    with pytest.raises(AuditIntegrityError, match='봉인'):
        store.audit_integrity()


def test_malformed_payload_cli_rejects_without_export_or_traceback(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    store = Store(tmp_path/'audit.db')
    store.event(None, 'fixture')
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE events SET detail=x'ff' WHERE seq=1")
    output = tmp_path/'must-not-exist.json'
    result = subprocess.run([sys.executable, '-m', 'aegis.cli.audit', '--source', str(store.path),
                             '--output', str(output)], capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parents[1])
    assert result.returncode == 2 and 'seq=1' in result.stderr
    assert 'Traceback' not in result.stderr and not output.exists()
