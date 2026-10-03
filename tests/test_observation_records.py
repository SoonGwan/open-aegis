"""Observed links remain metadata and their full counts cannot come from previews."""
import pytest
from tests.test_validation import client
from tests.test_identity import add, login


def populate(store, count=1050):
    store.put('assets', {'id': 'asset-a', 'name': '운영 포털', 'archived_at': 123})
    store.put('tasks', {'id': 'task-a', 'name': '승인된 관찰 검수', 'status': 'completed'})
    store.put_many([('observations', {'id': str(i), 'asset_id': 'asset-a', 'task_id': 'task-a',
                    'url': f'https://example.test/links/{i}', 'created_at': i, 'verified': False}) for i in range(count)])


def test_full_count_search_sources_and_page_are_bounded(client, monkeypatch):
    store = client.app.state.store
    populate(store)
    monkeypatch.setattr(store, 'all', lambda *_: pytest.fail('Unbounded observation read'))
    overview = client.get('/api/overview').json()
    assert len(overview['observations']) == 100
    assert overview['stats']['observations'] == 1050
    for search in ('운영 포털', '승인된 관찰', 'asset-a', 'task-a', 'example.test'):
        result = client.get('/api/records/observations', params={'search': search, 'offset': 1000}).json()
        assert result['total'] == 1050 and len(result['items']) == 25
        assert result['items'][0]['asset_name'] == '운영 포털'
        assert result['items'][0]['task_name'] == '승인된 관찰 검수'
    assert client.get('/api/records/observations?asset_id=asset-a&task_id=other').json()['total'] == 0
    assert client.get('/api/records/observations?asset_id=asset-a&task_id=task-a').json()['total'] == 1050
    assert store.count('traffic') == 0


def test_unknown_sources_and_literal_search_do_not_drop_observation(client):
    store = client.app.state.store
    store.put('observations', {'id': 'orphan', 'asset_id': 'missing', 'task_id': 'missing',
                               'url': "https://example.test/%_ ' OR 1=1 --", 'created_at': 1})
    result = client.get('/api/records/observations', params={'search': "%_ ' OR 1=1 --"}).json()
    assert result['total'] == 1
    assert result['items'][0]['asset_name'] is None and result['items'][0]['task_name'] is None
    assert client.get('/api/records/observations?search=no-match').json()['total'] == 0


def test_observation_updates_keep_order_and_source_names_live(client):
    store = client.app.state.store
    populate(store, 60)
    first = client.get('/api/records/observations').json()
    store.put('observations', {'id': 'new', 'asset_id': 'asset-a', 'task_id': 'task-a', 'url': 'https://example.test/new'})
    store.patch('observations', '34', url='https://example.test/updated', created_at=999)
    store.patch('assets', 'asset-a', name='포털 새 이름')
    pages = [first] + [client.get('/api/records/observations', params={'offset': offset, 'snapshot': first['snapshot']}).json() for offset in (25, 50)]
    ids = [item['id'] for page in pages for item in page['items']]
    assert ids == [str(i) for i in reversed(range(60))]
    assert all(page['total'] == 60 for page in pages)
    assert pages[1]['items'][0]['url'] == 'https://example.test/updated'
    assert pages[1]['items'][0]['asset_name'] == '포털 새 이름'
    assert client.get('/api/records/observations').json()['total'] == 61


def test_observation_permissions_and_bounds(client):
    populate(client.app.state.store, 1)
    for query in ('limit=101', 'offset=-1', 'snapshot=-1', 'enabled=true', 'archived=true', 'search=' + 'x' * 201):
        assert client.get('/api/records/observations?' + query).status_code == 422
    viewer = add(client, 'viewer')
    with login(client.app, viewer['username']) as read:
        assert read.get('/api/records/observations').json()['total'] == 1
    client.post('/api/auth/logout')
    assert client.get('/api/records/observations').status_code == 401
