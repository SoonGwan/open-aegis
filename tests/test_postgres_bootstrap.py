"""Owned PostgreSQL native initialization, role privileges and first HTTP setup."""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from aegis import postgres_transfer as transfer,postgres_backups as backups
from aegis.app import create_app
from aegis.audit import GENESIS
from aegis.maintenance import WorkspaceBusy
from aegis.postgres_bootstrap import initialize
from aegis.postgres_store import PostgresStore
from tests.test_postgres_transfer import postgres,schema
from tests.test_validation import lab,register,task


def absent(postgres,name):
    with transfer.connect(postgres['dsn']) as db:
        assert db.execute('SELECT 1 FROM pg_namespace WHERE nspname=%s',(name,)).fetchone() is None


def test_fresh_native_schema_needs_no_sqlite_preserves_genesis_and_sequences(postgres,tmp_path):
    name=schema();result=initialize(postgres['dsn'],name);store=PostgresStore(postgres['dsn'],name)
    assert result['created'] and not result['service_started'] and result['users']==result['sessions']==0
    assert store.users()==[] and store.audit_integrity()==result['audit']
    checkpoint=result['audit']['checkpoint'];assert checkpoint['seq']==0 and checkpoint['hash']==GENESIS
    store.put('notes',{'id':'first','title':'First native write'});store.event(None,'First native event')
    with store.read_transaction() as db:
        assert db.execute('SELECT rowid FROM records').fetchone()['rowid']==1
    assert store.events()[0]['seq']==1 and store.audit_integrity(checkpoint)['valid']
    output=tmp_path/'fresh.zip';backups.backup(postgres['dsn'],name,output)
    target=schema();backups.restore(output,postgres['dsn'],target)
    assert PostgresStore(postgres['dsn'],target).get('notes','first')['title']=='First native write'
    assert not list(tmp_path.rglob('*.db'))


def test_native_remote_first_setup_token_duplicate_init_and_authenticated_pending_plan(postgres,tmp_path,monkeypatch,lab):
    name=schema();initialize(postgres['dsn'],name)
    monkeypatch.setenv('AEGIS_STORAGE_BACKEND','postgres');monkeypatch.setenv('AEGIS_POSTGRES_DSN',postgres['dsn']);monkeypatch.setenv('AEGIS_POSTGRES_SCHEMA',name)
    monkeypatch.setenv('AEGIS_SETUP_TOKEN','owned-native-setup-token')
    folder=tmp_path/'unused';url,handler=lab;app=create_app(folder,allow_private=True)
    with TestClient(app,client=('198.51.100.27',3210)) as client:
        assert client.get('/api/auth/status').json()['setup_required']
        assert client.get('/api/assets').status_code==401
        assert client.post('/api/auth/setup',json={'password':'owned-bootstrap-password'}).status_code==403
        assert app.state.store.users()==[] and app.state.store.audit_integrity()['events']==0
        assert client.post('/api/auth/setup',json={'password':'owned-bootstrap-password','setup_token':'owned-native-setup-token'}).status_code==200
        assert client.post('/api/auth/setup',json={'password':'owned-bootstrap-password','setup_token':'owned-native-setup-token'}).status_code==409
        before=app.state.store.audit_integrity()
        with pytest.raises(WorkspaceBusy):initialize(postgres['dsn'],name)
        assert app.state.store.audit_integrity()==before
        asset=register(client,url);pending=task(client,asset,['security_headers'])
        assert pending['status']=='pending' and handler.requests==[]
        assert client.get('/api/settings').json()['storage']=='postgres'
        assert app.state.store.audit_integrity()['valid'];cookie=client.cookies.get('aegis_session')
    with TestClient(create_app(folder,allow_private=True)) as restarted:
        restarted.cookies.set('aegis_session',cookie)
        assert restarted.get('/api/auth/status').json()['authenticated']
        assert restarted.app.state.store.get('tasks',pending['id'])['status']=='pending' and handler.requests==[]
    assert not folder.exists()


def test_existing_native_workspace_is_never_modified_and_parallel_initializers_have_one_winner(postgres):
    import psycopg
    name=schema()
    def create():
        try:return initialize(postgres['dsn'],name)
        except (WorkspaceBusy,psycopg.errors.DuplicateSchema):return 'refused'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:create(),range(2)))
    assert sum(isinstance(row,dict) for row in results)==1 and results.count('refused')==1
    store=PostgresStore(postgres['dsn'],name);store.put('notes',{'id':'keep','title':'Never replace'})
    before=store.audit_integrity()
    with pytest.raises(psycopg.errors.DuplicateSchema):initialize(postgres['dsn'],name)
    assert store.get('notes','keep')['title']=='Never replace' and store.audit_integrity()==before


