import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

from aegis.app import create_app
from aegis.mcp_process import DiscoveryError, discover
from aegis.mcp_registry import Registry
from aegis import postgres_transfer
from aegis.store import Store
from tests.test_identity import add, login
from tests.test_remote_mcp import peer, requests
from tests.test_postgres_transfer import postgres, schema

BASE = '/api/integrations/mcp'


def configured_app(tmp_path, backend, request, monkeypatch):
    monkeypatch.setenv('AEGIS_STORAGE_BACKEND', backend)
    if backend == 'postgres':
        cluster = request.getfixturevalue('postgres')
        name = schema()
        source = Store(tmp_path / 'source' / 'aegis.db')
        postgres_transfer.sqlite_to_postgres(source.path, cluster['dsn'], name)
        monkeypatch.setenv('AEGIS_POSTGRES_DSN', cluster['dsn'])
        monkeypatch.setenv('AEGIS_POSTGRES_SCHEMA', name)
    return create_app(tmp_path / 'workspace', allow_private=True)


@pytest.fixture(params=['sqlite', 'postgres'])
def client(tmp_path, request, monkeypatch):
    monkeypatch.setenv('AEGIS_MCP_CONNECTIONS', '[]')
    with TestClient(configured_app(tmp_path, request.param, request, monkeypatch)) as client:
        assert client.post('/api/auth/setup', json={'password': 'aegis-test-password-only'}).status_code == 200
        yield client


@pytest.fixture
def registry_peer(client, peer):
    state, sdk = peer
    registry = client.app.state.mcp_registry
    registry.connections = {'fixture': sdk.connection}
    return state, registry


def preview(client):
    response = client.post(BASE + '/previews', json={'connection_id': 'fixture'})
    assert response.status_code == 200, response.text
    return response.json()


def register(client, review, selected=None):
    return client.post(BASE + '/previews/' + review['id'] + '/register',
                       json={'selected': selected or ['inspect'], 'reviewed': True})


def test_review_registration_retry_disable_and_no_execution(client, registry_peer):
    state, _ = registry_peer
    review = preview(client)
    assert review['catalog']['tools'][0]['name'] == 'inspect'
    registered = register(client, review)
    assert registered.status_code == 200, registered.text
    row = registered.json()['items'][0]
    assert row['enabled'] and row['revision'] == 1 and row['execution_available'] is False
    before = len(state['calls'])
    assert register(client, review).json() == registered.json()
    assert len(state['calls']) == before  # Response-loss replay makes no remote requests.
    listing = client.get(BASE + '/tools').json()
    assert listing['total'] == 1 and listing['items'] == [row]
    assert 'definition' not in listing['items'][0]
    detail = client.get(BASE + '/tools/' + row['id']).json()
    assert detail['definition'] == review['catalog']['tools'][0]
    disabled = client.post(BASE + '/tools/' + row['id'] + '/disable', json={'revision': 1})
    assert disabled.status_code == 200 and disabled.json()['revision'] == 2
    assert disabled.json()['enabled'] is False
    # Replaying the original registration receipt never restores current state.
    assert register(client, review).json() == registered.json()
    assert client.get(BASE + '/tools/' + row['id']).json()['enabled'] is False
    assert client.post(BASE + '/tools/' + row['id'] + '/disable', json={'revision': 1}).status_code == 409
    assert client.post(BASE + '/tools/' + row['id'] + '/disable', json={'revision': 2}).json() == disabled.json()
    assert not requests(state, 'tools/call')
    store = client.app.state.store
    assert store.count('assets') == store.count('tasks') == store.count('findings') == 0
    assert store.audit_integrity()['valid']
    records = json.dumps(store.all('mcp_previews') + store.all('mcp_tools') + store.events())
    assert state['token'] not in records and state['session'] not in records
    assert 'connection_contract' not in json.dumps(review)


