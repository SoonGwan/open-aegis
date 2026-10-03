import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from aegis.app import AssetInput, AuthorizationRule, create_app
from aegis.response_policy import evaluate_response, validate_schema

SCHEMA = {'type': 'object', 'required': ['tenant_id', 'items'], 'properties': {
    'tenant_id': {'type': 'string'}, 'items': {'type': 'array', 'items': {'type': 'integer'}}}}
RULE = {'path': '/api/account', 'role': 'fixture', 'expected_allowed': True,
        'response_schema': SCHEMA, 'ownership': {'pointer': '/tenant_id', 'expected': 'fixture-owner'}}


def response(body, **extra):
    return {'headers': {'content-type': 'application/json'}, 'body': json.dumps(body).encode(), **extra}


def test_nested_schema_and_ownership_have_no_value_evidence():
    assert evaluate_response(RULE, response({'tenant_id': 'fixture-owner', 'items': [1, 2]})) == {
        'schema_errors': [], 'ownership_matches': True}
    wrong = evaluate_response(RULE, response({'tenant_id': 'private-other-owner', 'items': [1]}))
    assert wrong == {'schema_errors': [], 'ownership_matches': False}
    invalid = evaluate_response(RULE, response({'tenant_id': 'private-other-owner', 'items': ['private-value']}))
    assert invalid == {'schema_errors': ['type'], 'ownership_matches': None}
    assert 'private' not in json.dumps([wrong, invalid])


@pytest.mark.parametrize('schema', [
    {'$ref': 'https://external.invalid/schema'}, {'pattern': '(a+)+$'},
    {'allOf': [{'type': 'string'}]}, {'additionalProperties': {'type': 'string'}},
    {'enum': [{'secret': 'value'}]}, {'type': 'unknown'}, {'minimum': 'wrong'},
    {'properties': {str(i): {} for i in range(65)}},
])
def test_unsupported_or_invalid_schema_is_rejected(schema):
    with pytest.raises(ValueError):
        validate_schema(schema)
    with pytest.raises(ValidationError):
        AuthorizationRule(**{**RULE, 'response_schema': schema})


@pytest.mark.parametrize('body,extra', [
    (b'{"tenant_id":"fixture-owner"}', {'truncated': True}),
    (b'<html>login</html>', {'headers': {'content-type': 'text/html'}}),
    (b'{"tenant_id":"one","tenant_id":"two"}', {}),
    (b'{"number":NaN}', {}), (b'{"number":1e9999}', {}), (b'\xff', {}),
    (b'[' * 1000 + b'0' + b']' * 1000, {}),
])
def test_ambiguous_response_is_inconclusive(body, extra):
    with pytest.raises(ValueError):
        evaluate_response(RULE, {'headers': {'content-type': 'application/json'}, 'body': body, **extra})


def test_pointer_escaping_array_and_missing_field():
    rule = {'ownership': {'pointer': '/a~1b/0/~0id', 'expected': 'owner'}}
    assert evaluate_response(rule, response({'a/b': [{'~id': 'owner'}]}))['ownership_matches'] is True
    with pytest.raises(ValueError):
        evaluate_response(rule, response({'a/b': []}))
    for pointer in ('tenant', '/bad~2escape', '/a/' * 17):
        with pytest.raises(ValidationError):
            AuthorizationRule(**{**RULE, 'ownership': {'pointer': pointer, 'expected': 'owner'}})
    with pytest.raises(ValidationError):
        AuthorizationRule(**{**RULE, 'response_shema': {}})


@pytest.fixture
def api_fixture(tmp_path, monkeypatch):
    monkeypatch.setenv('AEGIS_TARGET_RPS', '20')
    class Handler(BaseHTTPRequestHandler):
        payload = {'tenant_id': 'OTHER-CUSTOMER-SENTINEL', 'items': [1], 'secret': 'MUST_NOT_PERSIST_RESPONSE'}
        media = 'application/json'
        status = 200
        requests = []

        def do_GET(self):
            type(self).requests.append(self.path)
            self.send_response(self.status if self.path == '/api/account' else 200)
            self.send_header('Content-Type', self.media)
            self.end_headers()
            self.wfile.write(json.dumps(self.payload).encode())

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        app = create_app(tmp_path/'workspace', allow_private=True)
        with TestClient(app) as client:
            assert client.post('/api/auth/setup', json={'password': 'response-policy-fixture-password'}).status_code == 200
            yield client, f'http://127.0.0.1:{server.server_port}/', Handler
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def run(client, asset):
    plan = client.post('/api/tasks', json={'name': 'Policy fixture', 'asset_ids': [asset['id']], 'checks': ['api_authorization']}).json()
    assert client.post('/api/tasks/'+plan['id']+'/approve').status_code == 200
    return finish(client, plan['id'])


