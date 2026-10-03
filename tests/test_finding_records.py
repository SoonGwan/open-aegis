"""Paged finding history must retain provenance and never materialize whole collections."""
import pytest
from tests.test_validation import client
from tests.test_identity import add, login


def populate(store, count=60):
    proof = {'asset_id': 'asset-a', 'task_id': 'task-a', 'check': 'security_headers',
             'fingerprint': 'fingerprint-a', 'created_at': 1, 'observation': {'header': 'CSP'}}
    store.put_many([('evidence', {**proof, 'id': f'proof-{i}', 'created_at': i}) for i in range(count)])
    store.put('findings', {'id': 'finding-a', 'asset_id': 'asset-a', 'check': 'security_headers',
                          'fingerprint': 'fingerprint-a', 'task_ids': ['task-a'],
                          'evidence_ids': [f'proof-{i}' for i in range(count)]})
    store.put_many([('retests', {'id': f'retest-{i}', 'finding_id': 'finding-a', 'task_id': 'task-a',
                   'conclusion': 'inconclusive', 'state_note': "사유 %_ ' OR 1=1 --", 'created_at': i}) for i in range(count)])
    return proof


def test_large_detail_and_pages_are_bounded_without_per_proof_reads(client, monkeypatch):
    store = client.app.state.store
    populate(store, 1200)
    store.put_many([('retests', {'id': f'other-{i}', 'finding_id': 'other'}) for i in range(2000)])
    monkeypatch.setattr(store, 'all', lambda *_: pytest.fail('Unbounded history read'))
    original_get = store.get
    def guarded_get(kind, id):
        assert kind != 'evidence', 'Per-proof detail read'
        return original_get(kind, id)
    monkeypatch.setattr(store, 'get', guarded_get)
    detail = client.get('/api/findings/finding-a').json()
    for kind in ('evidence', 'retests'):
        assert len(detail[kind]) == 25
        assert detail[kind + '_page']['total'] == 1200
        assert detail[kind + '_page']['has_more'] is True
        page = client.get(f'/api/findings/finding-a/{kind}?offset=1175').json()
        assert page['total'] == 1200 and len(page['items']) == 25 and not page['has_more']
    assert client.get('/api/findings/finding-a/retests', params={'search': "%_ ' OR 1=1 --"}).json()['total'] == 1200
    assert client.get('/api/findings/finding-a/evidence?search=task-a').json()['total'] == 1200


def test_evidence_membership_alone_cannot_expose_foreign_records(client):
    store = client.app.state.store
    proof = populate(store, 1)
    invalid = []
    for field, value in [('asset_id', 'foreign'), ('task_id', 'foreign'),
                         ('check', 'foreign'), ('fingerprint', 'foreign'), ('fingerprint', None)]:
        id = 'foreign-' + str(len(invalid))
        store.put('evidence', {**proof, 'id': id, field: value})
        invalid.append(id)
    store.put('evidence', {**proof, 'id': 'unreferenced'})
    store.patch('findings', 'finding-a', evidence_ids=['proof-0', 'proof-0', 'missing', *invalid])
    result = client.get('/api/findings/finding-a/evidence').json()
    assert result['total'] == 1 and [row['id'] for row in result['items']] == ['proof-0']
    assert [row['id'] for row in client.get('/api/findings/finding-a').json()['evidence']] == ['proof-0']


@pytest.mark.parametrize('kind', ['evidence', 'retests'])
def test_history_page_walk_preserves_watermark_and_live_updates(client, kind):
    store = client.app.state.store
    proof = populate(store)
    path = '/api/findings/finding-a/' + kind
    first = client.get(path).json()
    if kind == 'evidence':
        store.put(kind, {**proof, 'id': 'new'})
        store.patch('findings', 'finding-a', evidence_ids=[f'proof-{i}' for i in range(60)] + ['new'])
        store.patch(kind, 'proof-34', observation={'updated': True})
    else:
        store.put(kind, {'id': 'new', 'finding_id': 'finding-a', 'state_note': 'new'})
        store.patch(kind, 'retest-34', state_note='updated')
    pages = [first] + [client.get(path, params={'offset': offset, 'snapshot': first['snapshot']}).json() for offset in (25, 50)]
    ids = [row['id'] for page in pages for row in page['items']]
    assert len(ids) == len(set(ids)) == 60 and 'new' not in ids
    assert all(page['total'] == 60 for page in pages)
    updated = pages[1]['items'][0]
    assert updated['observation'] == {'updated': True} if kind == 'evidence' else updated['state_note'] == 'updated'
    assert client.get(path).json()['total'] == 61


def test_history_auth_not_found_and_query_bounds(client):
    populate(client.app.state.store, 1)
    for collection in ('evidence', 'retests'):
        path = '/api/findings/finding-a/' + collection
        for query in ('limit=101', 'offset=-1', 'snapshot=-1', 'search=' + 'x' * 201):
            assert client.get(path + '?' + query).status_code == 422
        assert client.get('/api/findings/missing/' + collection).status_code == 404
    viewer = add(client, 'viewer')
    with login(client.app, viewer['username']) as read:
        assert read.get('/api/findings/finding-a/evidence').json()['total'] == 1
        assert read.get('/api/findings/finding-a/retests').json()['total'] == 1
    assert client.get('/api/findings/finding-a/users').status_code == 422
    client.post('/api/auth/logout')
    assert client.get('/api/findings/finding-a/evidence').status_code == 401
