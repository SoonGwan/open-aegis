"""Asset lifecycle must preserve evidence and invalidate stale approval scopes."""
from tests.test_validation import client, lab, register, task, finish


def test_edit_invalidates_pending_plan_without_target_request(client, lab):
    url, handler = lab
    asset = register(client, url)
    pending = task(client, asset, ['security_headers'])
    response = client.put('/api/assets/' + asset['id'], json={**asset, 'owner': 'New owner'})
    assert response.status_code == 200
    assert response.json()['revision'] == 2
    assert client.post('/api/tasks/' + pending['id'] + '/approve').status_code == 409
    assert handler.requests == []
    replacement = task(client, asset, ['security_headers'])
    assert client.post('/api/tasks/' + replacement['id'] + '/approve').status_code == 200
    assert finish(client, replacement['id'])['task']['status'] == 'completed'


def test_archive_preserves_history_and_pauses_schedules(client, lab):
    url, _ = lab
    asset = register(client, url)
    old = task(client, asset, ['security_headers'])
    client.post('/api/tasks/' + old['id'] + '/approve')
    finish(client, old['id'])
    findings = client.get('/api/findings').json()
    pending = task(client, asset, ['security_headers'])
    schedule = client.post('/api/schedules', json={'name': 'Daily', 'asset_ids': [asset['id']], 'interval_hours': 24}).json()
    path = '/api/assets/' + asset['id'] + '/archive'
    assert client.post(path, json={'archived': True}).status_code == 200
    assert client.get('/api/assets').json() == []
    assert len(client.get('/api/assets?include_archived=true').json()) == 1
    assert client.get('/api/findings').json() == findings
    assert client.get('/api/overview').json()['stats']['covered_assets'] == 0
    assert client.post('/api/tasks/' + pending['id'] + '/approve').status_code == 409
    assert client.post('/api/tasks', json={'name': 'New', 'asset_ids': [asset['id']]}).status_code == 409
    assert client.post('/api/schedules/' + schedule['id'] + '/toggle').status_code == 409
    assert client.post(path, json={'archived': False}).status_code == 200
    assert client.post('/api/tasks/' + pending['id'] + '/approve').status_code == 409
    assert client.get('/api/schedules').json()[0]['enabled'] is False
    assert client.post('/api/schedules/' + schedule['id'] + '/toggle').status_code == 200


def test_history_address_cannot_be_replaced(client, lab):
    url, _ = lab
    asset = register(client, url)
    task(client, asset, ['security_headers'])
    changed = {**asset, 'url': 'https://another.example/'}
    assert client.put('/api/assets/' + asset['id'], json=changed).status_code == 409
    assert client.get('/api/assets').json()[0]['url'] == url


def test_active_task_blocks_edit_and_archive(client, lab):
    url, _ = lab
    asset = register(client, url)
    pending = task(client, asset, ['security_headers'])
    client.app.state.store.patch('tasks', pending['id'], status='running')
    assert client.put('/api/assets/' + asset['id'], json=asset).status_code == 409
    assert client.post('/api/assets/' + asset['id'] + '/archive', json={'archived': True}).status_code == 409


def test_archive_idempotent_and_duplicate_url_rejected(client):
    first = register(client, 'https://one.example/')
    second = register(client, 'https://two.example/')
    assert client.put('/api/assets/' + second['id'], json={**second, 'url': first['url']}).status_code == 409
    path = '/api/assets/' + first['id'] + '/archive'
    a = client.post(path, json={'archived': True}).json()
    b = client.post(path, json={'archived': True}).json()
    assert a['revision'] == b['revision']
    assert client.post('/api/assets/missing/archive', json={'archived': True}).status_code == 404
