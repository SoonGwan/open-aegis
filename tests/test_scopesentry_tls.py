"""Real owned TLS/JWT source fixtures; never runs target validation."""
import base64
import hashlib
import hmac
import json
import os
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from aegis.app import create_app
from tests.test_scopesentry_remote import collect

SECRET = b'owned-source-fixture-signing-key'
PASSWORD = 'owned-tls-source-password'


def b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode()


def issue(expiry, secret=SECRET):
    header = b64(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode())
    payload = b64(json.dumps({'sub': 'owned-fixture-reader', 'exp': expiry}).encode())
    message = header + '.' + payload
    return message + '.' + b64(hmac.new(secret, message.encode(), hashlib.sha256).digest())


@pytest.fixture
def tls_source(tmp_path, monkeypatch, request):
    host_matches = getattr(request, 'param', True)
    cert, key = tmp_path / 'source.pem', tmp_path / 'source.key'
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '2',
                    '-subj', '/CN=owned-source-fixture', '-addext',
                    'subjectAltName=' + ('IP:127.0.0.1' if host_matches else 'DNS:wrong-source.invalid'),
                    '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)
    monkeypatch.setenv('SSL_CERT_FILE', str(cert))
    state = {'calls': [], 'clock': 2_000_000_000, 'accepted': 0, 'host_matches': host_matches}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            query = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state['calls'].append((self.path, query['pageIndex']))
            try:
                assert self.headers['Authorization'].startswith('Bearer ')
                header, payload, signature = self.headers['Authorization'].removeprefix('Bearer ').split('.')
                assert json.loads(base64.urlsafe_b64decode(header + '=' * (-len(header) % 4)))['alg'] == 'HS256'
                assert hmac.compare_digest(signature, b64(hmac.new(SECRET, (header + '.' + payload).encode(), hashlib.sha256).digest()))
                claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
                assert claims['exp'] > state['clock']
                assert self.path == '/scopesentry/api/assets/asset'
                state['accepted'] += 1
                numbers = range(1, 51) if query['pageIndex'] == 1 else [51]
                data = {'code': 200, 'data': {'list': [dict(id=f'{i:024x}', type='http', url=f'https://owned-tls-target.invalid/{i}') for i in numbers]}}
                status = 200
            except (AssertionError, ValueError, KeyError, TypeError):
                status, data = 401, {'code': 401, 'message': 'fixture JWT rejected'}
            raw = json.dumps(data).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = dict(id='fixture', url=f'https://127.0.0.1:{server.server_port}/scopesentry', token_env='OWNED_SOURCE_JWT', allow_private=True)
    monkeypatch.setenv('OWNED_SOURCE_JWT', issue(state['clock'] + 3600))
    monkeypatch.setenv('AEGIS_SCOPESENTRY_SOURCES', json.dumps([config]))
    yield state, config
    server.shutdown()
    server.server_close()
    thread.join(2)


@pytest.mark.parametrize('tls_source,trusted', [(True, True), (True, False), (False, True)], indirect=['tls_source'])
def test_source_tls_trust_and_hostname_before_credentials(tmp_path, monkeypatch, tls_source, trusted):
    state, config = tls_source
    if not trusted:
        monkeypatch.delenv('SSL_CERT_FILE')
    with TestClient(create_app(tmp_path / 'workspace')) as client:
        assert client.post('/api/auth/setup', json={'password': PASSWORD}).status_code == 200
        response = collect(client)
        if trusted and state['host_matches']:
            assert response.status_code == 200 and len(response.json()['rows']) == 50
            assert state['calls'] == [('/scopesentry/api/assets/asset', 1)]
        else:
            assert response.status_code == 502
            assert state['calls'] == [] and state['accepted'] == 0
            assert client.app.state.store.count('import_previews') == 0
        assert client.app.state.store.count('assets') == client.app.state.store.count('tasks') == 0


def test_signed_jwt_expiry_rotation_and_resume_survive_real_app_restart(tmp_path, monkeypatch, tls_source):
    state, config = tls_source
    folder = tmp_path / 'workspace'
    issued_tokens = [os.environ['OWNED_SOURCE_JWT']]
    with TestClient(create_app(folder)) as first_client:
        assert first_client.post('/api/auth/setup', json={'password': PASSWORD}).status_code == 200
        first = collect(first_client).json()
        state['clock'] += 7200
        assert collect(first_client, first).status_code == 502
        assert first_client.get('/api/assets').status_code == 200
        assert first_client.app.state.store.get('import_previews', first['id'])['remote']['next_preview_id'] is None
        monkeypatch.setenv('OWNED_SOURCE_JWT', issue(state['clock'] + 3600, b'wrong-signing-key'))
        issued_tokens.append(os.environ['OWNED_SOURCE_JWT'])
        assert collect(first_client).status_code == 502
        monkeypatch.setenv('OWNED_SOURCE_JWT', issue(state['clock'] + 3600))
        issued_tokens.append(os.environ['OWNED_SOURCE_JWT'])
        before = len(state['calls'])
        assert collect(first_client, first).status_code == 409
        assert len(state['calls']) == before
        current = collect(first_client).json()
    # A genuinely reconstructed app/lease/transport, with same configuration and credential.
    with TestClient(create_app(folder)) as restarted:
        assert restarted.post('/api/auth/login', json={'username': 'admin', 'password': PASSWORD}).status_code == 200
        next_page = collect(restarted, current).json()
        assert next_page['remote']['page'] == 2 and len(next_page['rows']) == 1
        count = len(state['calls'])
        assert collect(restarted, current).json() == next_page
        assert len(state['calls']) == count
        store = restarted.app.state.store
        assert store.count('assets') == store.count('tasks') == store.count('traffic') == 0
        for plan in (first, current, next_page):
            stored = json.dumps(store.get('import_previews', plan['id']))
            assert all(token not in stored for token in issued_tokens)


def test_private_source_is_refused_before_tls_and_jwt_when_not_enabled(tmp_path, monkeypatch, tls_source):
    state, config = tls_source
    monkeypatch.setenv('AEGIS_SCOPESENTRY_SOURCES', json.dumps([{**config, 'allow_private': False}]))
    with TestClient(create_app(tmp_path / 'workspace')) as client:
        client.post('/api/auth/setup', json={'password': PASSWORD})
        assert collect(client).status_code == 502
        assert state['calls'] == []
        assert client.app.state.store.count('import_previews') == 0
