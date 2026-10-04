import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from aegis.scopesentry_remote import Connection, Sources
from tests.test_validation import client, lab
from tests.test_identity import add, login

PATH = '/api/integrations/scopesentry/remote/preview'


@pytest.fixture
def source(client, monkeypatch):
    state = {'calls': [], 'rows': [dict(id=f'{i:024x}', type='http', url=f'https://owned-fixture.invalid/{i}', body='private-marker') for i in range(1, 52)], 'status': 200, 'raw': None, 'delay': 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            query = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state['calls'].append((self.path, self.headers.get('Authorization'), query))
            start = (query['pageIndex'] - 1) * query['pageSize']
            raw = state['raw'] or json.dumps({'code': 200, 'data': {'list': state['rows'][start:start + query['pageSize']]}}).encode()
            time.sleep(state['delay'])
            try:
                self.send_response(state['status'])
                self.send_header('Content-Type', 'application/json')
                self.send_header('Location', '/credential-sink')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv('FIXTURE_SENTRY_JWT', 'fixture-jwt-secret')
    sources = client.app.state.source_connections
    sources.connections = {'fixture': Connection(id='fixture', url=f'http://127.0.0.1:{server.server_port}', token_env='FIXTURE_SENTRY_JWT', allow_private=True, lab_http=True, project='owned')}
    yield state, sources
    server.shutdown()
    server.server_close()
    thread.join(2)


def collect(client, previous=None):
    data = {'connection_id': 'fixture'}
    if previous:
        data['previous_preview_id'] = previous['id']
    return client.post(PATH, json=data)


def test_remote_read_contract_resume_cache_and_no_target_requests(client, source, lab):
    state, sources = source
    first = collect(client).json()
    assert len(first['rows']) == 50 and first['remote']['has_more']
    second = collect(client, first).json()
    assert len(second['rows']) == 1 and second['remote']['page'] == 2
    assert not second['remote']['has_more']
    assert collect(client, first).json() == second
    assert [q['pageIndex'] for _, _, q in state['calls']] == [1, 1, 2]
    for path, auth, query in state['calls']:
        assert path == '/api/assets/asset' and auth == 'Bearer fixture-jwt-secret'
        assert query['filter'] == {'type': ['http'], 'project': ['owned']}
        assert query['pageSize'] == 50 and query['index'] == 'asset'
    assert collect(client, second).status_code == 409
    store = client.app.state.store
    assert store.count('assets') == store.count('tasks') == 0
    assert lab[1].requests == []
    record = json.dumps(store.get('import_previews', first['id']))
    assert 'fixture-jwt-secret' not in record and 'private-marker' not in record
    assert 'contract' not in json.dumps(first)
    public = client.get('/api/integrations/scopesentry/connections').text
    assert 'token_env' not in public and 'fixture-jwt-secret' not in public


@pytest.mark.parametrize('fault', ['boundary', 'duplicate', 'rotation'])
def test_remote_source_change_preserves_checkpoint(client, source, monkeypatch, fault):
    state, sources = source
    first = collect(client).json()
    if fault == 'boundary':
        state['rows'][0]['url'] += '/changed'
    elif fault == 'duplicate':
        state['rows'][50] = state['rows'][0].copy()
    else:
        monkeypatch.setenv('FIXTURE_SENTRY_JWT', 'rotated-token')
    assert collect(client, first).status_code == 409
    assert client.app.state.store.count('import_previews') == 1
    assert client.app.state.store.get('import_previews', first['id'])['remote']['next_preview_id'] is None
    if fault == 'rotation':
        assert len(state['calls']) == 1


@pytest.mark.parametrize('status', [401, 403, 302, 500])
def test_provider_errors_do_not_expire_local_session_or_advance_page(client, source, status):
    state, sources = source
    first = collect(client).json()
    state['status'] = status
    response = collect(client, first)
    assert response.status_code == 502 and 'fixture-jwt-secret' not in response.text
    assert client.get('/api/assets').status_code == 200
    assert client.app.state.store.count('import_previews') == 1
    state['status'] = 200
    assert collect(client, first).json()['remote']['page'] == 2
    assert all(path != '/credential-sink' for path, _, _ in state['calls'])


@pytest.mark.parametrize('raw', [b'not-json', b'{"code":200,"code":200}', b'{"code":true,"data":{"list":[]}}', b'{"code":200,"data":{"list":[{"type":"http","url":"https://owned.invalid/"}]}}', b'x' * (1024 * 1024 + 1)])
def test_invalid_remote_contract_never_persists(client, source, raw):
    state, sources = source
    state['raw'] = raw
    assert collect(client).status_code == 502
    assert client.app.state.store.count('import_previews') == 0


def test_empty_terminal_page_and_actor_bound_resume(client, source):
    state, sources = source
    state['rows'] = state['rows'][:50]
    first = collect(client).json()
    operator = add(client, 'operator')
    with login(client.app, operator['username']) as other:
        assert collect(other, first).status_code == 404
    terminal = collect(client, first).json()
    assert terminal['rows'] == [] and not terminal['remote']['has_more']
    assert collect(client, first).json() == terminal


def test_configuration_role_credentials_deadline_and_admission(client, source, monkeypatch):
    state, sources = source
    viewer = add(client, 'viewer')
    with login(client.app, viewer['username']) as other:
        assert other.get('/api/integrations/scopesentry/connections').status_code == 403
        assert collect(other).status_code == 403
    assert client.post(PATH, json={'connection_id': 'arbitrary-url'}).status_code == 404
    monkeypatch.delenv('FIXTURE_SENTRY_JWT')
    assert collect(client).status_code == 503 and state['calls'] == []
    monkeypatch.setenv('FIXTURE_SENTRY_JWT', 'fixture-jwt-secret')
    sources.gate.acquire()
    try:
        assert collect(client).status_code == 429
    finally:
        sources.gate.release()
    sources.timeout = .15
    state['delay'] = .5
    started = time.monotonic()
    assert collect(client).status_code == 502
    assert time.monotonic() - started < .45
    assert client.app.state.store.count('import_previews') == 0


@pytest.mark.parametrize('config', [dict(url='http://public.example'), dict(url='http://127.0.0.1', allow_private=True), dict(url='https://example.com/?secret=x'), dict(url='https://example.com', project='\ud800')])
def test_source_configuration_rejects_insecure_or_invalid_values(client, config):
    with pytest.raises((ValueError, UnicodeError)):
        Sources(client.app.state.store, threading.Event(), [dict(id='fixture', token_env='JWT', **config)])


def test_next_checkpoint_and_preview_roll_back_together(client, source):
    first = collect(client).json()
    store = client.app.state.store
    with store.connect() as db:
        db.execute("CREATE TRIGGER reject_next BEFORE INSERT ON records WHEN NEW.kind='import_previews' BEGIN SELECT RAISE(ABORT,'fixture'); END")
    with pytest.raises(Exception, match='fixture'):
        collect(client, first)
    assert store.get('import_previews', first['id'])['remote']['next_preview_id'] is None
    assert store.count('import_previews') == 1
    with store.connect() as db:
        db.execute('DROP TRIGGER reject_next')
    assert collect(client, first).status_code == 200
