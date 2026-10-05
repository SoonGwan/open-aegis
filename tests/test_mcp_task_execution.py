import json
import time

import pytest
from fastapi.testclient import TestClient

from tests.test_mcp_execution import KEY, service, target
from tests.test_mcp_registry import configured_app
from tests.test_postgres_transfer import postgres

BASE = '/api/integrations/mcp'


@pytest.fixture(params=['sqlite', 'postgres'])
def workspace(tmp_path, request, monkeypatch, service):
    _, sdk = service
    monkeypatch.setenv('AEGIS_MCP_CONNECTIONS', json.dumps([sdk.connection.model_dump()]))
    monkeypatch.setenv('AEGIS_MCP_SCOPE_OWNED', KEY.decode())
    monkeypatch.setenv('AEGIS_MCP_EXECUTORS', json.dumps([{
        'connection_id': 'owned-server', 'scope_key_env': 'AEGIS_MCP_SCOPE_OWNED', 'allow_private': True}]))
    with TestClient(configured_app(tmp_path, request.param, request, monkeypatch)) as client:
        assert client.post('/api/auth/setup', json={'password': 'aegis-test-password-only'}).status_code == 200
        yield client


def register(client, checks):
    preview = client.post(BASE + '/previews', json={'connection_id': 'owned-server'})
    assert preview.status_code == 200, preview.text
    response = client.post(BASE + '/previews/' + preview.json()['id'] + '/register',
        json={'selected': ['validate_' + check for check in checks], 'reviewed': True})
    assert response.status_code == 200, response.text
    assert all(row['execution_available'] for row in response.json()['items'])
    return response.json()['items']


def plan(client, url, checks):
    asset = client.post('/api/assets', json={'name': 'Owned target', 'url': url, 'authorized': True})
    assert asset.status_code == 200, asset.text
    response = client.post('/api/tasks', json={'name': 'Owned remote task', 'asset_ids': [asset.json()['id']],
        'checks': checks, 'planner': 'rules', 'remote_connection_id': 'owned-server'})
    assert response.status_code == 200, response.text
    return response.json()


def finished(client, task_id):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        response = client.get('/api/tasks/' + task_id)
        assert response.status_code == 200, response.text
        task = response.json()['task']
        if task['status'] not in ('pending', 'queued', 'running', 'stopping'):
            return task
        time.sleep(.03)
    raise AssertionError('Owned remote task did not finish')


def test_real_admin_review_plan_approval_worker_get_result_and_audit(workspace, target):
    url, state = target
    client = workspace
    register(client, ['security_headers', 'endpoint_inventory'])
    task = plan(client, url, ['security_headers', 'endpoint_inventory'])
    assert task['status'] == 'pending' and task['remote_execution']['connection_id'] == 'owned-server'
    assert not state['requests']
    approved = client.post('/api/tasks/' + task['id'] + '/approve')
    assert approved.status_code == 200, approved.text
    result = finished(client, task['id'])
    assert result['status'] == 'completed', result
    assert state['requests'] == [('/approved', None), ('/approved', None)]
    store = client.app.state.store
    receipts = store.all('mcp_execution_receipts')
    assert len(receipts) == 2 and store.count('mcp_execution_attempts') == 2
    assert all(row['state'] == 'admitted' for row in store.all('mcp_execution_attempts'))
    assert store.count('findings') > 0 and store.count('observations') == 1
    assert all(row['status'] == 'completed' for row in store.all('coverage'))
    assert store.audit_integrity()['valid']
    raw = json.dumps(store.all('tasks') + receipts + store.all('mcp_execution_attempts') + store.events())
    assert KEY.decode() not in raw
    assert client.post('/api/tasks/' + task['id'] + '/approve').status_code == 409
    assert len(state['requests']) == 2


def test_disabled_registered_tool_refuses_approval_before_target_request(workspace, target):
    client = workspace
    tool = register(client, ['security_headers'])[0]
    task = plan(client, target[0], ['security_headers'])
    assert client.post(BASE + '/tools/' + tool['id'] + '/disable', json={'revision': tool['revision']}).status_code == 200
    response = client.post('/api/tasks/' + task['id'] + '/approve')
    assert response.status_code == 409
    assert not target[1]['requests']
    assert client.app.state.store.get('tasks', task['id'])['status'] == 'pending'


