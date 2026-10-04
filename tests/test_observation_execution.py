"""Explicit owned observed URL requests, distinct proof and original-URL retests."""
import copy
import json
from concurrent.futures import ThreadPoolExecutor
import pytest

from aegis.worker_observations import record_link
from tests.test_validation import client, lab, finish
from tests.test_next_plan import completed
from tests.test_identity import add, login


def selected(client, lab, extra=()):
    original, _ = completed(client, lab, ['endpoint_inventory'])
    source = client.app.state.store.get('tasks', original['id'])
    for path in extra:
        record_link(client.app.state.store, source, source['scope_snapshot'][0], 'endpoint_inventory', lab[0]+path)
    path = '/api/tasks/'+original['id']+'/observation-plan'
    preview = client.get(path)
    assert preview.status_code == 200, preview.text
    context = preview.json()['context']
    selection = {'fingerprint':context['fingerprint'], 'observation_ids':[r['id'] for r in context['items']],
                 'checks':['security_headers', 'cookie_policy'], 'request_id':'a'*32}
    return original, path, selection


def test_selected_requests_are_approval_gated_frozen_once_and_distinct_from_base_coverage(client, lab):
    original, path, body = selected(client, lab, ['login'])
    before = list(lab[1].requests)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _:client.post(path, json=body), range(2)))
    assert all(r.status_code == 200 for r in replies), [r.text for r in replies]
    plan = replies[0].json()
    assert replies[1].json()['id'] == plan['id']
    assert plan['status'] == 'pending' and not plan['approved_at'] and lab[1].requests == before
    changed = {**body, 'checks':['transport_security']}
    assert client.post(path, json=changed).status_code == 409
    store = client.app.state.store
    source = store.get('tasks', original['id'])
    record_link(store, source, source['scope_snapshot'][0], 'endpoint_inventory', lab[0]+'admin')
    assert client.post(path, json=body).json()['id'] == plan['id']
    assert client.post('/api/tasks/'+plan['id']+'/approve').status_code == 200
    result = finish(client, plan['id'])
    assert set(lab[1].requests[len(before):]) == {'/login', '/api/account'}
    assert len(lab[1].requests) == len(before)+2  # Responses reused between checks.
    assert all(row['status'] == 'completed' and len(row['targets']) == 2 for row in result['coverage'])
    findings = [f for f in result['findings'] if f['check'] == 'security_headers']
    assert findings and all(f['code'].startswith('observed-') for f in findings)
    assert {store.get('evidence', store.get('findings', f['id'])['evidence_ids'][-1])['observation']['requested_url'] for f in findings} == {lab[0]+'login', lab[0]+'api/account'}
    assert client.get('/api/tasks/'+plan['id']+'/next-plan').status_code == 409
    coverage = client.get('/api/overview').json()['coverage_summary']
    assert coverage['completed'] == 1  # Only original endpoint inventory, no base-response claim.


@pytest.mark.parametrize('change', ['observation', 'asset', 'missing_id'])
def test_changed_input_refuses_pending_creation(client, lab, change):
    original, path, body = selected(client, lab)
    store = client.app.state.store
    if change == 'observation':store.patch('observations', body['observation_ids'][0], verified=True)
    elif change == 'asset':store.patch('assets', original['asset_ids'][0], revision=2)
    else:body['observation_ids'] = ['unknown']
    before = list(lab[1].requests)
    assert client.post(path, json=body).status_code == 409
    assert store.count('tasks') == 1 and lab[1].requests == before


def test_selection_validation_and_roles_and_approval_tampering(client, lab):
    original, path, body = selected(client, lab)
    for changed in ({**body, 'checks':['api_authorization']}, {**body, 'observation_ids':body['observation_ids']*2},
                    {**body, 'observation_ids':body['observation_ids']*11}, {**body, 'url':lab[0]+'other'}):
        assert client.post(path, json=changed).status_code == 422
    viewer = add(client, 'viewer')
    with login(client.app, viewer['username']) as read:
        assert read.get(path).status_code == 200
        assert read.post(path, json=body).status_code == 403
    plan = client.post(path, json=body).json()
    damaged = copy.deepcopy(plan['observation_execution'])
    damaged['targets'][0]['url'] = lab[0]+'unselected'
    client.app.state.store.patch('tasks', plan['id'], observation_execution=damaged)
    before = list(lab[1].requests)
    assert client.post('/api/tasks/'+plan['id']+'/approve').status_code == 409
    assert lab[1].requests == before


def test_observed_finding_retest_uses_same_endpoint_and_preserves_source_evidence(client, lab):
    _, path, body = selected(client, lab, ['login'])
    body['observation_ids'] = [id for id in body['observation_ids']
        if client.app.state.store.get('observations', id)['url'] == lab[0]+'login']
    plan = client.post(path, json=body).json()
    client.post('/api/tasks/'+plan['id']+'/approve')
    result = finish(client, plan['id'])
    finding = next(f for f in result['findings'] if f['check'] == 'security_headers')
    evidence = client.get('/api/findings/'+finding['id']).json()['evidence']
    lab[1].hardened = True
    retest = client.post('/api/findings/'+finding['id']+'/retest')
    assert retest.status_code == 200, retest.text
    retry = retest.json()
    assert retry['observation_execution']['observation_ids'] == [finding['observation_id']]
    before = list(lab[1].requests)
    assert client.post('/api/tasks/'+retry['id']+'/approve').status_code == 200
    finish(client, retry['id'])
    assert lab[1].requests[len(before):] == ['/login']
    detail = client.get('/api/findings/'+finding['id']).json()
    assert detail['finding']['status'] == 'resolved' and detail['evidence'] == evidence


