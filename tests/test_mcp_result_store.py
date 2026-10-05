import copy
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from aegis.coverage import slot
from aegis.mcp_executor import Runner
from aegis.mcp_result_store import AdmissionError, admit
from tests.test_mcp_execution import KEY, approved_task, grant, target
from tests.test_mcp_registry import client
from tests.test_postgres_transfer import postgres


@pytest.fixture
def prepared(client, target, tmp_path):
    return prepare(client.app.state.store, target[0], tmp_path)


def prepare(store, url, tmp_path, check='security_headers'):
    task = approved_task(url, check)
    task.update(created_at=time.time(), asset_ids=['owned-asset'], workers=1)
    asset = task['scope_snapshot'][0]
    store.put('assets', asset)
    store.put('tasks', task)
    store.put('coverage', slot(task, asset, check))
    token = grant(task)
    output = Runner('owned-server', KEY, tmp_path / 'ledger.db', allow_private=True).execute(
        'validate_' + check, {'grant': token})
    response = {'isError': False, 'content': [], 'structuredContent': output}
    return store, task, token, response


def receive(prepared):
    store, task, token, response = prepared
    return admit(store, task, 'owned-asset', task['checks'][0], token, KEY,
                 'owned-server', response, allow_private=True)


def state(store):
    return {kind: store.all(kind) for kind in ('findings', 'evidence', 'finding_history',
             'observations', 'traffic', 'coverage', 'mcp_execution_receipts')} | {'events': store.events()}


def test_actual_get_result_admission_commits_linked_evidence_coverage_and_audit_once(prepared):
    store, task, token, _ = prepared
    receipt = receive(prepared)
    assert receipt['finding_ids'] and receipt['evidence_ids'] and len(receipt['traffic_ids']) == 1
    assert len(receipt['finding_ids']) == len(receipt['evidence_ids'])
    assert store.get('coverage', receipt['coverage_id'])['status'] == 'completed'
    for proof_id in receipt['evidence_ids']:
        assert store.get('evidence', proof_id)['task_id'] == task['id']
    assert store.get('traffic', receipt['traffic_ids'][0])['remote_admission_id'] == receipt['id']
    assert store.events()[-1]['detail']['remote_admission_id'] == receipt['id']
    assert store.audit_integrity()['valid']
    store.patch('tasks', task['id'], status='completed')
    before = state(store)
    assert receive(prepared) == receipt
    assert state(store) == before
    raw = json.dumps(before)
    assert token not in raw and KEY.decode() not in raw


@pytest.mark.parametrize('change', ['stopped', 'snapshot', 'policy', 'approval', 'asset_revision', 'coverage', 'coverage_id'])
def test_changed_current_authority_refuses_whole_result_without_any_writes(prepared, change):
    store, task, _, _ = prepared
    if change == 'stopped':
        store.patch('tasks', task['id'], status='stopping')
    elif change == 'snapshot':
        asset = {**task['scope_snapshot'][0], 'url': task['scope_snapshot'][0]['url'] + '/other'}
        store.patch('tasks', task['id'], scope_snapshot=[asset])
    elif change == 'policy':
        store.patch('tasks', task['id'], execution_policy={**task['execution_policy'], 'request_budget': 1})
    elif change == 'approval':
        store.patch('tasks', task['id'], approved_at=task['approved_at'] + 1)
    elif change == 'asset_revision':
        store.patch('assets', 'owned-asset', revision=5)
    elif change == 'coverage':
        store.patch('coverage', f"{task['id']}:owned-asset:security_headers", status='failed')
    else:
        key = f"{task['id']}:owned-asset:security_headers"
        with store.write_transaction() as db:
            marker = '%s' if getattr(store, 'backend', None) == 'postgres' else '?'
            row = store.get('coverage', key, connection=db)
            row['id'] = 'wrong-storage-key'
            db.execute(f'UPDATE records SET data={marker} WHERE kind={marker} AND id={marker}',
                       (json.dumps(row), 'coverage', key))
    before = state(store)
    with pytest.raises(AdmissionError):
        receive(prepared)
    assert state(store) == before


