"""Owned native PostgreSQL online archives and atomic fresh-schema recovery."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from aegis import postgres_backups as backups,postgres_transfer as transfer,call_ledger
from aegis.app import create_app
from aegis.maintenance import WorkspaceBusy
from aegis.postgres_store import PostgresStore
from tests.test_postgres_transfer import postgres,source,schema
from tests.test_validation import lab,register,task


@pytest.fixture
def native(postgres,source):
    name=schema();transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    return PostgresStore(postgres['dsn'],name)


def absent(postgres,name):
    with transfer.connect(postgres['dsn']) as db:
        assert db.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s',(name,)).fetchone() is None


def contents(path):
    with zipfile.ZipFile(path) as archive:return {name:archive.read(name) for name in archive.namelist()}


def rewrite(source,destination,change,rehash=False):
    frames=contents(source);change(frames)
    if rehash:
        metadata=json.loads(frames['metadata.json'])
        for table in transfer.TABLES:
            raw=frames[table+'.ndjson'];metadata['manifest'][table]={'rows':len(raw.splitlines()),'sha256':hashlib.sha256(raw).hexdigest()}
        frames['metadata.json']=backups.encoded(metadata)
    with zipfile.ZipFile(destination,'w') as archive:
        for name,raw in frames.items():archive.writestr(name,raw)


def test_online_archive_keeps_snapshot_and_source_cookie_while_owned_writes_continue(native,postgres,tmp_path,monkeypatch):
    user=native.user(username='admin');native.session('live-cookie',time.time()+300,user['id'])
    before=native.audit_integrity();original=transfer.validate_postgres
    with native.acquire_runtime():
        def append_after_snapshot(db,**kwargs):
            state,audit=original(db,**kwargs)
            native.put('notes',{'id':'one','title':'Concurrent later edit'})
            native.put('notes',{'id':'later','title':'Excluded from backup'})
            native.event(None,'Concurrent later event')
            return state,audit
        monkeypatch.setattr(transfer,'validate_postgres',append_after_snapshot)
        output=tmp_path/'online 한글.zip';result=backups.backup(postgres['dsn'],native.schema,output)
        assert native.valid_session('live-cookie') and native.get('notes','later')
        assert result['audit']==before and result['omitted_sessions']==1
    monkeypatch.setattr(transfer,'validate_postgres',original)
    assert output.stat().st_mode & 0o777==0o600 and backups.validate(output,before['checkpoint'])['audit']==before
    name=schema();backups.restore(output,postgres['dsn'],name,before['checkpoint']);restored=PostgresStore(postgres['dsn'],name)
    assert restored.get('notes','one')['price']=='0.000000000000001'
    assert restored.get('notes','later') is None and restored.audit_integrity()==before
    assert restored.user(username='admin')==user and not restored.valid_session('live-cookie')
    with pytest.raises(backups.BackupError):backups.backup(postgres['dsn'],native.schema,output)
    assert not list(tmp_path.glob('.pg-backup-*'))


def test_real_http_backup_and_restore_preserve_password_revoke_copy_and_never_resume_work(native,postgres,tmp_path,monkeypatch,lab):
    monkeypatch.setenv('AEGIS_STORAGE_BACKEND','postgres');monkeypatch.setenv('AEGIS_POSTGRES_DSN',postgres['dsn']);monkeypatch.setenv('AEGIS_POSTGRES_SCHEMA',native.schema)
    folder=tmp_path/'unused';app=create_app(folder,allow_private=True);url,handler=lab
    with TestClient(app) as live:
        assert live.post('/api/auth/login',json={'username':'admin','password':'owned-migration-password'}).status_code==200
        cookie=live.cookies.get('aegis_session');asset=register(live,url);pending=task(live,asset,['security_headers'])
        store=app.state.store;store.put('tasks',{'id':'unfinished','status':'running','checks':[],'scope_snapshot':[]})
        call=call_ledger.start(store,'planner','unfinished','owned','https://owned.invalid/',time.time(),{'status':'unconfigured','quote':None})
        output=tmp_path/'live.zip';metadata=backups.backup(postgres['dsn'],native.schema,output)
        name=schema();backups.restore(output,postgres['dsn'],name)
        assert live.get('/api/assets').status_code==200 and store.valid_session(cookie)
        monkeypatch.setenv('AEGIS_POSTGRES_SCHEMA',name)
        with TestClient(create_app(tmp_path/'unused-copy',allow_private=True)) as recovered:
            recovered.cookies.set('aegis_session',cookie);assert recovered.get('/api/assets').status_code==401
            assert recovered.post('/api/auth/login',json={'username':'admin','password':'owned-migration-password'}).status_code==200
            copy=recovered.app.state.store
            assert copy.get('tasks','unfinished')['status']=='interrupted'
            assert copy.get('llm_calls',call)['state']=='interrupted'
            assert copy.get('tasks',pending['id'])['status']=='pending'
            assert copy.audit_integrity(metadata['audit']['checkpoint'])['valid']
            assert handler.requests==[]
        assert store.get('tasks','unfinished')['status']=='running' and store.valid_session(cookie)
    assert not folder.exists() and not (tmp_path/'unused-copy').exists()


def test_identity_gaps_and_raw_records_survive_native_restore(native,postgres,tmp_path):
    with native.write_transaction() as db:
        db.execute("SELECT setval(pg_get_serial_sequence('records','rowid'),1000,true)")
        db.execute("SELECT setval(pg_get_serial_sequence('events','seq'),2000,true)")
    with native.read_transaction() as db:expected=transfer.postgres_manifest(db)
    output=tmp_path/'gaps.zip';metadata=backups.backup(postgres['dsn'],native.schema,output)
    assert metadata['record_sequence']==1000 and metadata['event_sequence']==2000
    name=schema();backups.restore(output,postgres['dsn'],name);restored=PostgresStore(postgres['dsn'],name)
    with restored.read_transaction() as db:assert transfer.postgres_manifest(db)==expected
    restored.put('notes',{'id':'after','title':'Preserve allocation gap'});restored.event(None,'After recovery')
    with restored.read_transaction() as db:
        assert db.execute("SELECT rowid FROM records WHERE kind='notes' AND id='after'").fetchone()['rowid']==1001
    assert restored.events()[-1]['seq']==2001 and restored.audit_integrity()['valid']


def test_existing_schema_and_live_owner_are_refused_without_changes(native,postgres,tmp_path):
    import psycopg
    output=tmp_path/'backup.zip';backups.backup(postgres['dsn'],native.schema,output)
    with native.read_transaction() as db:expected=transfer.postgres_manifest(db)
    with pytest.raises(psycopg.errors.DuplicateSchema):backups.restore(output,postgres['dsn'],native.schema)
    with native.acquire_runtime(),pytest.raises(WorkspaceBusy):backups.restore(output,postgres['dsn'],native.schema)
    fresh=PostgresStore(postgres['dsn'],native.schema)
    with fresh.read_transaction() as db:assert transfer.postgres_manifest(db)==expected


def test_post_copy_verification_failure_rolls_back_every_new_object(native,postgres,tmp_path,monkeypatch):
    output=tmp_path/'backup.zip';backups.backup(postgres['dsn'],native.schema,output);name=schema()
    def fail(*args,**kwargs):raise backups.BackupError('Owned post-COPY verification failure')
    monkeypatch.setattr(transfer,'validate_postgres',fail)
    with pytest.raises(backups.BackupError,match='post-COPY'):backups.restore(output,postgres['dsn'],name)
    absent(postgres,name)


@pytest.mark.parametrize('mutation',['frame','audit','missing','extra','sequence','type','json','oversize','metadata','encoding'])
def test_damaged_archives_fail_validation_before_any_schema_is_created(native,postgres,tmp_path,mutation):
    output=tmp_path/'backup.zip';backups.backup(postgres['dsn'],native.schema,output);bad=tmp_path/'bad.zip'
    def change(frames):
        if mutation=='frame':frames['records.ndjson']=frames['records.ndjson'].replace(b'raw',b'RAW',1)
        elif mutation=='audit':
            rows=[json.loads(row) for row in frames['events.ndjson'].splitlines()];rows[0][4]='changed';frames['events.ndjson']=b''.join(backups.encoded(row) for row in rows)
        elif mutation=='missing':frames.pop('users.ndjson')
        elif mutation=='extra':frames['execute.sql']=b'DROP SCHEMA public CASCADE;'
        elif mutation=='sequence':
            metadata=json.loads(frames['metadata.json']);metadata['event_sequence']=0;frames['metadata.json']=backups.encoded(metadata)
        elif mutation in ('type','json'):
            rows=[json.loads(row) for row in frames['records.ndjson'].splitlines()];rows[0][0 if mutation=='type' else 3]=True if mutation=='type' else '{bad';frames['records.ndjson']=b''.join(backups.encoded(row) for row in rows)
        elif mutation=='oversize':frames['records.ndjson']=b'x'*(backups.MAX_ROW_BYTES+1)+b'\n'
        elif mutation=='metadata':frames['metadata.json']=b'x'*(backups.MAX_METADATA_BYTES+1)
        elif mutation=='encoding':frames['users.ndjson']=frames['users.ndjson'].replace(b',',b', ',1)
    rewrite(output,bad,change,rehash=mutation in ('audit','type','json','oversize','encoding'))
    with pytest.raises(ValueError):backups.validate(bad)
    name=schema()
    with pytest.raises(ValueError):backups.restore(bad,postgres['dsn'],name)
    absent(postgres,name)


@pytest.mark.parametrize('compressed',[False,True])
def test_duplicate_or_compressed_zip_members_are_refused(native,postgres,tmp_path,compressed):
    output=tmp_path/'backup.zip';backups.backup(postgres['dsn'],native.schema,output);frames=contents(output);bad=tmp_path/'bad.zip'
    with zipfile.ZipFile(bad,'w',compression=zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED) as archive:
        for name,raw in frames.items():archive.writestr(name,raw)
        if not compressed:
            with pytest.warns(UserWarning):archive.writestr('metadata.json',frames['metadata.json'])
    with pytest.raises(backups.BackupError):backups.validate(bad)


def test_external_checkpoint_mismatch_and_non_zip_refused_before_connection(native,postgres,tmp_path,monkeypatch):
    output=tmp_path/'backup.zip';metadata=backups.backup(postgres['dsn'],native.schema,output)
    def denied(_):raise AssertionError('Invalid input opened target DB')
    monkeypatch.setattr(transfer,'connect',denied)
    checkpoint={**metadata['audit']['checkpoint'],'hash':'f'*64}
    with pytest.raises(ValueError,match='체크포인트'):backups.restore(output,postgres['dsn'],schema(),checkpoint)
    output.write_text('not a ZIP archive')
    with pytest.raises(backups.BackupError):backups.restore(output,postgres['dsn'],schema())


def test_two_concurrent_publishers_never_overwrite_and_remove_stages(native,postgres,tmp_path,monkeypatch):
    barrier=threading.Barrier(2);original=os.link
    def publish(source,destination):barrier.wait(timeout=10);return original(source,destination)
    monkeypatch.setattr(backups.os,'link',publish);output=tmp_path/'race.zip'
    def make():
        try:return backups.backup(postgres['dsn'],native.schema,output)
        except FileExistsError:return 'refused'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:make(),range(2)))
    assert sum(isinstance(row,dict) for row in results)==1 and results.count('refused')==1
    assert backups.validate(output)['audit']==native.audit_integrity() and not list(tmp_path.glob('.pg-backup-*'))


def test_read_transaction_exit_failure_never_publishes(native,postgres,tmp_path,monkeypatch):
    original=transfer.connect
    class ExitFailure:
        def __init__(self,db):self.db=db
        def __enter__(self):self.db.__enter__();return self
        def __exit__(self,*args):return self.db.__exit__(*args)
        def __getattr__(self,key):return getattr(self.db,key)
        @contextmanager
        def transaction(self):
            with self.db.transaction():yield
            raise RuntimeError('Owned exit acknowledgement failure')
    monkeypatch.setattr(transfer,'connect',lambda dsn:ExitFailure(original(dsn)));output=tmp_path/'refused.zip'
    with pytest.raises(RuntimeError,match='acknowledgement'):backups.backup(postgres['dsn'],native.schema,output)
    assert not output.exists() and not list(tmp_path.glob('.pg-backup-*'))


def test_real_cli_configuration_archive_check_and_credentials_are_sanitized(native,postgres,tmp_path):
    env={**os.environ,'AEGIS_STORAGE_BACKEND':'postgres','AEGIS_POSTGRES_DSN':postgres['dsn'],'AEGIS_POSTGRES_SCHEMA':native.schema,'AEGIS_DATA_DIR':str(tmp_path/'unused')}
    def run(module,*args,environment=env):return subprocess.run([sys.executable,'-m','aegis.cli.'+module,*map(str,args)],env=environment,capture_output=True,text=True,timeout=30)
    output=tmp_path/'cli.zip';result=run('backup','--output',output);assert result.returncode==0,result.stderr
    metadata=json.loads(result.stdout);checkpoint=tmp_path/'checkpoint.json';checkpoint.write_text(json.dumps(metadata['audit']['checkpoint']))
    no_db={**env,'AEGIS_POSTGRES_DSN':'postgresql://secret-user:secret-value@127.0.0.1:1/db'}
    checked=run('restore','--source',output,'--check-only','--checkpoint',checkpoint,environment=no_db)
    assert checked.returncode==0 and json.loads(checked.stdout)['manifest']==metadata['manifest']
    name=schema();restored=run('restore','--source',output,'--schema',name,'--checkpoint',checkpoint)
    assert restored.returncode==0,restored.stderr
    assert PostgresStore(postgres['dsn'],name).get('notes','one')==native.get('notes','one')
    for module,args,environment in [('backup',['--output',tmp_path/'fail.zip'],no_db),('backup',['--source','should-not-read','--output',tmp_path/'fail.zip'],env),('restore',['--source',output,'--schema',schema()],no_db),('restore',['--source',output,'--destination',tmp_path/'no.db'],env),('restore',['--source',output,'--schema',native.schema],env)]:
        failed=run(module,*args,environment=environment)
        assert failed.returncode==2 and 'Traceback' not in failed.stderr
        assert 'secret-user' not in failed.stderr+failed.stdout and 'secret-value' not in failed.stderr+failed.stdout
    assert not (tmp_path/'unused').exists() and not (tmp_path/'fail.zip').exists() and not (tmp_path/'no.db').exists()
