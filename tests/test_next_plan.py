"""Owned HTTP follow-up plans are evidence-based, repeatable and approval gated."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from aegis.runtime import ExecutionPolicy
from tests.test_validation import client, lab, register, task, finish
from tests.test_identity import add, login


def completed(client, lab, checks=None):
    original = task(client, register(client, lab[0]), checks or ['security_headers'])
    assert client.post('/api/tasks/'+original['id']+'/approve').status_code == 200
    finish(client, original['id'])
    return original, '/api/tasks/'+original['id']+'/next-plan'


def test_real_results_offer_unattempted_checks_and_chain_finishes_without_oscillation(client, lab):
    original, path = completed(client, lab)
    requests = list(lab[1].requests)
    proposal = client.get(path).json()
    assert proposal['available'] and not proposal['execution_authorized']
    assert 'security_headers' not in proposal['task']['checks']
    body = {'fingerprint': proposal['fingerprint']}
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: client.post(path, json=body), range(2)))
    assert [r.status_code for r in replies] == [200, 200]
    fresh = replies[0].json()
    assert replies[1].json()['id'] == fresh['id']
    assert fresh['status'] == 'pending' and fresh['approved_at'] is None
    assert fresh['followup_of'] == original['id'] and fresh['planning_round'] == 1
    assert client.app.state.store.count('tasks') == 2
    assert lab[1].requests == requests
    assert client.post('/api/tasks/'+fresh['id']+'/approve').status_code == 200
    finish(client, fresh['id'])
    following = client.get('/api/tasks/'+fresh['id']+'/next-plan').json()
    assert following['reason'] == 'no_remaining_checks' and not following['available']
    assert following['basis']['skipped_cells']  # no authorization rule is not success
    assert client.post(path, json=body).json()['id'] == fresh['id']


def test_failed_cells_are_selected_and_completed_repetitions_disclosed_with_dependencies(client, lab):
    original, path = completed(client, lab, ['security_headers', 'cookie_policy'])
    store = client.app.state.store
    asset = register(client, lab[0]+'other/')
    source = store.get('tasks', original['id'])
    first = source['asset_ids'][0]
    store.patch('tasks', original['id'], asset_ids=[first, asset['id']], scope_snapshot=source['scope_snapshot']+[asset],
                worker_dependencies={asset['id']:[first]})
    from aegis.coverage import slot
    store.put('coverage', slot(source, source['scope_snapshot'][0], 'cookie_policy', status='failed'))
    source = store.get('tasks', original['id'])
    for check in source['checks']:
        store.put('coverage', slot(source, asset, check, status='completed'))
    proposal = client.get(path).json()
    assert proposal['basis']['retry_checks'] == ['cookie_policy']
    assert proposal['basis']['repeated_completed_cells'] == [f"{source['id']}:{asset['id']}:cookie_policy"]
    assert proposal['task']['worker_dependencies'] == {asset['id']:[first]}
    fresh = client.post(path, json={'fingerprint':proposal['fingerprint']}).json()
    assert fresh['worker_dependencies'] == proposal['task']['worker_dependencies']
    assert fresh['asset_ids'] == source['asset_ids']


@pytest.mark.parametrize('change', ['asset','coverage','policy'])
def test_stale_proposal_cannot_create_a_plan(client, lab, change):
    original, path = completed(client, lab)
    proposal = client.get(path).json()
    store = client.app.state.store
    if change == 'asset':store.patch('assets', original['asset_ids'][0], revision=2)
    if change == 'coverage':store.patch('coverage', f"{original['id']}:{original['asset_ids'][0]}:security_headers", status='failed')
    if change == 'policy':client.app.state.engine.policy = ExecutionPolicy(target_rps=1)
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).status_code == 409
    assert store.count('tasks') == 1
    updated = client.get(path).json()
    assert updated['fingerprint'] != proposal['fingerprint']
    assert client.post(path,json={'fingerprint':updated['fingerprint']}).status_code == 200


def test_accept_transaction_failure_preserves_source_and_creates_nothing(client, lab):
    original, path = completed(client, lab)
    store = client.app.state.store
    before = store.get('tasks', original['id'])
    proposal = client.get(path).json()
    with store.connect() as db:
        db.execute("CREATE TRIGGER reject_followup BEFORE INSERT ON records WHEN NEW.kind='tasks' AND json_extract(NEW.data,'$.next_plan_id') IS NOT NULL BEGIN SELECT RAISE(ABORT,'followup rollback'); END")
    with pytest.raises(sqlite3.IntegrityError,match='followup rollback'):
        client.post(path,json={'fingerprint':proposal['fingerprint']})
    assert store.get('tasks', original['id']) == before
    assert store.count('tasks') == 1


def test_roles_and_pending_archived_missing_corrupt_lineage_are_refused(client, lab):
    original, path = completed(client, lab)
    proposal = client.get(path).json()
    viewer = add(client, 'viewer')
    with login(client.app, viewer['username']) as read:
        assert read.get(path).status_code == 200
        assert read.post(path,json={'fingerprint':proposal['fingerprint']}).status_code == 403
    operator = add(client, 'operator')
    with login(client.app, operator['username']) as write:
        fresh = write.post(path,json={'fingerprint':proposal['fingerprint']}).json()
        assert write.post('/api/tasks/'+fresh['id']+'/approve').status_code == 403
    assert client.get('/api/tasks/missing/next-plan').status_code == 404
    assert client.get('/api/tasks/'+fresh['id']+'/next-plan').status_code == 409
    store = client.app.state.store
    store.patch('tasks', fresh['id'], status='completed', approved_at=1, followup_of=fresh['id'])
    assert client.get('/api/tasks/'+fresh['id']+'/next-plan').status_code == 409
    store.patch('assets', original['asset_ids'][0], archived_at=1)
    assert client.get(path).status_code == 409


def test_no_remaining_checks_produces_no_plan_and_read_never_executes(client, lab):
    from aegis.checks import CATALOG
    original, path = completed(client, lab, [c['id'] for c in CATALOG])
    requests = list(lab[1].requests)
    proposal = client.get(path).json()
    assert not proposal['available'] and proposal['reason'] == 'no_remaining_checks'
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).status_code == 409
    assert lab[1].requests == requests


def test_old_round_completion_becomes_stale_on_asset_revision_change(client, lab):
    original, path = completed(client, lab)
    proposal = client.get(path).json()
    fresh = client.post(path,json={'fingerprint':proposal['fingerprint']}).json()
    assert client.post('/api/tasks/'+fresh['id']+'/approve').status_code == 200
    finish(client, fresh['id'])
    store = client.app.state.store
    store.patch('assets', original['asset_ids'][0], revision=2)
    following = client.get('/api/tasks/'+fresh['id']+'/next-plan').json()
    assert 'security_headers' in following['basis']['retry_checks']
    assert all(row['status']=='stale' for row in following['basis']['coverage'])


def test_eight_round_limit_prevents_endless_failed_check_loop(client, lab):
    from aegis.coverage import slot
    from aegis.checks import CATALOG
    original, path = completed(client, lab, [c['id'] for c in CATALOG])
    store = client.app.state.store
    current = store.get('tasks', original['id'])
    for expected in range(1,9):
        store.put('coverage', slot(current,current['scope_snapshot'][0],'security_headers',status='failed'))
        path = '/api/tasks/'+current['id']+'/next-plan'
        proposal = client.get(path).json()
        assert proposal['available'] and proposal['planning_round']==expected
        response = client.post(path,json={'fingerprint':proposal['fingerprint']})
        assert response.status_code==200
        current = response.json()
        # Synthetic completed fixture; no execution consent or target calls in this loop.
        store.patch('tasks',current['id'],status='failed',approved_at=1)
        current=store.get('tasks',current['id'])
    store.put('coverage', slot(current,current['scope_snapshot'][0],'security_headers',status='failed'))
    path='/api/tasks/'+current['id']+'/next-plan'
    proposal=client.get(path).json()
    assert not proposal['available'] and proposal['reason']=='round_limit'
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).status_code==409
    assert store.count('tasks')==9


def test_changed_source_tool_contract_does_not_reuse_completion(client, lab):
    original,path=completed(client,lab)
    before=client.get(path).json()
    client.app.state.store.patch('tasks',original['id'],tool_contracts=None)
    after=client.get(path).json()
    assert after['basis']['retry_checks']==['security_headers']
    assert after['basis']['coverage'][0]['status']=='stale'
    assert after['fingerprint']!=before['fingerprint']
    assert client.post(path,json={'fingerprint':before['fingerprint']}).status_code==409
