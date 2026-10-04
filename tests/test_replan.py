"""Refreshing a pending plan preserves provenance without granting execution consent."""
import sqlite3
from concurrent.futures import Future, ThreadPoolExecutor

import pytest

from aegis.runtime import ExecutionPolicy
from aegis.tool_contracts import contracts_for
from tests.test_identity import add, login
from tests.test_validation import client, lab, register, task


def test_replan_uses_current_scope_policy_contracts_and_preserves_original(client, lab):
    url, handler = lab
    store = client.app.state.store
    engine = client.app.state.engine
    asset = register(client, url)
    original = task(client, asset, ['security_headers'])
    store.patch('tasks', original['id'], tool_contracts=None)
    revised = client.put('/api/assets/' + asset['id'], json={**asset, 'authorized': True, 'name': 'Current fixture'}).json()
    engine.policy = ExecutionPolicy(target_rps=1, pending_limit=1)
    response = client.post('/api/tasks/' + original['id'] + '/replan')
    assert response.status_code == 200
    fresh = response.json()
    assert fresh['status'] == 'pending' and fresh['approved_at'] is None
    assert fresh['scope_snapshot'][0] == revised
    assert fresh['execution_policy'] == engine.policy.public()
    assert fresh['tool_contracts'] == contracts_for(original['checks'])
    assert fresh['replan_of'] == original['id'] and fresh['id'] != original['id']
    before = store.get('tasks', original['id'])
    assert before['status'] == 'rejected' and before['termination_reason'] == 'replanned'
    assert before['replaced_by'] == fresh['id'] and before['scope_snapshot'] == original['scope_snapshot']
    assert before['tool_contracts'] is None and before['approved_at'] is None
    assert client.get('/api/tasks/' + original['id']).json()['coverage'][0]['status'] == 'cancelled'
    assert client.get('/api/tasks/' + fresh['id']).json()['coverage'][0]['status'] == 'not_started'
    assert client.post('/api/tasks/' + original['id'] + '/approve').status_code == 409
    assert handler.requests == []
    assert store.count('tasks', statuses=['pending']) == 1


def test_replan_retries_and_concurrent_clicks_return_one_same_plan(client, lab):
    asset = register(client, lab[0])
    original = task(client, asset, ['security_headers'])
    path = '/api/tasks/' + original['id'] + '/replan'
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post(path), range(2)))
    assert all(response.status_code == 200 for response in responses)
    fresh = responses[0].json()
    assert responses[1].json()['id'] == fresh['id']
    client.app.state.store.patch('tasks', fresh['id'], status='completed')
    assert client.post(path).json()['id'] == fresh['id']
    assert client.app.state.store.count('tasks') == 2
    assert lab[1].requests == []


def test_replan_and_approval_cannot_both_replace_and_start_original(client, lab, monkeypatch):
    engine = client.app.state.engine
    monkeypatch.setattr(engine.pool, 'submit', lambda *_: Future())
    original = task(client, register(client, lab[0]), ['security_headers'])
    path = '/api/tasks/' + original['id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda action: client.post(path + action), ['/approve', '/replan']))
    assert sorted(response.status_code for response in responses) == [200, 409]
    stored = client.app.state.store.get('tasks', original['id'])
    assert stored['status'] in ('queued', 'rejected')
    assert client.app.state.store.count('tasks', statuses=['pending', 'queued']) == 1
    assert lab[1].requests == []


def test_replan_storage_failure_rolls_back_source_and_replacement(client, lab):
    store = client.app.state.store
    original = task(client, register(client, lab[0]), ['security_headers'])
    with store.connect() as db:
        db.execute("CREATE TRIGGER reject_replan BEFORE INSERT ON records WHEN NEW.kind='coverage' AND json_extract(NEW.data,'$.status')='cancelled' BEGIN SELECT RAISE(ABORT,'synthetic rollback'); END")
    with pytest.raises(sqlite3.IntegrityError, match='synthetic rollback'):
        client.post('/api/tasks/' + original['id'] + '/replan')
    assert store.get('tasks', original['id']) == original
    assert store.count('tasks') == 1
    assert client.get('/api/tasks/' + original['id']).json()['coverage'][0]['status'] == 'not_started'
    assert lab[1].requests == []


def test_replan_rejects_archived_missing_nonpending_and_unauthorized(client, lab):
    store = client.app.state.store
    asset = register(client, lab[0])
    original = task(client, asset, ['security_headers'])
    path = '/api/tasks/' + original['id'] + '/replan'
    viewer = add(client, 'viewer')
    with login(client.app, viewer['username']) as read:
        assert read.post(path).status_code == 403
    operator = add(client, 'operator')
    with login(client.app, operator['username']) as write:
        assert write.post(path).status_code == 200
    assert client.post('/api/tasks/missing/replan').status_code == 404
    new_id = store.get('tasks', original['id'])['replaced_by']
    store.patch('tasks', new_id, status='running')
    assert client.post('/api/tasks/' + new_id + '/replan').status_code == 409
    store.patch('tasks', new_id, status='pending')
    store.patch('assets', asset['id'], archived_at=1)
    assert client.post('/api/tasks/' + new_id + '/replan').status_code == 409
    assert store.get('tasks', new_id)['status'] == 'pending'
    client.post('/api/auth/logout')
    assert client.post('/api/tasks/' + new_id + '/replan').status_code == 401
    assert lab[1].requests == []


def test_replan_preserves_schedule_and_retest_lineage_with_current_decision_revision(client, lab):
    store = client.app.state.store
    original = task(client, register(client, lab[0]), ['security_headers'])
    store.put('findings', {'id': 'replan-finding', 'triage_revision': 7})
    store.patch('tasks', original['id'], retest_of='replan-finding', retest_triage_revision=1, schedule_id='schedule-fixture')
    fresh = client.post('/api/tasks/' + original['id'] + '/replan').json()
    assert fresh['status'] == 'pending' and fresh['retest_of'] == 'replan-finding'
    assert fresh['retest_triage_revision'] == 7 and fresh['schedule_id'] == 'schedule-fixture'
    assert store.get('tasks', original['id'])['retest_triage_revision'] == 1
    assert lab[1].requests == []