def test_failed_observed_response_is_not_completed_and_retry_retains_selection(client, lab):
    _, path, body = selected(client, lab)
    plan = client.post(path, json=body).json()
    lab[1].fault = True
    client.post('/api/tasks/'+plan['id']+'/approve')
    result = finish(client, plan['id'])
    assert result['task']['status'] == 'failed'
    assert all(row['status'] == 'failed' and row['targets'][0]['status'] == 'failed' for row in result['coverage'])
    lab[1].fault = False
    retry = client.post('/api/tasks/'+plan['id']+'/retry')
    assert retry.status_code == 200, retry.text
    assert retry.json()['observation_execution']['observation_ids'] == body['observation_ids']
    client.post('/api/tasks/'+retry.json()['id']+'/approve')
    assert finish(client, retry.json()['id'])['task']['status'] == 'completed'
    client.app.state.store.patch('observations', body['observation_ids'][0], verified=True)
    assert client.post('/api/tasks/'+plan['id']+'/retry').json()['id'] == retry.json()['id']


def test_replacement_preserves_selected_urls_but_requires_new_approval(client, lab):
    _, path, body = selected(client, lab)
    plan = client.post(path, json=body).json()
    before = list(lab[1].requests)
    replacement = client.post('/api/tasks/'+plan['id']+'/replan')
    assert replacement.status_code == 200, replacement.text
    assert replacement.json()['observation_execution']['observation_ids'] == body['observation_ids']
    assert replacement.json()['status'] == 'pending' and lab[1].requests == before


def test_one_failed_url_keeps_successful_proof_but_fails_the_check(client, lab, monkeypatch):
    _, path, body = selected(client, lab, ['login'])
    original = lab[1].do_GET
    def respond(handler):
        if handler.path == '/api/account':
            type(handler).requests.append(handler.path)
            handler.send_response(503); handler.end_headers()
        else:original(handler)
    monkeypatch.setattr(lab[1], 'do_GET', respond)
    plan = client.post(path, json=body).json()
    before = list(lab[1].requests)
    client.post('/api/tasks/'+plan['id']+'/approve')
    result = finish(client, plan['id'])
    assert result['task']['status'] == 'failed'
    requests = lab[1].requests[len(before):]
    assert requests.count('/login') == 1 and requests.count('/api/account') == 2
    assert len(requests) == 3  # One transport retry, not a new GET for the second check.
    assert all({row['status'] for row in cell['targets']} == {'completed', 'failed'} and cell['status'] == 'failed'
               for cell in result['coverage'])
    assert result['findings'] and all(client.app.state.store.get('observations', f['observation_id'])['url'] == lab[0]+'login'
                                      for f in result['findings'])


def test_denied_response_retest_is_inconclusive_instead_of_resolving(client, lab):
    _, path, body = selected(client, lab)
    plan = client.post(path, json=body).json()
    client.post('/api/tasks/'+plan['id']+'/approve')
    finding = next(f for f in finish(client, plan['id'])['findings'] if f['check'] == 'security_headers')
    lab[1].hardened = True  # Owned API now returns403; this is not a header success.
    retry = client.post('/api/findings/'+finding['id']+'/retest').json()
    client.post('/api/tasks/'+retry['id']+'/approve');finish(client, retry['id'])
    detail = client.get('/api/findings/'+finding['id']).json()
    assert detail['finding']['status'] == 'open' and detail['retests'][0]['conclusion'] == 'inconclusive'


def test_selected_redirect_uses_existing_scope_guard(client, lab):
    _, path, body = selected(client, lab, ['redirect-outside'])
    body['observation_ids'] = [id for id in body['observation_ids']
        if client.app.state.store.get('observations', id)['url'] == lab[0]+'redirect-outside']
    plan = client.post(path, json=body).json()
    before = list(lab[1].requests)
    client.post('/api/tasks/'+plan['id']+'/approve')
    result = finish(client, plan['id'])
    assert result['task']['status'] == 'failed'
    assert lab[1].requests[len(before):] == ['/redirect-outside']
    assert all(cell['targets'][0]['error_type'] == 'ScopeError' for cell in result['coverage'])


def test_final_write_rechecks_observations_and_rolls_back_pending_records(client, lab, monkeypatch):
    from aegis import observation_execution
    _, path, body = selected(client, lab)
    store = client.app.state.store
    original = observation_execution.prepare
    def change_at_commit(*args, **kwargs):
        db = kwargs.get('connection')
        if db is not None:
            row = store.get('observations', body['observation_ids'][0], connection=db)
            marker = '%s' if getattr(store,'backend',None) == 'postgres' else '?'
            db.execute(f"UPDATE records SET data={marker} WHERE kind='observations' AND id={marker}",
                       (json.dumps({**row, 'verified':True}), row['id']))
        return original(*args, **kwargs)
    monkeypatch.setattr(observation_execution, 'prepare', change_at_commit)
    before = list(lab[1].requests)
    assert client.post(path, json=body).status_code == 409
    assert store.count('tasks') == 1 and lab[1].requests == before
    assert store.get('observations', body['observation_ids'][0])['verified'] is False