def test_valid_signature_for_different_approval_cannot_be_admitted(prepared):
    store, task, _, _ = prepared
    different = {**task, 'approved_at': task['approved_at'] - 1}
    token = grant(different)
    response = copy.deepcopy(prepared[3])
    response['structuredContent']['grant_sha256'] = hashlib.sha256(token.encode()).hexdigest()
    before = state(store)
    with pytest.raises(AdmissionError):
        receive((store, task, token, response))
    assert state(store) == before


def test_caller_mutation_during_validation_cannot_rebind_result_to_new_approval(prepared, monkeypatch):
    from aegis import mcp_result_store
    store, task, _, _ = prepared
    original = mcp_result_store.validate_execution_response
    before = state(store)
    def mutate(*args, **kwargs):
        output = original(*args, **kwargs)
        task['approved_at'] += 1
        store.patch('tasks', task['id'], approved_at=task['approved_at'])
        return output
    monkeypatch.setattr(mcp_result_store, 'validate_execution_response', mutate)
    with pytest.raises(AdmissionError, match='task_authority_changed'):
        receive(prepared)
    assert state(store) == before


@pytest.mark.parametrize('change', ['invalid_result', 'secret', 'changed_replay'])
def test_invalid_or_conflicting_result_is_not_partially_saved(prepared, change):
    store, _, _, response = prepared
    if change == 'changed_replay':
        receive(prepared)
    response['structuredContent']['result'][0][0]['title'] = KEY.decode() if change == 'secret' else 'changed title'
    if change == 'invalid_result':
        response['structuredContent']['result'][0][-1]['check'] = 'cookie_policy'
    before = state(store)
    with pytest.raises(AdmissionError):
        receive(prepared)
    assert state(store) == before


def test_audit_failure_rolls_back_every_result_record_and_retry_remains_possible(prepared, monkeypatch):
    store = prepared[0]
    before = state(store)
    original = store.event
    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError('owned injected failure after event append')
    monkeypatch.setattr(store, 'event', fail)
    with pytest.raises(RuntimeError, match='owned injected failure'):
        receive(prepared)
    assert state(store) == before
    assert store.audit_integrity()['valid']
    monkeypatch.setattr(store, 'event', original)
    assert receive(prepared)['finding_ids']


def test_concurrent_identical_admission_returns_one_receipt_without_duplicates(prepared):
    store = prepared[0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: receive(prepared), range(2)))
    assert first == second
    assert store.count('mcp_execution_receipts') == 1
    assert store.count('traffic') == 1
    assert store.count('findings') == len(first['finding_ids'])
    assert store.count('evidence') == len(first['evidence_ids'])
    assert len(store.events(task_id=prepared[1]['id'])) == 1
    assert store.audit_integrity()['valid']


@pytest.mark.parametrize('check,expected_status', [('endpoint_inventory', 'completed'), ('api_authorization', 'skipped')])
@pytest.mark.parametrize('audit_failure', [False, True])
def test_observations_and_skipped_coverage_share_atomic_transaction(client, target, tmp_path, monkeypatch, check, expected_status, audit_failure):
    prepared = prepare(client.app.state.store, target[0], tmp_path, check)
    store = prepared[0]
    before = state(store)
    if audit_failure:
        def fail(*args, **kwargs):
            raise RuntimeError('owned audit failure')
        monkeypatch.setattr(store, 'event', fail)
        with pytest.raises(RuntimeError, match='owned audit failure'):
            receive(prepared)
        assert state(store) == before
        return
    receipt = receive(prepared)
    assert store.get('coverage', receipt['coverage_id'])['status'] == expected_status
    assert bool(receipt['observation_ids']) == (check == 'endpoint_inventory')
    for observation_id in receipt['observation_ids']:
        row = store.get('observations', observation_id)
        assert row['url'] == target[0] + '/child'
        assert row['scope_revision'] == 4 and row['task_id'] == prepared[1]['id']
    assert store.audit_integrity()['valid']