@pytest.mark.parametrize('stage',['ddl','audit','manifest'])
def test_initialization_failure_rolls_back_schema_tables_and_sequences_and_can_retry(postgres,monkeypatch,stage):
    import psycopg
    name=schema()
    with monkeypatch.context() as patch:
        if stage=='ddl':patch.setattr(transfer,'DDL',(*transfer.DDL,'CREATE TABLE deliberately_bad ('))
        else:
            def fail(*args,**kwargs):raise RuntimeError('Owned '+stage+' verification failure')
            patch.setattr(transfer,'validate_postgres' if stage=='audit' else 'postgres_manifest',fail)
        with pytest.raises((RuntimeError,psycopg.Error)):initialize(postgres['dsn'],name)
    absent(postgres,name)
    assert initialize(postgres['dsn'],name)['created']


def test_nonsuperuser_with_database_create_can_initialize_and_run_native_http(postgres,tmp_path,monkeypatch):
    _,sql,_=transfer.driver();role=schema();name=schema()
    with transfer.connect(postgres['dsn']) as admin:
        admin.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT').format(sql.Identifier(role)))
        admin.execute(sql.SQL('GRANT CONNECT,CREATE ON DATABASE postgres TO {}').format(sql.Identifier(role)))
    dsn=postgres['dsn']+' user='+role;result=initialize(dsn,name)
    with transfer.connect(dsn) as db:
        row=db.execute('SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user').fetchone()
        assert row=={'rolsuper':False,'rolcreatedb':False,'rolcreaterole':False}
        assert db.execute('SELECT pg_get_userbyid(nspowner) AS owner FROM pg_namespace WHERE nspname=%s',(name,)).fetchone()['owner']==role
    with transfer.connect(postgres['dsn']) as admin:
        admin.execute(sql.SQL('REVOKE CREATE ON DATABASE postgres FROM {}').format(sql.Identifier(role)))
    monkeypatch.setenv('AEGIS_STORAGE_BACKEND','postgres');monkeypatch.setenv('AEGIS_POSTGRES_DSN',dsn);monkeypatch.setenv('AEGIS_POSTGRES_SCHEMA',name)
    monkeypatch.setenv('AEGIS_SETUP_TOKEN','')
    with TestClient(create_app(tmp_path/'unused-role')) as client:
        assert client.post('/api/auth/setup',json={'password':'owned-role-setup-password'}).status_code==200
        assert client.post('/api/notes',json={'title':'Ordinary role write','content':'Native'}).status_code==200
        assert client.post('/api/audit/verify',json={}).json()['status']=='verified'
        assert client.app.state.store.audit_integrity(result['audit']['checkpoint'])['valid']
    assert not (tmp_path/'unused-role').exists()


def test_role_without_database_create_never_leaves_objects(postgres):
    import psycopg
    _,sql,_=transfer.driver();role=schema();name=schema()
    with transfer.connect(postgres['dsn']) as admin:
        admin.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT').format(sql.Identifier(role)))
        admin.execute(sql.SQL('REVOKE CREATE ON DATABASE postgres FROM {}').format(sql.Identifier(role)))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):initialize(postgres['dsn']+' user='+role,name)
    absent(postgres,name)


def test_real_initialization_cli_env_default_explicit_override_and_failure_redaction(postgres,tmp_path):
    env={**os.environ,'AEGIS_POSTGRES_DSN':postgres['dsn'],'AEGIS_POSTGRES_SCHEMA':schema(),'AEGIS_DATA_DIR':str(tmp_path/'unused')}
    def run(*args,environment=env):
        return subprocess.run([sys.executable,'-m','aegis.cli.init_postgres',*args],env=environment,capture_output=True,text=True,timeout=30)
    created=run();assert created.returncode==0,created.stderr
    assert json.loads(created.stdout)['schema']==env['AEGIS_POSTGRES_SCHEMA']
    other=schema();assert json.loads(run('--schema',other).stdout)['schema']==other
    for environment,args in [(env,()),(env,('--schema','public')),({**env,'AEGIS_POSTGRES_SCHEMA':''},()),({**env,'AEGIS_POSTGRES_DSN':'postgresql://bootstrap-secret-user:bootstrap-secret-password@127.0.0.1:1/db'},('--schema',schema()))]:
        failed=run(*args,environment=environment)
        assert failed.returncode==2 and 'Traceback' not in failed.stderr
        assert 'bootstrap-secret-user' not in failed.stderr+failed.stdout and 'bootstrap-secret-password' not in failed.stderr+failed.stdout
    assert not (tmp_path/'unused').exists()
