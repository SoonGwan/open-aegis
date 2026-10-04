import json
import os
import sqlite3
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from aegis.audit import AuditIntegrityError, initialize_chain
from aegis.checkpoint_archive import capture_checkpoint, CheckpointArchiveError, filename
from aegis.store import Store


def test_archive_append_idempotent_private_and_prefix_comparison(tmp_path):
    store = Store(tmp_path/'source.db')
    destination = tmp_path/'independent'
    store.event(None, 'DO-NOT-EXPOSE', detail={'token':'SECRET'})
    first = capture_checkpoint(store.audit_integrity, destination)
    original = (destination/filename(first['checkpoint'])).read_bytes()
    assert first['created'] is True and first['events'] == 1
    assert 'DO-NOT-EXPOSE' not in original.decode() and 'SECRET' not in original.decode()
    assert destination.stat().st_mode & 0o777 == 0o700
    assert (destination/filename(first['checkpoint'])).stat().st_mode & 0o777 == 0o600
    assert capture_checkpoint(store.audit_integrity, destination)['created'] is False
    store.event(None, 'next')
    second = capture_checkpoint(store.audit_integrity, destination)
    assert second['created'] is True and second['events'] == 2
    assert (destination/filename(first['checkpoint'])).read_bytes() == original
    assert len(list(destination.glob('checkpoint-*.json'))) == 2
    assert not list(destination.glob('.checkpoint-stage-*'))


def test_valid_rewrite_and_rollback_refused_against_archived_head(tmp_path):
    store = Store(tmp_path/'source.db')
    store.event(None, 'original')
    destination = tmp_path/'independent'
    checkpoint = capture_checkpoint(store.audit_integrity, destination)['checkpoint']
    before = {p.name:p.read_bytes() for p in destination.glob('checkpoint-*')}
    with sqlite3.connect(store.path) as db:
        db.execute('DROP TABLE event_hashes')
        db.execute('DROP TABLE audit_state')
        db.execute("UPDATE events SET message='forged'")
        initialize_chain(db)
        db.execute('UPDATE audit_state SET chain_id=?', (checkpoint['chain_id'],))
    assert store.audit_integrity()['valid']
    with pytest.raises(AuditIntegrityError): capture_checkpoint(store.audit_integrity, destination)
    assert {p.name:p.read_bytes() for p in destination.glob('checkpoint-*')} == before
    assert not list(destination.glob('.checkpoint-stage-*'))


def test_concurrent_capture_fails_without_wait_and_recovers(tmp_path):
    store = Store(tmp_path/'source.db')
    destination = tmp_path/'archive'
    entered, release = threading.Event(), threading.Event()
    def slow(previous):
        entered.set()
        assert release.wait(5)
        return store.audit_integrity(previous)
    with ThreadPoolExecutor(1) as executor:
        running = executor.submit(capture_checkpoint, slow, destination)
        try:
            assert entered.wait(5)
            with pytest.raises(CheckpointArchiveError, match='실행 중'):
                capture_checkpoint(store.audit_integrity, destination)
        finally:
            release.set()
        assert running.result()['created']
    assert capture_checkpoint(store.audit_integrity, destination)['created'] is False


@pytest.mark.parametrize('failure', ['verify', 'write', 'link'])
def test_failure_preserves_archive_and_releases_lock(tmp_path, monkeypatch, failure):
    store = Store(tmp_path/'source.db')
    destination = tmp_path/'archive'
    first = capture_checkpoint(store.audit_integrity, destination)
    before = {p.name:p.read_bytes() for p in destination.glob('checkpoint-*')}
    store.event(None, 'later')
    def broken(*args, **kwargs): raise OSError('controlled failure')
    with monkeypatch.context() as patch:
        verify = store.audit_integrity
        if failure == 'verify': verify = broken
        elif failure == 'write': patch.setattr(os, 'fsync', broken)
        else: patch.setattr(os, 'link', broken)
        with pytest.raises(OSError): capture_checkpoint(verify, destination)
    assert {p.name:p.read_bytes() for p in destination.glob('checkpoint-*')} == before
    assert not list(destination.glob('.checkpoint-stage-*'))
    assert capture_checkpoint(store.audit_integrity, destination)['created']


@pytest.mark.parametrize('change', ['symlink','oversize','mismatch','other_chain','branch'])
def test_archive_corruption_refused_without_source_or_archive_changes(tmp_path, change):
    store = Store(tmp_path/'source.db')
    store.event(None, 'event')
    destination = tmp_path/'archive'
    first = capture_checkpoint(store.audit_integrity, destination)
    path = destination/filename(first['checkpoint'])
    if change == 'symlink':
        copy = tmp_path/'copy.json'; copy.write_bytes(path.read_bytes())
        path.unlink(); path.symlink_to(copy)
    elif change == 'oversize': path.write_bytes(b' '*4097)
    elif change == 'mismatch': path.write_text('{}')
    else:
        checkpoint = {**first['checkpoint'], 'chain_id':'a'*32} if change == 'other_chain' else {**first['checkpoint'], 'hash':'f'*64}
        (destination/filename(checkpoint)).write_text(json.dumps(checkpoint))
    before = store.audit_integrity()
    with pytest.raises(CheckpointArchiveError): capture_checkpoint(store.audit_integrity, destination)
    assert store.audit_integrity() == before