def finish(client, task_id):
    for _ in range(100):
        result = client.get('/api/tasks/'+task_id).json()
        if result['task']['status'] in ('completed', 'failed'):
            return result
        time.sleep(.05)
    pytest.fail('Policy fixture did not finish')


def register(client, url, rule=RULE):
    result = client.post('/api/assets', json={'name': 'Policy fixture', 'url': url, 'type': 'api',
                         'authorized': True, 'authorization_rules': [rule]})
    assert result.status_code == 200, result.text
    return result.json()


def test_real_http_owner_mismatch_snapshot_and_redaction(api_fixture):
    client, url, handler = api_fixture
    asset = register(client, url)
    assert handler.requests == []
    result = run(client, asset)
    assert result['task']['scope_snapshot'][0]['authorization_rules'][0]['ownership'] == RULE['ownership']
    assert result['coverage'][0]['status'] == 'completed'
    assert result['findings'][0]['code'] == 'auth-owner-0'
    assert handler.requests == ['/', '/api/account']
    exported = client.get('/api/reports/export?format=json').text
    assert 'OTHER-CUSTOMER-SENTINEL' not in exported and 'MUST_NOT_PERSIST_RESPONSE' not in exported
    assert result['findings'][0]['severity'] == 'high'


@pytest.mark.parametrize('mode,allowed,status,code', [
    ('correct', True, 'completed', None), ('schema', True, 'completed', 'auth-schema-0'),
    ('schema', False, 'failed', None), ('html', True, 'failed', None),
    ('oversized', True, 'failed', None), ('missing-owner', True, 'failed', None),
    ('deny', False, 'completed', None), ('correct', False, 'completed', 'auth-rule-0'),
])
def test_real_http_policy_outcomes(api_fixture, mode, allowed, status, code):
    client, url, handler = api_fixture
    handler.payload = {'tenant_id': 'fixture-owner', 'items': [1]}
    rule = {**RULE, 'expected_allowed': allowed}
    if mode == 'schema':
        handler.payload['items'] = ['not-an-integer']
    elif mode == 'html':
        handler.media = 'text/html'
    elif mode == 'oversized':
        handler.payload['extra'] = 'x' * 140000
    elif mode == 'missing-owner':
        rule = {**rule, 'response_schema': None}
        del handler.payload['tenant_id']
    elif mode == 'deny':
        handler.status = 403
        handler.media = 'text/html'
    result = run(client, register(client, url, rule))
    assert result['task']['status'] == status
    assert result['coverage'][0]['status'] == ('failed' if status == 'failed' else 'completed')
    assert [item['code'] for item in result['findings']] == ([code] if code else [])


def test_response_policy_change_requires_new_approval(api_fixture):
    client, url, handler = api_fixture
    asset = register(client, url)
    pending = client.post('/api/tasks', json={'name': 'Old policy', 'asset_ids': [asset['id']], 'checks': ['api_authorization']}).json()
    updated = client.put('/api/assets/'+asset['id'], json={
        'name': asset['name'], 'url': url, 'type': 'api', 'authorized': True,
        'authorization_rules': [{**RULE, 'ownership': {'pointer': '/tenant_id', 'expected': 'new-fixture-owner'}}]})
    assert updated.status_code == 200 and updated.json()['revision'] == asset['revision'] + 1
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code == 409
    assert handler.requests == []
    assert client.get('/api/tasks/'+pending['id']).json()['task']['scope_snapshot'][0]['authorization_rules'][0]['ownership'] == RULE['ownership']


def test_owner_retest_inconclusive_then_resolved(api_fixture):
    client, url, handler = api_fixture
    first = run(client, register(client, url))
    finding_id = first['findings'][0]['id']
    handler.media = 'text/html'
    retest = client.post('/api/findings/'+finding_id+'/retest').json()
    assert client.post('/api/tasks/'+retest['id']+'/approve').status_code == 200
    assert finish(client, retest['id'])['task']['status'] == 'failed'
    detail = client.get('/api/findings/'+finding_id).json()
    assert detail['retests'][0]['conclusion'] == 'inconclusive'
    assert detail['finding']['status'] == 'open'
    handler.media = 'application/json'
    handler.payload['tenant_id'] = 'fixture-owner'
    retest = client.post('/api/findings/'+finding_id+'/retest').json()
    assert client.post('/api/tasks/'+retest['id']+'/approve').status_code == 200
    assert finish(client, retest['id'])['task']['status'] == 'completed'
    detail = client.get('/api/findings/'+finding_id).json()
    assert detail['retests'][0]['conclusion'] == 'resolved'
    assert detail['finding']['status'] == 'resolved'