def test_roles_and_actor_ownership(client, registry_peer):
    state, _ = registry_peer
    review = preview(client)
    operator = add(client, 'operator')
    viewer = add(client, 'viewer')
    second_admin = add(client, 'admin', 'other-admin')
    before = len(state['calls'])
    for actor in (operator, viewer):
        with login(client.app, actor['username']) as other:
            assert other.get(BASE + '/connections').status_code == 403
            assert other.get(BASE + '/tools').status_code == 403
            assert other.post(BASE + '/previews', json={'connection_id': 'fixture'}).status_code == 403
            assert register(other, review).status_code == 403
    with login(client.app, second_admin['username']) as other:
        assert register(other, review).status_code == 403
    anonymous = TestClient(client.app)
    try:
        assert anonymous.get(BASE + '/connections').status_code == 401
    finally:
        anonymous.close()
    assert len(state['calls']) == before
    assert client.app.state.store.count('mcp_tools') == 0


@pytest.mark.parametrize('change', ['catalog', 'credential', 'expiry'])
def test_changed_review_is_not_registered(client, registry_peer, monkeypatch, change):
    state, registry = registry_peer
    review = preview(client)
    if change == 'catalog':
        state['revision'] = '2'
    elif change == 'credential':
        monkeypatch.setenv('FIXTURE_MCP_TOKEN', 'new-fixture-secret')
    else:
        registry.store.patch('mcp_previews', review['id'], expires_at=0)
    response = register(client, review)
    assert response.status_code == (410 if change == 'expiry' else 409)
    assert registry.store.count('mcp_tools') == 0
    assert registry.store.get('mcp_previews', review['id'])['registered_at'] is None
    assert not requests(state, 'tools/call')


def test_disable_during_old_review_requires_new_review(client, registry_peer):
    state, _ = registry_peer
    first = register(client, preview(client)).json()['items'][0]
    stale = preview(client)
    assert client.post(BASE + '/tools/' + first['id'] + '/disable', json={'revision': 1}).status_code == 200
    assert register(client, stale).status_code == 409
    assert client.get(BASE + '/tools/' + first['id']).json()['enabled'] is False
    fresh = preview(client)
    row = register(client, fresh).json()['items'][0]
    assert row['enabled'] and row['revision'] == 3
    assert not requests(state, 'tools/call')


def test_registration_audit_failure_rolls_back_every_record(client, registry_peer, monkeypatch):
    state, registry = registry_peer
    review = preview(client)
    original = registry.store.event

    def fail(task_id, message, *args, **kwargs):
        if message == '검토된 MCP 도구 등록':
            raise RuntimeError('owned-audit-fault')
        return original(task_id, message, *args, **kwargs)

    monkeypatch.setattr(registry.store, 'event', fail)
    with pytest.raises(RuntimeError, match='owned-audit-fault'):
        register(client, review)
    assert registry.store.count('mcp_tools') == 0
    assert registry.store.get('mcp_previews', review['id'])['registered_at'] is None
    monkeypatch.setattr(registry.store, 'event', original)
    assert register(client, review).status_code == 200
    assert registry.store.audit_integrity()['valid']
    assert not requests(state, 'tools/call')


@pytest.mark.parametrize('selection', [['inspect', 'inspect'], ['unknown']])
def test_invalid_selection_never_fetches_or_registers(client, registry_peer, selection):
    state, registry = registry_peer
    review = preview(client)
    before = len(state['calls'])
    assert register(client, review, selection).status_code == 422
    assert len(state['calls']) == before
    assert registry.store.count('mcp_tools') == 0


def test_gate_limits_competing_discovery(client, registry_peer):
    _, registry = registry_peer
    registry.gate.acquire()
    try:
        response = client.post(BASE + '/previews', json={'connection_id': 'fixture'})
        assert response.status_code == 429 and response.headers['Retry-After'] == '2'
    finally:
        registry.gate.release()


def test_credential_reflection_in_metadata_is_rejected(client, registry_peer):
    state, registry = registry_peer
    state['revision'] = state['token']
    response = client.post(BASE + '/previews', json={'connection_id': 'fixture'})
    assert response.status_code == 502
    assert state['token'] not in response.text
    assert registry.store.count('mcp_previews') == registry.store.count('mcp_tools') == 0


