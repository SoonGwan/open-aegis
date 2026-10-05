"""Bounded reads must stay correct under inserts, updates and literal search input."""
import json
import pytest
from aegis.store import Store
from tests.test_validation import client


def test_page_watermark_survives_updates_and_new_inserts(tmp_path):
    store = Store(tmp_path / 'records.db')
    for index in range(60):
        store.put('tasks', {'id': str(index), 'name': f'작업 {index}', 'status': 'pending'})
    first = store.page('tasks')
    store.patch('tasks', '20', name='수정한 작업')
    store.put('tasks', {'id': 'new', 'name': '새 작업', 'status': 'pending'})
    pages = [first] + [store.page('tasks', offset=offset, snapshot=first['snapshot']) for offset in (25, 50)]
    ids = [item['id'] for page in pages for item in page['items']]
    assert ids == [str(index) for index in reversed(range(60))]
    assert len(set(ids)) == 60
    assert all(page['total'] == 60 for page in pages)
    assert store.page('tasks')['items'][0]['id'] == 'new'
    assert next(item for page in pages for item in page['items'] if item['id'] == '20')['name'] == '수정한 작업'


def test_large_query_never_materializes_entire_collection(tmp_path, monkeypatch):
    store = Store(tmp_path / 'large.db')
    with store.connect() as db:
        db.executemany('INSERT INTO records VALUES (?,?,?)',
                       [('traffic', str(index), json.dumps({'id': str(index), 'url': f'https://example.test/{index}', 'task_id': 'a' if index % 2 else 'b'})) for index in range(15_000)])
    monkeypatch.setattr(store, 'all', lambda *_: pytest.fail('Unbounded read'))
    result = store.page('traffic', search='example.test', filters={'task_id': 'a'})
    assert result['total'] == 7500
    assert len(result['items']) == 25 and result['has_more']
    assert len(json.dumps(result).encode()) < 6000
    assert store.count('traffic') == 15_000


def test_literal_search_filters_and_archive(tmp_path):
    store = Store(tmp_path / 'search.db')
    store.put('assets', {'id': 'a', 'name': "100%_ ' OR 1=1 --", 'url': 'https://a.test', 'owner': '개발팀', 'archived_at': None})
    store.put('assets', {'id': 'b', 'name': 'Normal', 'archived_at': 123})
    assert store.page('assets', search="%_ ' OR 1=1 --")['total'] == 1
    assert store.page('assets', search='개발팀', archived=False)['items'][0]['id'] == 'a'
    assert store.page('assets', archived=True)['items'][0]['id'] == 'b'
    store.put('findings', {'id': 'f', 'title': 'Header', 'task_ids': ['t1', 't2'], 'severity': 'medium'})
    assert store.page('findings', filters={'task_id': 't2', 'severity': 'medium'})['total'] == 1
    assert store.page('findings', filters={'task_id': 't3'})['total'] == 0
    with pytest.raises(ValueError):
        store.page('settings')
    with pytest.raises(ValueError):
        store.page('tasks', filters={"id') OR 1=1 --": 'x'})


def test_records_api_auth_bounds_and_no_private_collections(client):
    assert client.get('/api/records/tasks?limit=101').status_code == 422
    assert client.get('/api/records/tasks?offset=-1').status_code == 422
    assert client.get('/api/records/tasks?snapshot=-1').status_code == 422
    assert client.get('/api/records/tasks?archived=true').status_code == 200
    assert client.get('/api/records/tasks?archived=true').json()['items'] == []
    assert client.get('/api/records/notes?archived=true').status_code == 422
    for kind in ('users', 'settings', 'sessions', 'evidence'):
        assert client.get('/api/records/' + kind).status_code == 422
    assert client.get('/api/records/tasks').json()['items'] == []
    client.post('/api/auth/logout')
    assert client.get('/api/records/tasks').status_code == 401


def test_overview_and_legacy_arrays_are_bounded_with_complete_counts(client, monkeypatch):
    store = client.app.state.store
    for index in range(1050):
        store.put('tasks', {'id': str(index), 'name': f'Task {index}', 'status': 'pending'})
    monkeypatch.setattr(store, 'all', lambda *_: pytest.fail('Unbounded overview read'))
    response = client.get('/api/overview')
    assert response.status_code == 200
    assert len(response.json()['tasks']) == 100
    assert response.json()['stats']['tasks'] == 1050
    assert response.json()['stats']['pending'] == 1050
    legacy = client.get('/api/tasks')
    assert len(legacy.json()) == 1000
    assert legacy.headers['X-Total-Count'] == '1050'
    assert legacy.headers['X-Results-Limited'] == 'true'
    page = client.get('/api/records/tasks?search=Task&status=pending&offset=1000').json()
    assert page['total'] == 1050 and len(page['items']) == 25


def test_asset_history_count_and_severity_stats_do_not_use_preview_slice(client):
    store = client.app.state.store
    store.put('assets', {'id': 'old', 'name': 'Old asset', 'archived_at': None})
    store.put('coverage', {'id': 'old-proof', 'asset_id': 'old', 'check': 'security_headers', 'status': 'completed'})
    for index in range(110):
        store.put('coverage', {'id': str(index), 'asset_id': 'other', 'check': 'security_headers'})
        store.put('findings', {'id': str(index), 'severity': 'high', 'status': 'open'})
    store.put('findings', {'id': 'critical', 'severity': 'critical', 'status': 'open'})
    asset = client.get('/api/records/assets').json()['items'][0]
    assert asset['completed_check_count'] == 1
    overview = client.get('/api/overview').json()
    assert len(overview['coverage']) == 100
    assert overview['stats']['findings_high'] == 110
    assert overview['stats']['findings_critical'] == 1
    assert overview['stats']['findings'] == 111