def test_rotated_signing_key_refuses_old_plan_approval(workspace, target, monkeypatch):
    client = workspace
    register(client, ['security_headers'])
    task = plan(client, target[0], ['security_headers'])
    monkeypatch.setenv('AEGIS_MCP_SCOPE_OWNED', 'changed-owned-key-0123456789abcdefghij')
    assert client.post('/api/tasks/' + task['id'] + '/approve').status_code == 409
    assert not target[1]['requests']


def test_remote_response_failure_records_unconfirmed_attempt_and_no_receipt(workspace, target):
    client = workspace
    register(client, ['security_headers', 'cookie_policy'])
    task = plan(client, target[0], ['security_headers', 'cookie_policy'])
    target[1]['status'] = 404
    assert client.post('/api/tasks/' + task['id'] + '/approve').status_code == 200
    assert finished(client, task['id'])['status'] == 'failed'
    store = client.app.state.store
    assert store.count('mcp_execution_receipts') == store.count('findings') == 0
    assert [row['state'] for row in store.all('mcp_execution_attempts')] == ['unconfirmed']
    assert len(target[1]['requests']) == 1
    assert all(row['status'] == 'failed' for row in store.all('coverage'))


def test_shared_asset_budget_is_not_reset_between_remote_checks(workspace, target):
    from dataclasses import replace
    client = workspace
    client.app.state.engine.policy = replace(client.app.state.engine.policy, request_budget=1)
    register(client, ['security_headers', 'cookie_policy'])
    task = plan(client, target[0], ['security_headers', 'cookie_policy'])
    assert client.post('/api/tasks/' + task['id'] + '/approve').status_code == 200
    result = finished(client, task['id'])
    assert result['errors'] == 1
    assert len(target[1]['requests']) == 1
    store = client.app.state.store
    assert store.count('mcp_execution_attempts') == store.count('mcp_execution_receipts') == 1
    statuses = {row['check']: row['status'] for row in store.all('coverage')}
    assert statuses == {'security_headers': 'completed', 'cookie_policy': 'failed'}


def test_approval_audit_failure_cannot_queue_or_dispatch_remote_work(workspace, target, monkeypatch):
    client = workspace
    register(client, ['security_headers'])
    task = plan(client, target[0], ['security_headers'])
    store = client.app.state.store
    before = store.events()
    original = store.event
    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError('owned approval audit failure')
    monkeypatch.setattr(store, 'event', fail)
    with pytest.raises(RuntimeError, match='owned approval audit failure'):
        client.post('/api/tasks/' + task['id'] + '/approve')
    stored = store.get('tasks', task['id'])
    assert stored['status'] == 'pending' and stored['approved_at'] is None
    assert task['id'] not in client.app.state.engine.stops
    assert store.events() == before and store.audit_integrity()['valid']
    assert store.count('mcp_execution_attempts') == 0 and not target[1]['requests']
    monkeypatch.setattr(store, 'event', original)
    assert client.post('/api/tasks/' + task['id'] + '/approve').status_code == 200
    assert finished(client, task['id'])['status'] == 'completed'


def test_current_executor_list_has_no_network_or_secrets(workspace, target):
    client = workspace
    assert client.get(BASE + '/executors').json() == []
    tools = register(client, ['security_headers'])
    listing = client.get(BASE + '/executors').json()
    assert listing[0]['check_ids'] == ['security_headers']
    assert KEY.decode() not in json.dumps(listing)
    assert not target[1]['requests']
    assert client.post(BASE + '/tools/' + tools[0]['id'] + '/disable', json={'revision': 1}).status_code == 200
    assert client.get(BASE + '/executors').json() == []


def test_pending_replan_preserves_remote_location(workspace, target):
    client = workspace
    register(client, ['security_headers'])
    task = plan(client, target[0], ['security_headers'])
    replan = client.post('/api/tasks/' + task['id'] + '/replan')
    assert replan.status_code == 200, replan.text
    replacement = replan.json()
    assert replacement['remote_connection_id'] == 'owned-server' and replacement['status'] == 'pending'
    assert not target[1]['requests']
    assert client.post('/api/tasks/' + replacement['id'] + '/approve').status_code == 200
    assert finished(client, replacement['id'])['status'] == 'completed'


