"""Actual disposable PostgreSQL tests: opt in with AEGIS_TEST_POSTGRES=1."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import uuid

import pytest
from aegis import postgres_transfer as transfer
from aegis.auth import new_user
from aegis.backups import InvalidBackup,validate_backup
from aegis.maintenance import WorkspaceBusy,WorkspaceLease
from aegis.store import Store


@pytest.mark.parametrize('name',['public','pg_catalog','information_schema','aegis;drop table users','X','a'*64,'a-b',''])
def test_reserved_or_unsafe_postgres_schema_is_refused(name):
    with pytest.raises(transfer.TransferError):transfer.validate_schema(name)


@pytest.fixture(scope='module')
def postgres():
    if os.environ.get('AEGIS_TEST_POSTGRES')!='1':pytest.skip('Owned PostgreSQL rehearsal requires explicit opt-in')
    psycopg=pytest.importorskip('psycopg')
    binaries={name:shutil.which(name) for name in ('initdb','pg_ctl','createdb','pg_dump','pg_restore')}
    if not all(binaries.values()):pytest.fail('PostgreSQL client/server binaries are required for opted-in rehearsal')
    with tempfile.TemporaryDirectory(prefix='aegis-pg-',dir='/tmp') as temporary:
        root=Path(temporary);data=root/'cluster';socket=root/'socket';socket.mkdir(mode=0o700)
        subprocess.run([binaries['initdb'],'-D',str(data),'--auth=trust','--no-locale','--encoding=UTF8'],check=True,capture_output=True)
        subprocess.run([binaries['pg_ctl'],'-D',str(data),'-l',str(root/'server.log'),'-o',f"-c listen_addresses='' -k {socket} -p 55439",'-w','start'],check=True,capture_output=True)
        try:
            yield {'dsn':f'host={socket} port=55439 dbname=postgres','root':root,'binaries':binaries}
        finally:
            subprocess.run([binaries['pg_ctl'],'-D',str(data),'-w','-m','fast','stop'],check=True,capture_output=True)


@pytest.fixture
def source(tmp_path):
    store=Store(tmp_path/'source'/'aegis.db')
    user=new_user('admin','합성 관리자','admin','owned-migration-password')
    store.add_user(user);store.session('owned-old-cookie',9_999_999_999,user['id'])
    store.put('notes',{'id':'one','title':'한글\n引号 " \\ 🚀','price':'0.000000000000001'})
    store.put('notes',{'id':'deleted','title':'gap'})
    with store.connect() as db:db.execute("DELETE FROM records WHERE kind='notes' AND id='deleted'")
    store.put('tasks',{'id':'owned-task','status':'completed'})
    store.event('owned-task','합성 이벤트',detail={'exact':'0.000000000000001','unicode':'한글 🚀'})
    with store.connect() as db:
        db.execute("INSERT INTO records VALUES ('llm_calls','raw',?)",('{ "id": "raw", "state": "uncommitted", "large": 9007199254740991 }',))
        db.execute("UPDATE sqlite_sequence SET seq=100 WHERE name='events'")
    return store


def schema():return 'aegis_'+uuid.uuid4().hex[:16]


def test_actual_roundtrip_revokes_sessions_preserves_exact_rows_audit_and_sequence(postgres,source,tmp_path):
    name=schema();before=source.path.read_bytes()
    result=transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    assert result['sessions_revoked']==1 and not result['service_backend_enabled']
    assert source.path.read_bytes()==before and source.valid_session('owned-old-cookie')
    output=tmp_path/'returned'/'aegis.db'
    reverse=transfer.postgres_to_sqlite(postgres['dsn'],name,output)
    assert result['manifest']==reverse['manifest'] and result['audit']==reverse['audit']
    assert output.stat().st_mode & 0o777==0o600
    restored=Store(output)
    assert restored.user(username='admin')==source.user(username='admin')
    assert not restored.valid_session('owned-old-cookie')
    assert restored.get('notes','one')==source.get('notes','one')
    restored.event('owned-task','복구 후 이벤트')
    assert restored.events()[-1]['seq']==101 and restored.audit_integrity()['valid']
    with pytest.raises(Exception):transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    assert transfer.postgres_to_sqlite(postgres['dsn'],name,tmp_path/'other'/'aegis.db')['manifest']==result['manifest']
    with pytest.raises(transfer.TransferError):transfer.postgres_to_sqlite(postgres['dsn'],name,output)


def test_invalid_source_live_workspace_or_active_tasks_never_create_schema(postgres,source):
    name=schema()
    with WorkspaceLease(source.path.parent),pytest.raises(WorkspaceBusy):
        transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    source.patch('tasks','owned-task',status='running')
    with pytest.raises(transfer.TransferError,match='작업'):transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    source.patch('tasks','owned-task',status='completed')
    with source.connect() as db:db.execute('UPDATE events SET message=?',('tampered',))
    with pytest.raises(InvalidBackup):transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    with transfer.connect(postgres['dsn']) as db:
        assert db.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s',(name,)).fetchone() is None


def test_postgres_failure_rolls_back_schema_and_export_tamper_never_publishes(postgres,source,tmp_path):
    name=schema();source.put('notes',{'id':'bad','title':'literal'})
    # PostgreSQL TEXT cannot represent a literal NUL; SQLite can. Preserve, never silently strip.
    with source.connect() as db:db.execute("UPDATE records SET data=? WHERE id='bad'",('{"id":"bad","text":}',))
    # JSON invalidity is refused before opening PostgreSQL.
    with pytest.raises(InvalidBackup):transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    with source.connect() as db:
        db.execute("DELETE FROM records WHERE kind='notes' AND id='bad'")
        db.execute("UPDATE users SET name=?",('literal\0name',))
    import psycopg
    with pytest.raises(psycopg.Error):transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    with transfer.connect(postgres['dsn']) as db:
        assert db.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s',(name,)).fetchone() is None
    with source.connect() as db:db.execute("UPDATE users SET name=?",('합성 관리자',))
    from unittest.mock import patch
    with patch.object(transfer,'postgres_manifest',side_effect=RuntimeError('Owned final verification failure')):
        with pytest.raises(RuntimeError):transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    with transfer.connect(postgres['dsn']) as db:
        assert db.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s',(name,)).fetchone() is None
    transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    with transfer.connect(postgres['dsn']) as db:
        db.execute(f'UPDATE {name}.events SET message=%s',('tampered',))
    output=tmp_path/'refused'/'aegis.db'
    with pytest.raises(ValueError):transfer.postgres_to_sqlite(postgres['dsn'],name,output)
    assert not output.exists() and not list(output.parent.glob('.pg-transfer-*'))


def test_real_pg_dump_restore_then_sqlite_return_preserves_proofs(postgres,source,tmp_path):
    name=schema();expected=transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    dump=tmp_path/'owned.dump';environment={**os.environ,'PGHOST':str(postgres['root']/'socket'),'PGPORT':'55439'}
    with dump.open('xb') as file:
        subprocess.run([postgres['binaries']['pg_dump'],'--format=custom','--schema',name,'postgres'],env=environment,stdout=file,stderr=subprocess.PIPE,check=True)
    dump.chmod(0o600)
    database='restore_'+uuid.uuid4().hex[:12]
    subprocess.run([postgres['binaries']['createdb'],database],env=environment,check=True,capture_output=True)
    subprocess.run([postgres['binaries']['pg_restore'],'--exit-on-error','--dbname',database,str(dump)],env=environment,check=True,capture_output=True)
    dsn=postgres['dsn'].replace('dbname=postgres','dbname='+database)
    result=transfer.postgres_to_sqlite(dsn,name,tmp_path/'dump-return'/'aegis.db')
    assert result['manifest']==expected['manifest'] and result['audit']==expected['audit']
    validate_backup(tmp_path/'dump-return'/'aegis.db')


def test_cli_connection_failure_does_not_echo_credentials(tmp_path):
    environment={**os.environ,'AEGIS_POSTGRES_DSN':'postgresql://private-user:never-echo-this@127.0.0.1:1/db'}
    import sys
    result=subprocess.run([sys.executable,'-m','aegis.cli.transfer','postgres-to-sqlite','--schema','owned','--output',str(tmp_path/'result.db')],env=environment,capture_output=True,text=True)
    assert result.returncode==1 and '전송에 실패' in result.stderr
    assert 'never-echo-this' not in result.stderr+result.stdout and 'private-user' not in result.stderr+result.stdout
    assert not (tmp_path/'result.db').exists()


def test_reserved_sql_identifier_is_quoted_in_all_transfer_statements(postgres,source,tmp_path):
    result=transfer.sqlite_to_postgres(source.path,postgres['dsn'],'select')
    reverse=transfer.postgres_to_sqlite(postgres['dsn'],'select',tmp_path/'reserved'/'aegis.db')
    assert result['manifest']==reverse['manifest']


def test_reverse_final_verification_failure_removes_stage_without_publication(postgres,source,tmp_path,monkeypatch):
    name=schema();transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    monkeypatch.setattr(transfer,'sqlite_manifest',lambda db:{'owned_forced_mismatch':True})
    output=tmp_path/'stage-failure'/'aegis.db'
    with pytest.raises(transfer.TransferError,match='검증'):
        transfer.postgres_to_sqlite(postgres['dsn'],name,output)
    assert not output.exists() and not list(output.parent.glob('.pg-transfer-*'))


def test_reverse_read_snapshot_is_consistent_across_concurrent_record_edit(postgres,source,tmp_path,monkeypatch):
    name=schema();expected=transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    original=transfer.postgres_manifest
    def after_manifest(db):
        manifest=original(db)
        with transfer.connect(postgres['dsn']) as writer:
            writer.execute(f'UPDATE {name}.records SET data=%s WHERE kind=%s AND id=%s',
                           (json.dumps({'id':'one','title':'later concurrent edit'}),'notes','one'))
        return manifest
    monkeypatch.setattr(transfer,'postgres_manifest',after_manifest)
    output=tmp_path/'consistent'/'aegis.db'
    returned=transfer.postgres_to_sqlite(postgres['dsn'],name,output)
    assert returned['manifest']==expected['manifest']
    assert Store(output).get('notes','one')==source.get('notes','one')


def test_read_transaction_exit_failure_never_publishes_sqlite(postgres,source,tmp_path,monkeypatch):
    from contextlib import contextmanager
    name=schema();transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    original=transfer.connect
    class ExitFailure:
        def __init__(self,connection):self.connection=connection
        def __enter__(self):self.connection.__enter__();return self
        def __exit__(self,*args):return self.connection.__exit__(*args)
        def __getattr__(self,name):return getattr(self.connection,name)
        @contextmanager
        def transaction(self):
            with self.connection.transaction():yield
            raise RuntimeError('Owned read transaction exit acknowledgement failure')
    monkeypatch.setattr(transfer,'connect',lambda dsn:ExitFailure(original(dsn)))
    output=tmp_path/'exit-failure'/'aegis.db'
    with pytest.raises(RuntimeError,match='acknowledgement'):
        transfer.postgres_to_sqlite(postgres['dsn'],name,output)
    assert not output.exists(), 'Output was published before read transaction exit succeeded'
    assert not list(output.parent.glob('.pg-transfer-*'))