def test_discovery_child_gets_only_selected_secrets_and_is_reaped(peer, monkeypatch):
    state, sdk = peer
    from aegis import mcp_process
    monkeypatch.setenv('UNRELATED_PRIVATE_KEY', 'never-forward-this')
    original = mcp_process.subprocess.Popen
    children = []

    def capture(*args, **kwargs):
        assert 'UNRELATED_PRIVATE_KEY' not in kwargs['env']
        assert kwargs['env']['FIXTURE_MCP_TOKEN'] == state['token']
        child = original(*args, **kwargs)
        children.append((child, kwargs['cwd']))
        return child

    monkeypatch.setattr(mcp_process.subprocess, 'Popen', capture)
    assert discover(sdk.connection)['tools'][0]['name'] == 'inspect'
    from pathlib import Path
    assert len(children) == 1 and children[0][0].poll() == 0
    assert not Path(children[0][1]).exists()
    assert not requests(state, 'tools/call')


def test_parent_watchdog_kills_and_reaps_hanging_child(peer, monkeypatch):
    _, sdk = peer
    from aegis import mcp_process
    original = mcp_process.subprocess.Popen
    children = []

    def hang(command, **kwargs):
        child = original([command[0], '-I', '-c', 'import time;time.sleep(30)'], **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(mcp_process.subprocess, 'Popen', hang)
    start = time.monotonic()
    with pytest.raises(DiscoveryError):
        discover(sdk.connection, timeout=.08)
    assert time.monotonic() - start < 1
    assert len(children) == 1 and children[0].poll() == -9


def test_shutdown_cancels_live_discovery_and_reaps_child(peer, monkeypatch):
    state, sdk = peer
    from aegis import mcp_process
    original = mcp_process.subprocess.Popen
    stop, children = threading.Event(), []
    state['mode'] = 'slow'

    def capture(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        stop.set()
        return child

    monkeypatch.setattr(mcp_process.subprocess, 'Popen', capture)
    with pytest.raises(DiscoveryError):
        discover(sdk.connection, stop)
    assert len(children) == 1 and children[0].poll() == -9


@pytest.mark.parametrize('raw', ['{}', '[{},{}]', '[NaN]', '[{"id":"a","id":"b"}]'])
def test_configuration_fails_closed(client, monkeypatch, raw):
    monkeypatch.setenv('AEGIS_MCP_CONNECTIONS', raw)
    with pytest.raises(RuntimeError, match='AEGIS_MCP_CONNECTIONS'):
        Registry.from_env(client.app.state.store, threading.Event())


@pytest.mark.parametrize('backend', ['sqlite', 'postgres'])
def test_actual_app_restart_preserves_registration_without_remote_calls(tmp_path, peer, monkeypatch, request, backend):
    state, sdk = peer
    monkeypatch.setenv('AEGIS_MCP_CONNECTIONS', json.dumps([sdk.connection.model_dump()]))
    with TestClient(configured_app(tmp_path, backend, request, monkeypatch)) as first:
        assert first.post('/api/auth/setup', json={'password': 'aegis-test-password-only'}).status_code == 200
        row = register(first, preview(first)).json()['items'][0]
    before = len(state['calls'])
    with TestClient(create_app(tmp_path / 'workspace', allow_private=True)) as second:
        assert second.post('/api/auth/login', json={'password': 'aegis-test-password-only'}).status_code == 200
        assert second.get(BASE + '/tools/' + row['id']).json()['definition']['name'] == 'inspect'
        assert second.get(BASE + '/tools').json()['items'] == [row]
    assert len(state['calls']) == before


@pytest.mark.parametrize('peer', ['trusted', 'untrusted', 'wrong_host'], indirect=True)
def test_registry_child_tls_trust_and_hostname_before_credentials(client, registry_peer):
    state, registry = registry_peer
    response = client.post(BASE + '/previews', json={'connection_id': 'fixture'})
    if state['tls'] == 'trusted':
        assert response.status_code == 200, response.text
        assert register(client, response.json()).status_code == 200
        assert registry.store.count('mcp_tools') == 1
    else:
        assert response.status_code == 502
        assert not state['calls']
        assert registry.store.count('mcp_previews') == registry.store.count('mcp_tools') == 0
    assert state['token'] not in response.text and state['session'] not in response.text
    assert not requests(state, 'tools/call')
