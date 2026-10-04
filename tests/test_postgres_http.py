"""Actual HTTP app lifecycle on the configured native PostgreSQL backend."""
import json
import threading
import time

import pytest
from fastapi.testclient import TestClient
from aegis import app as application,postgres_transfer as transfer,call_ledger
from aegis.maintenance import WorkspaceBusy
from aegis.postgres_maintenance import PostgresLease
from aegis.store import Store
from tests.test_postgres_transfer import postgres,schema
from tests.test_validation import lab,register,task,finish
from tests.test_validation import (
    test_no_requests_before_approval_and_no_duplicate_execution as test_native_approval_and_conversation,
    test_retest_failing_before_passing_after_preserves_evidence as test_native_retest,
    test_server_error_does_not_falsely_resolve_finding as test_native_inconclusive_retest,
    test_authorization_rules_and_secret_redaction as test_native_policy_and_report_redaction,
    test_import_validation_is_atomic as test_native_asset_import_atomic,
    test_rejected_task_never_executes as test_native_rejected_task,
    test_record_assistant_is_grounded_and_sends_no_requests as test_native_grounded_rules_chat,
)


@pytest.fixture
def configured(postgres,tmp_path,monkeypatch):
    source=Store(tmp_path/'source'/'aegis.db');name=schema()
    transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    monkeypatch.setenv('AEGIS_STORAGE_BACKEND','postgres')
    monkeypatch.setenv('AEGIS_POSTGRES_DSN',postgres['dsn'])
    monkeypatch.setenv('AEGIS_POSTGRES_SCHEMA',name)
    return name,tmp_path/'unused-sqlite'


@pytest.fixture
def client(configured):
    _,folder=configured;app=application.create_app(folder,allow_private=True)
    with TestClient(app) as client:
        assert client.post('/api/auth/setup',json={'password':'aegis-test-password-only'}).status_code==200
        yield client
    assert not folder.exists() and app.state.store.owner.closed


def test_native_http_auth_settings_notes_assignees_roles_and_import(client):
    assert client.get('/api/settings').json()['storage']=='postgres'
    assert client.get('/api/health').json()['status']=='ok'
    assert client.get('/api/overview').status_code==200
    users=[]
    for role,name in [('operator','ÄBC'),('viewer','Viewer')]:
        response=client.post('/api/users',json={'username':role,'name':name,'role':role,'password':'owned-http-password'})
        assert response.status_code==200;users.append(response.json())
    assert client.post('/api/users',json={'username':'operator','name':'duplicate','role':'viewer','password':'owned-http-password'}).status_code==409
    assert client.get('/api/assignees',params={'search':'äbc'}).json()['total']==0
    assert client.get('/api/assignees',params={'search':'Äbc'}).json()['items'][0]['id']==users[0]['id']
    assert client.get('/api/assignees',params={'search':"' OR 1=1 --"}).json()['total']==0
    note=client.post('/api/notes',json={'title':'Owned note','content':'unchanged'}).json()
    assert client.delete('/api/notes/'+note['id']).status_code==200
    assert client.delete('/api/notes/'+note['id']).status_code==404
    plan=client.post('/api/integrations/scopesentry/preview',json={'source_key':'owned','export':json.dumps({'_id':'000000000000000000000001','type':'http','url':'https://owned-http-import.invalid/'})}).json()
    response=client.post('/api/integrations/scopesentry/'+plan['id']+'/apply',json={'selected':['000000000000000000000001'],'authorized':True})
    assert response.status_code==200 and response.json()['created']==1
    assert client.get('/api/audit/verify').status_code==405
    verified=client.post('/api/audit/verify',json={}).json();assert verified['status']=='verified'
    assert client.get('/api/llm/usage?source=all&ledger=attempts').json()['calls']==0
    for role in ('viewer','operator'):
        other=TestClient(client.app)
        try:
            assert other.post('/api/auth/login',json={'username':role,'password':'owned-http-password'}).status_code==200
            assert other.get('/api/users').status_code==403
            assert other.post('/api/audit/verify',json={}).status_code==403
            assert other.get('/api/reports/export?format=json').status_code==200
            if role=='viewer':assert other.post('/api/notes',json={'title':'x','content':'x'}).status_code==403
        finally:other.close()
    cookie=client.cookies.get('aegis_session')
    assert client.post('/api/auth/logout').status_code==200
    client.cookies.set('aegis_session',cookie)
    assert client.get('/api/assets').status_code==401


def test_native_restart_sessions_recovery_and_duplicate_start(configured,postgres):
    name,folder=configured;app=application.create_app(folder,allow_private=True);store=app.state.store
    with TestClient(app) as client:
        assert client.post('/api/auth/setup',json={'password':'owned-restart-password'}).status_code==200
        cookie=client.cookies.get('aegis_session')
        note=client.post('/api/notes',json={'title':'Persistent','content':'preserved'}).json()
        store.put('tasks',{'id':'unfinished','status':'running','checks':[],'scope_snapshot':[]})
        call=call_ledger.start(store,'planner','unfinished','owned','https://owned.invalid/',time.time(),{'status':'unconfigured','quote':None})
        with pytest.raises(WorkspaceBusy):application.create_app(folder)
        assert store.get('tasks','unfinished')['status']=='running'
    with TestClient(application.create_app(folder,allow_private=True)) as restarted:
        restarted.cookies.set('aegis_session',cookie)
        assert restarted.get('/api/auth/status').json()['authenticated']
        assert restarted.get('/api/records/notes').json()['items'][0]['id']==note['id']
        assert restarted.app.state.store.get('tasks','unfinished')['status']=='interrupted'
        assert restarted.app.state.store.get('llm_calls',call)['state']=='interrupted'
        assert restarted.post('/api/audit/verify',json={}).json()['status']=='verified'
    with PostgresLease(postgres['dsn'],name):pass
    assert not folder.exists()


def test_native_owner_loss_http_refuses_without_exposing_sql(client,postgres):
    store=client.app.state.store;owner=store.owner
    with transfer.connect(postgres['dsn']) as db:assert db.execute('SELECT pg_terminate_backend(%s) AS killed',(owner.pid,)).fetchone()['killed']
    for path in ['/api/health','/api/assets','/api/settings']:
        response=client.get(path)
        assert response.status_code==503 and 'pg_' not in response.text and 'dbname' not in response.text
        assert response.headers['cache-control']=='no-store'
    assert client.post('/api/notes',json={'title':'must refuse','content':'x'}).status_code==503


def test_native_startup_failure_releases_owner_and_invalid_config_no_fallback(configured,postgres,monkeypatch):
    name,folder=configured
    with monkeypatch.context() as patch:
        patch.setenv('AEGIS_SCOPESENTRY_SOURCES','invalid')
        with pytest.raises(RuntimeError,match='AEGIS_SCOPESENTRY_SOURCES'):application.create_app(folder)
    with PostgresLease(postgres['dsn'],name):pass
    with monkeypatch.context() as patch:
        patch.setenv('AEGIS_STORAGE_BACKEND','unknown')
        with pytest.raises(ValueError,match='AEGIS_STORAGE_BACKEND'):application.create_app(folder)
    with monkeypatch.context() as patch:
        patch.setenv('AEGIS_POSTGRES_SCHEMA','missing')
        with pytest.raises(RuntimeError,match='PostgreSQL 저장소'):application.create_app(folder)
    assert not folder.exists()