def test_finding_retest_uses_same_remote_location_with_new_approval(workspace, target):
    client = workspace
    register(client, ['security_headers'])
    task = plan(client, target[0], ['security_headers'])
    assert client.post('/api/tasks/' + task['id'] + '/approve').status_code == 200
    assert finished(client, task['id'])['status'] == 'completed'
    finding = client.app.state.store.all('findings')[0]
    retest = client.post('/api/findings/' + finding['id'] + '/retest')
    assert retest.status_code == 200, retest.text
    next_task = retest.json()
    assert next_task['remote_connection_id'] == 'owned-server' and next_task['status'] == 'pending'
    assert len(target[1]['requests']) == 1
    assert client.post('/api/tasks/' + next_task['id'] + '/approve').status_code == 200
    assert finished(client, next_task['id'])['status'] == 'completed'
    assert len(target[1]['requests']) == 2


@pytest.mark.parametrize('changed', ['approval', 'asset'])
def test_authority_changed_after_grant_creation_prevents_dispatch(workspace, target, monkeypatch, changed):
    from aegis import mcp_task_execution
    client = workspace
    register(client, ['security_headers'])
    task = plan(client, target[0], ['security_headers'])
    store = client.app.state.store
    original = mcp_task_execution.issue_grant
    def mutate(*args, **kwargs):
        token = original(*args, **kwargs)
        if changed == 'approval':
            store.patch('tasks', task['id'], approved_at=time.time() + 1)
        else:
            store.patch('assets', task['asset_ids'][0], authorized=False)
        return token
    monkeypatch.setattr(mcp_task_execution, 'issue_grant', mutate)
    assert client.post('/api/tasks/' + task['id'] + '/approve').status_code == 200
    assert finished(client, task['id'])['status'] == 'failed'
    assert not target[1]['requests']
    assert store.count('mcp_execution_attempts') == store.count('mcp_execution_receipts') == 0


def test_source_stop_prevents_admission_and_next_remote_check(workspace, target):
    client = workspace
    register(client, ['security_headers', 'cookie_policy'])
    task = plan(client, target[0], ['security_headers', 'cookie_policy'])
    target[1]['delay'] = 1.5
    assert client.post('/api/tasks/' + task['id'] + '/approve').status_code == 200
    deadline = time.monotonic() + 8
    while not target[1]['requests'] and time.monotonic() < deadline:
        time.sleep(.02)
    assert len(target[1]['requests']) == 1
    assert client.post('/api/tasks/' + task['id'] + '/stop').status_code == 200
    assert finished(client, task['id'])['status'] == 'stopped'
    store = client.app.state.store
    assert store.count('mcp_execution_receipts') == store.count('findings') == 0
    assert [row['state'] for row in store.all('mcp_execution_attempts')] == ['unconfirmed']
    assert len(target[1]['requests']) == 1
    assert all(row['status'] == 'cancelled' for row in store.all('coverage'))


def test_engine_startup_marks_unknown_dispatch_without_replaying(workspace, target):
    from aegis.engine import Engine
    from aegis.remote_mcp import _digest
    client = workspace
    register(client, ['security_headers'])
    task = plan(client, target[0], ['security_headers'])
    engine, store = client.app.state.engine, client.app.state.store
    store.patch('tasks', task['id'], status='running', approved_at=time.time())
    attempt_id = _digest([task['id'], task['asset_ids'][0], 'security_headers', 'owned-server'])
    store.put_many([('mcp_execution_attempts', {'id': attempt_id, 'task_id': task['id'], 'state': 'dispatching'})])
    engine.shutdown()
    if getattr(store, 'backend', None) == 'postgres':
        from aegis.postgres_store import PostgresStore
        store = PostgresStore(store._dsn, store.schema)
    else:
        from aegis.store import Store
        store = Store(store.path)
    restarted = Engine(store, allow_private=True)
    try:
        assert store.get('tasks', task['id'])['status'] == 'interrupted'
        attempt = store.get('mcp_execution_attempts', attempt_id)
        assert attempt['state'] == 'unconfirmed' and attempt['termination_reason'] == 'source_restart'
        assert not target[1]['requests'] and store.count('mcp_execution_receipts') == 0
        assert store.audit_integrity()['valid']
    finally:
        restarted.shutdown()