def test_directory_symlink_refused(tmp_path):
    store = Store(tmp_path/'source.db')
    actual = tmp_path/'actual'; actual.mkdir()
    link = tmp_path/'link'; link.symlink_to(actual, target_is_directory=True)
    with pytest.raises(OSError): capture_checkpoint(store.audit_integrity, link)
    assert not list(actual.iterdir())


def test_actual_cli_repeated_capture_readonly_and_sanitized_failure(tmp_path):
    store = Store(tmp_path/'source.db'); store.event(None, 'SECRET-EVENT')
    destination = tmp_path/'archive'
    command = [sys.executable, '-m', 'aegis.cli.checkpoint', '--backend', 'sqlite', '--source', str(store.path), '--destination', str(destination)]
    before = store.audit_integrity()
    first = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert first.returncode == 0 and json.loads(first.stdout)['created'] is True
    second = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert second.returncode == 0 and json.loads(second.stdout)['created'] is False
    assert store.audit_integrity() == before
    with sqlite3.connect(store.path) as db: db.execute("UPDATE events SET message='TAMPER-SECRET'")
    failed = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert failed.returncode == 2 and 'seq=1' in failed.stderr
    assert 'SECRET' not in first.stdout+first.stderr+failed.stdout+failed.stderr
    assert len(list(destination.glob('checkpoint-*.json'))) == 1


def test_valid_truncated_chain_refused(tmp_path):
    store = Store(tmp_path/'source.db')
    store.event(None, 'first')
    destination = tmp_path/'archive'
    first = capture_checkpoint(store.audit_integrity, destination)['checkpoint']
    store.event(None, 'second')
    capture_checkpoint(store.audit_integrity, destination)
    with sqlite3.connect(store.path) as db:
        db.execute('DELETE FROM event_hashes WHERE seq>?', (first['seq'],))
        db.execute('DELETE FROM events WHERE seq>?', (first['seq'],))
        db.execute('UPDATE audit_state SET last_seq=?,head_hash=?', (first['seq'], first['hash']))
    assert store.audit_integrity()['valid']
    with pytest.raises(AuditIntegrityError): capture_checkpoint(store.audit_integrity, destination)
    assert len(list(destination.glob('checkpoint-*.json'))) == 2


def test_directory_fsync_failure_may_publish_complete_checkpoint(tmp_path, monkeypatch):
    store = Store(tmp_path/'source.db')
    destination = tmp_path/'archive'
    original = os.fsync
    import stat
    def fail_directory(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode): raise OSError('controlled directory sync failure')
        return original(fd)
    with monkeypatch.context() as patch:
        patch.setattr(os, 'fsync', fail_directory)
        with pytest.raises(OSError): capture_checkpoint(store.audit_integrity, destination)
    assert len(list(destination.glob('checkpoint-*.json'))) == 1
    assert not list(destination.glob('.checkpoint-stage-*'))
    assert capture_checkpoint(store.audit_integrity, destination)['created'] is False


def test_stage_collision_never_deletes_an_existing_file(tmp_path, monkeypatch):
    from aegis import checkpoint_archive
    store = Store(tmp_path/'source.db')
    destination = tmp_path/'archive'; destination.mkdir()
    existing = destination/'.checkpoint-stage-controlled'; existing.write_bytes(b'preserve')
    monkeypatch.setattr(checkpoint_archive.secrets, 'token_hex', lambda n:'controlled')
    with pytest.raises(FileExistsError): capture_checkpoint(store.audit_integrity, destination)
    assert existing.read_bytes() == b'preserve'
    assert not list(destination.glob('checkpoint-*.json'))


def test_archive_capacity_never_prunes_and_allows_unchanged_verification(tmp_path, monkeypatch):
    from aegis import checkpoint_archive
    monkeypatch.setattr(checkpoint_archive, 'MAX_CHECKPOINTS', 2)
    store = Store(tmp_path/'source.db')
    destination = tmp_path/'archive'
    capture_checkpoint(store.audit_integrity, destination)
    store.event(None, 'one')
    capture_checkpoint(store.audit_integrity, destination)
    assert capture_checkpoint(store.audit_integrity, destination)['created'] is False
    before = {p.name:p.read_bytes() for p in destination.glob('checkpoint-*')}
    store.event(None, 'two')
    with pytest.raises(CheckpointArchiveError, match='한도'):
        capture_checkpoint(store.audit_integrity, destination)
    assert {p.name:p.read_bytes() for p in destination.glob('checkpoint-*')} == before
