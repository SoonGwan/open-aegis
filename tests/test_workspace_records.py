"""Workspace lists stay bounded and scheduled work cannot hide behind future rows."""
import time

import pytest

from aegis.store import Store
from tests.test_validation import client, lab, register
from tests.test_identity import add, login


def test_notes_search_pages_and_legacy_limits(client, monkeypatch):
    store = client.app.state.store
    store.put_many([('notes', {'id': str(i), 'title': f'Note {i}',
                             'content': "복구 %_ ' OR 1=1 --", 'created_at': i}) for i in range(1050)])
    monkeypatch.setattr(store, 'all', lambda *_: pytest.fail('Unbounded workspace read'))
    first = client.get('/api/records/notes', params={'search': "%_ ' OR 1=1 --"}).json()
    assert first['total'] == 1050 and len(first['items']) == 25
    assert first['items'][0]['id'] == '1049'
    store.put('notes', {'id': 'new', 'title': 'New', 'content': '복구'})
    store.patch('notes', '1024', title='Updated')
    second = client.get('/api/records/notes', params={'offset': 25, 'snapshot': first['snapshot']}).json()
    assert second['total'] == 1050 and second['items'][0]['id'] == '1024'
    assert second['items'][0]['title'] == 'Updated'
    legacy = client.get('/api/notes')
    assert len(legacy.json()) == 1000
    assert legacy.headers['X-Total-Count'] == '1051'
    assert legacy.headers['X-Results-Limited'] == 'true'
    assert client.get('/api/records/notes?enabled=true').status_code == 422


def test_schedule_nested_search_asset_and_enabled_filters(client, monkeypatch):
    store = client.app.state.store
    store.put_many([('schedules', {'id': str(i), 'task': {'name': f'주간 검증 {i}',
                         'goal': '복구 정책', 'asset_ids': ['asset-a' if i % 2 else 'asset-b']},
                         'enabled': bool(i % 2), 'next_at': time.time() + 86400}) for i in range(1100)])
    monkeypatch.setattr(store, 'all', lambda *_: pytest.fail('Unbounded workspace read'))
    result = client.get('/api/records/schedules?search=복구&asset_id=asset-a&enabled=true').json()
    assert result['total'] == 550 and len(result['items']) == 25
    assert all(row['enabled'] and row['task']['asset_ids'] == ['asset-a'] for row in result['items'])
    assert client.get('/api/records/schedules?enabled=false').json()['total'] == 550
    assert client.get('/api/records/schedules?enabled=garbage').status_code == 422
    assert client.get('/api/records/schedules?search=복구&asset_id=asset-a&enabled=false').json()['total'] == 0
    legacy = client.get('/api/schedules')
    assert len(legacy.json()) == 1000 and legacy.headers['X-Total-Count'] == '1100'
    assert legacy.headers['X-Results-Limited'] == 'true'


def test_due_batches_prioritize_oldest_without_starving_later_due_work(tmp_path, monkeypatch):
    store = Store(tmp_path / 'due.db')
    store.put_many([('schedules', {'id': str(i), 'enabled': True, 'next_at': i}) for i in range(150)])
    store.put_many([('schedules', {'id': 'future-' + str(i), 'enabled': True, 'next_at': 10000}) for i in range(200)])
    store.put('schedules', {'id': 'paused', 'enabled': False, 'next_at': -100})
    monkeypatch.setattr(store, 'all', lambda *_: pytest.fail('Unbounded scheduler read'))
    first = store.due_schedules(200)
    assert [row['id'] for row in first] == [str(i) for i in range(100)]
    for row in first:
        store.patch('schedules', row['id'], next_at=10000)
    assert [row['id'] for row in store.due_schedules(200)] == [str(i) for i in range(100, 150)]
    with store.connect() as db:
        plan = db.execute("EXPLAIN QUERY PLAN SELECT data FROM records WHERE kind='schedules' AND json_extract(data,'$.enabled')=1 AND json_extract(data,'$.next_at')<=? ORDER BY json_extract(data,'$.next_at'),rowid LIMIT ?", (200, 100)).fetchall()
    assert any('records_schedule_due' in row['detail'] for row in plan)


def test_due_schedule_creates_pending_plan_without_http(client, lab, monkeypatch):
    url, handler = lab
    asset = register(client, url)
    schedule = client.post('/api/schedules', json={'name': 'Due fixture', 'asset_ids': [asset['id']], 'interval_hours': 24}).json()
    store = client.app.state.store
    store.patch('schedules', schedule['id'], next_at=0)
    monkeypatch.setattr(store, 'all', lambda *_: pytest.fail('Unbounded scheduler read'))
    deadline = time.monotonic() + 8
    while store.get('schedules', schedule['id'])['last_at'] is None and time.monotonic() < deadline:
        time.sleep(.05)
    assert store.count('tasks') == 1
    task = store.page('tasks')['items'][0]
    assert task['status'] == 'pending' and task['schedule_id'] == schedule['id']
    assert handler.requests == []
    assert store.get('schedules', schedule['id'])['last_at'] is not None


def test_viewer_reads_workspace_pages_but_cannot_change_them(client):
    viewer = add(client, 'viewer')
    with login(client.app, viewer['username']) as read:
        assert read.get('/api/records/notes').status_code == 200
        assert read.get('/api/records/schedules').status_code == 200
        assert read.post('/api/notes', json={'title': 'No', 'content': 'No'}).status_code == 403
        assert read.post('/api/schedules/missing/toggle').status_code == 403
        assert read.delete('/api/notes/missing').status_code == 403
