import copy
from concurrent.futures import Future

import pytest

from aegis import tool_contracts
from aegis.checks import issue
from aegis.tool_contracts import contracts_for, validate_result, ToolContractError
from tests.test_validation import client, lab, register, task, finish


def finding(check='security_headers'):
    return issue(check, 'fixture', 'Synthetic result', 'low', {'present': False}, 'Review fixture')


def test_contract_snapshot_is_deterministic_and_independent():
    first = contracts_for(['security_headers', 'endpoint_inventory'])
    assert first['package_sha256'] == tool_contracts._source_fingerprint()
    assert len(first['package_sha256']) == 64
    second = copy.deepcopy(first)
    first['checks'][0]['permissions'].append('shell')
    assert contracts_for(['security_headers', 'endpoint_inventory']) == second
    for invalid in ([], ['unknown'], ['security_headers', 'security_headers'], [None], 'security_headers'):
        with pytest.raises(ToolContractError):
            contracts_for(invalid)


@pytest.mark.parametrize('damage', ['missing', 'version', 'fingerprint', 'boolean_version', 'float_version', 'extra_field'])
def test_stale_or_legacy_approval_sends_no_requests(client, lab, damage):
    url, handler = lab
    plan = task(client, register(client, url), ['security_headers'])
    manifest = copy.deepcopy(plan['tool_contracts'])
    if damage == 'missing': manifest = None
    elif damage == 'version': manifest['checks'][0]['version'] += 1
    elif damage == 'boolean_version': manifest['checks'][0]['version'] = True
    elif damage == 'float_version': manifest['checks'][0]['version'] = 1.0
    elif damage == 'extra_field': manifest['unexpected'] = 'reject'
    else: manifest['package_sha256'] = '0' * 64
    client.app.state.store.patch('tasks', plan['id'], tool_contracts=manifest)
    response = client.post('/api/tasks/' + plan['id'] + '/approve')
    assert response.status_code == 409 and '새 계획' in response.json()['detail']
    assert client.app.state.store.get('tasks', plan['id'])['status'] == 'pending'
    assert handler.requests == []


def test_contract_recheck_precedes_planner_and_target_requests(client, lab, monkeypatch):
    url, handler = lab
    engine = client.app.state.engine
    monkeypatch.setattr(engine.pool, 'submit', lambda *_: Future())
    plan = task(client, register(client, url), ['security_headers'])
    assert client.post('/api/tasks/' + plan['id'] + '/approve').status_code == 200
    monkeypatch.setattr(tool_contracts, 'PACKAGE_SHA256', '0' * 64)
    monkeypatch.setattr(engine, 'plan', lambda *_: pytest.fail('Planner called after contract changed'))
    engine.run(plan['id'])
    detail = client.get('/api/tasks/' + plan['id']).json()
    assert detail['task']['status'] == 'failed'
    assert detail['task']['termination_reason'] == 'tool_contract_changed'
    assert all(row['status'] == 'failed' for row in detail['coverage'])
    assert handler.requests == []


def test_complete_result_rejected_before_any_finding_is_saved(client, lab, monkeypatch):
    url, handler = lab
    plan = task(client, register(client, url), ['security_headers'])
    bad = finding('cookie_policy')
    bad['title'] = 'SYNTHETIC_PRIVATE_RESULT_MARKER'
    monkeypatch.setattr('aegis.engine.run_check', lambda *_: ([finding(), bad], [], None))
    assert client.post('/api/tasks/' + plan['id'] + '/approve').status_code == 200
    detail = finish(client, plan['id'])
    assert detail['task']['status'] == 'failed'
    assert detail['findings'] == []
    assert detail['coverage'][0]['error_type'] == 'ToolContractError'
    assert len(handler.requests) == 1
    store = client.app.state.store
    assert store.count('findings') == 0 and store.count('evidence') == 0
    assert 'SYNTHETIC_PRIVATE_RESULT_MARKER' not in str(store.event_page(plan['id']))


@pytest.mark.parametrize('result', [
    ([finding()] * 129, [], None),
    ([{**finding(), 'extra': 'reject'}], [], None),
    ([{**finding(), 'evidence': {'value': float('nan')}}], [], None),
    ([{**finding(), 'evidence': {'value': 'x' * (512 * 1024)}}], [], None),
    ([finding()], [], 'skipped with partial results'),
    ([], ['https://outside.invalid/'], None),
    ([], ['https://owned.invalid/app/?token=private'], None),
])
def test_result_count_shape_size_and_observation_scope_reject(result):
    check = 'endpoint_inventory' if result[1] else 'security_headers'
    with pytest.raises(ToolContractError):
        validate_result(check, {'url': 'https://owned.invalid/app/'}, result)


def test_valid_builtin_result_and_scoped_observation_are_preserved():
    output = ([finding()], [], None)
    assert validate_result('security_headers', {'url': 'https://owned.invalid/app/'}, output) == output
    links = ([], ['https://owned.invalid/app/next'], None)
    assert validate_result('endpoint_inventory', {'url': 'https://owned.invalid/app/'}, links) == links
    assert validate_result('api_authorization', {'url': 'https://owned.invalid/app/'}, ([], [], 'no rules')) == ([], [], 'no rules')
