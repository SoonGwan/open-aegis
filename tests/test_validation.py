import hashlib
import io
import json
import socket
import threading
import time
from http.server import ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from aegis.app import create_app
from aegis.engine import Engine
from aegis.store import Store
from aegis.network import ScopeError, Transport, in_scope, normalize_url, resolve
from examples.lab_server import LabHandler


@pytest.fixture
def lab():
    class Handler(LabHandler):
        hardened = False
        fault = False
        requests = []
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}/', Handler
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path, allow_private=True)
    with TestClient(app) as client:
        assert client.post('/api/auth/setup', json={'password': 'aegis-test-password-only'}).status_code == 200
        yield client


def register(client, url, **extra):
    response = client.post('/api/assets', json={'name': 'Synthetic lab', 'url': url, 'authorized': True, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def task(client, asset, checks):
    response = client.post('/api/tasks', json={'name': 'Fixture validation', 'asset_ids': [asset['id']], 'checks': checks})
    assert response.status_code == 200, response.text
    return response.json()


def finish(client, id):
    for _ in range(100):
        result = client.get('/api/tasks/' + id).json()
        if result['task']['status'] in ('completed', 'failed', 'stopped'):
            return result
        time.sleep(.05)
    pytest.fail('Task did not finish within five seconds')


def test_authentication_csrf_and_session_invalidation(tmp_path):
    with TestClient(create_app(tmp_path)) as c:
        assert c.get('/api/assets').status_code == 401
        assert c.post('/api/auth/setup', json={'password': 'strong-test-password'}, headers={'Origin': 'https://attacker.invalid'}).status_code == 403
        assert c.post('/api/auth/setup', json={'password': 'strong-test-password'}).status_code == 200
        assert c.post('/api/auth/setup', json={'password': 'another-password'}).status_code == 409
        cookie = c.cookies.get('aegis_session')
        assert c.get('/api/assets').status_code == 200
        assert c.post('/api/auth/logout').status_code == 200
        c.cookies.set('aegis_session', cookie)
        assert c.get('/api/assets').status_code == 401
        assert c.get('/api/health', headers={'Host': 'attacker.invalid'}).status_code == 400


def test_no_requests_before_approval_and_no_duplicate_execution(client, lab):
    url, handler = lab
    asset = register(client, url)
    pending = task(client, asset, ['security_headers', 'endpoint_inventory'])
    time.sleep(.1)
    assert handler.requests == []
    assert pending['status'] == 'pending'
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code == 200
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code == 409
    result = finish(client, pending['id'])
    assert result['task']['status'] == 'completed'
    assert handler.requests == ['/']
    assert len(result['coverage']) == 2
    assert any(f['code'] == 'missing-nosniff' for f in result['findings'])
    reply=client.post('/api/tasks/'+pending['id']+'/messages',json={'content':'검증 요약'}).json()
    cited=[citation['evidence'] for citation in reply['provenance']['citations'][1:]]
    assert cited and all(proof is not None and proof['task_id']==pending['id'] for proof in cited)
    for proof in cited:
        original=client.app.state.store.get('evidence',proof['id'])
        assert json.loads(proof['excerpt'])==original['observation']
    assert handler.requests==['/'], 'Conversation must not make additional target requests'
    observations = client.get('/api/overview').json()['observations']
    assert [o['url'] for o in observations] == [url+'api/account']


def test_retest_failing_before_passing_after_preserves_evidence(client, lab):
    url, handler = lab
    asset = register(client, url)
    pending = task(client, asset, ['security_headers'])
    client.post('/api/tasks/'+pending['id']+'/approve')
    result = finish(client, pending['id'])
    finding = next(f for f in result['findings'] if f['code'] == 'missing-nosniff')
    original = client.get('/api/findings/'+finding['id']).json()['evidence']
    assert len(original) == 1
    handler.hardened = True
    retest = client.post('/api/findings/'+finding['id']+'/retest').json()
    assert client.post('/api/findings/'+finding['id']+'/retest').json()['id'] == retest['id']
    client.post('/api/tasks/'+retest['id']+'/approve')
    assert finish(client, retest['id'])['task']['status'] == 'completed'
    detail = client.get('/api/findings/'+finding['id']).json()
    assert detail['finding']['status'] == 'resolved'
    assert detail['retests'][0]['conclusion'] == 'resolved'
    assert detail['evidence'] == original


def test_server_error_does_not_falsely_resolve_finding(client, lab):
    url, handler = lab
    asset = register(client, url)
    pending = task(client, asset, ['security_headers'])
    client.post('/api/tasks/'+pending['id']+'/approve')
    finding = finish(client, pending['id'])['findings'][0]
    handler.fault = True
    retest = client.post('/api/findings/'+finding['id']+'/retest').json()
    client.post('/api/tasks/'+retest['id']+'/approve')
    finish(client, retest['id'])
    detail = client.get('/api/findings/'+finding['id']).json()
    assert detail['finding']['status'] == 'open'
    assert detail['retests'][0]['conclusion'] == 'inconclusive'


def test_authorization_rules_and_secret_redaction(client, lab, monkeypatch):
    url, handler = lab
    monkeypatch.setenv('AEGIS_TEST_USER', 'Bearer secret-test-value-123')
    asset = register(client, url, authorization_rules=[{'path': '/api/account', 'role': 'other-tenant', 'expected_allowed': False, 'credential_env': 'AEGIS_TEST_USER'}])
    pending = task(client, asset, ['api_authorization', 'cookie_policy'])
    client.post('/api/tasks/'+pending['id']+'/approve')
    result = finish(client, pending['id'])
    assert any(f['severity'] == 'high' and f['confidence'] == 'policy-mismatch' for f in result['findings'])
    report = client.get('/api/reports/export?format=json').text
    assert 'secret-test-value-123' not in report
    assert 'fixture-only' not in report
    assert 'NOT-REAL-CUSTOMER-DATA' not in report
    traffic = client.get('/api/traffic').json()
    assert len(traffic) == 2
    assert all(len(t['body_sha256']) == 64 for t in traffic)


def test_out_of_scope_redirect_is_never_requested(lab):
    url, handler = lab
    with pytest.raises(ScopeError, match='범위'):
        Transport(url, allow_private=True, delay=0).get(url+'redirect-outside')
    assert handler.requests == ['/redirect-outside']


@pytest.mark.parametrize('url', ['file:///etc/passwd','http://user:secret@example.com/','http://example.com/a/../b','http://example.com/%252e%252e/admin','http://example.com/a\\b'])
def test_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        normalize_url(url)


def test_exact_origin_and_path_scope():
    assert in_scope('https://example.com/app/account','https://example.com/app')
    assert not in_scope('https://example.com/apple','https://example.com/app')
    assert not in_scope('https://example.com.evil.invalid/app','https://example.com/app')
    assert not in_scope('http://example.com/app','https://example.com/app')
    assert not in_scope('https://example.com:8443/app','https://example.com/app')


@pytest.mark.parametrize('address', ['127.0.0.1','10.0.0.1','169.254.169.254','::1','::ffff:169.254.169.254','100.100.100.200'])
def test_private_and_metadata_addresses_blocked(monkeypatch,address):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',(address,80))])
    with pytest.raises(ScopeError): resolve('example.com',80)
    if '169.254' in address or address == '100.100.100.200':
        with pytest.raises(ScopeError): resolve('example.com',80,allow_private=True)


def test_dns_connection_is_pinned_to_checked_address(lab, monkeypatch):
    url, _ = lab
    port = int(url.split(':')[-1].strip('/'))
    calls=[]
    def resolver(host, resolved_port, *args, **kwargs):
        calls.append(host)
        return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',resolved_port))]
    monkeypatch.setattr(socket,'getaddrinfo',resolver)
    response=Transport(f'http://fixture.invalid:{port}/',allow_private=True,delay=0).get()
    assert response['status'] == 200
    assert calls == ['fixture.invalid','127.0.0.1']


def test_cancellation_prevents_request(lab):
    url, handler = lab
    with pytest.raises(InterruptedError): Transport(url,True,cancelled=lambda:True).get()
    assert handler.requests == []


def test_import_validation_is_atomic(client):
    response = client.post('/api/assets/import',json=[{'name':'one','url':'https://example.com/','authorized':True},{'name':'two','url':'https://example.com/','authorized':True}])
    assert response.status_code == 409
    assert client.get('/api/assets').json() == []


def test_rejected_task_never_executes(client,lab):
    url, handler = lab
    asset=register(client,url)
    pending=task(client,asset,['security_headers'])
    assert client.post('/api/tasks/'+pending['id']+'/stop').json()['status'] == 'rejected'
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code == 409
    assert handler.requests == []


def test_asset_policy_rejects_out_of_scope_and_arbitrary_env(client):
    for rule in [
        {'path':'/outside','role':'user','expected_allowed':False},
        {'path':'/app/test','role':'user','expected_allowed':False,'credential_env':'AWS_SECRET_ACCESS_KEY'}
    ]:
        assert client.post('/api/assets',json={'name':'app','url':'https://example.com/app/','authorized':True,'authorization_rules':[rule]}).status_code == 422


def test_missing_test_credential_never_marks_authorization_completed(client,lab):
    url,_=lab
    asset=register(client,url,authorization_rules=[{'path':'/api/account','role':'user','expected_allowed':True,'credential_env':'AEGIS_TEST_MISSING'}])
    pending=task(client,asset,['api_authorization'])
    client.post('/api/tasks/'+pending['id']+'/approve')
    result=finish(client,pending['id'])
    assert result['task']['status'] == 'failed'
    assert len(result['coverage']) == 1
    assert result['coverage'][0]['status'] == 'failed'
    assert result['coverage'][0]['error_type'] == 'ValueError'
    assert len(client.get('/api/traffic').json()) == 1


def test_http_request_budget_is_enforced(lab):
    url,handler=lab
    transport=Transport(url,allow_private=True,delay=0)
    transport.max_requests=1
    transport.get()
    with pytest.raises(ScopeError,match='예산'): transport.get()
    assert handler.requests == ['/']


@pytest.mark.parametrize('proposed', [['cookie_policy','security_headers'],['Bash','security_headers'],['security_headers'],['security_headers','security_headers']])
def test_ai_planner_cannot_expand_or_drop_approved_tools(tmp_path,monkeypatch,proposed):
    monkeypatch.setenv('AEGIS_LLM_API_KEY','synthetic-key')
    monkeypatch.setenv('AEGIS_LLM_MODEL','synthetic-model')
    payload={'choices':[{'message':{'content':json.dumps({'checks':proposed})}}]}
    monkeypatch.setattr('aegis.engine.completion',lambda *a,**k:payload)
    store=Store(tmp_path/'aegis.db')
    engine=Engine(store)
    approved=['security_headers','cookie_policy']
    store.put('tasks', {'id':'task','status':'pending'})
    plan=engine.plan({'id':'task','checks':approved,'planner':'ai','goal':'Fixture','scope_snapshot':[]})
    assert set(plan) == set(approved) and len(plan) == len(approved)
    if proposed == ['cookie_policy','security_headers']: assert plan == proposed
    else: assert plan == approved
    engine.shutdown()


def test_restart_marks_stopping_tasks_interrupted(tmp_path):
    store=Store(tmp_path/'aegis.db')
    store.put('tasks',{'id':'stopping-task','status':'stopping'})
    engine=Engine(store)
    assert store.get('tasks','stopping-task')['status'] == 'interrupted'
    engine.shutdown()


def test_record_assistant_is_grounded_and_sends_no_requests(client,lab):
    url,handler=lab
    asset=register(client,url)
    pending=task(client,asset,['security_headers'])
    answer=client.post('/api/tasks/'+pending['id']+'/messages',json={'content':'지금 무엇을 수정하면 되나요?'}).json()
    assert 'pending' in answer['content']
    assert '아직 대상 요청을 보내지 않았습니다' in answer['content']
    assert handler.requests == []
    assert len(client.get('/api/tasks/'+pending['id']+'/messages').json()) == 2
