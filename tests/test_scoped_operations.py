import pytest
from aegis.store import Store
from aegis.engine import Engine
from aegis.coverage import slot
from tests.test_validation import client, register


def test_restart_recovers_all_batches_without_decoding_finished_history(tmp_path, monkeypatch):
    store = Store(tmp_path/'restart.db')
    asset = {'id':'asset','revision':1}
    tasks = [{'id':f'active-{i}','status':('running','queued','stopping')[i%3],
              'created_at':i, 'scope_snapshot':[asset], 'checks':['security_headers','cookie_policy']}
             for i in range(205)]
    history = [{'id':f'history-{i}','status':'completed','content':'x'*10000} for i in range(1100)]
    store.put_many([('tasks',t) for t in history+tasks])
    for task in tasks:
        store.put('coverage',slot(task,asset,'security_headers','completed'))
    monkeypatch.setattr(store,'all',lambda *_:pytest.fail('whole-workspace read'))
    # Coverage finalization must also avoid collecting the whole expected matrix.
    monkeypatch.setattr('aegis.coverage.task_rows',lambda *_args,**_kw:pytest.fail('matrix materialized'))
    import json
    decode = json.loads
    def scoped_decode(raw, *args, **kwargs):
        result = decode(raw, *args, **kwargs)
        if isinstance(result, dict) and str(result.get('id','')).startswith('history-'):
            pytest.fail('completed history decoded during recovery')
        return result
    monkeypatch.setattr('aegis.store.json.loads', scoped_decode)
    engine = Engine(store)
    try:
        for task in tasks:
            assert store.get('tasks',task['id'])['status'] == 'interrupted'
            assert store.get('coverage',task['id']+':asset:security_headers')['status'] == 'completed'
            assert store.get('coverage',task['id']+':asset:cookie_policy')['status'] == 'interrupted'
        assert store.count('tasks',statuses=['interrupted']) == 205
        assert store.count('tasks',statuses=['completed']) == 1100
        assert engine.metrics()['queue_watchdog']['alive']
    finally:
        engine.shutdown()


def test_recovery_keyset_excludes_new_records_and_survives_updates(tmp_path):
    store = Store(tmp_path/'cursor.db')
    store.put_many([('tasks',{'id':str(i),'status':'running'}) for i in range(205)])
    rows = store.recovery_tasks()
    first = next(rows)
    store.patch('tasks',first['id'],status='interrupted')
    store.put('tasks',{'id':'after-start','status':'queued'})
    remaining = list(rows)
    assert len(remaining) == 204
    assert {first['id'],*[row['id'] for row in remaining]} == {str(i) for i in range(205)}
    assert store.get('tasks','after-start')['status'] == 'queued'


def test_asset_guards_and_archive_use_scoped_sql(client, monkeypatch):
    store = client.app.state.store
    asset = register(client,'https://scoped.invalid/a')
    other = register(client,'https://scoped.invalid/b')
    payload = {key:asset[key] for key in ('name','url','type','authorized','owner','tags','authorization_rules')}
    store.put_many([('assets',{'id':f'history-{i}','url':f'https://history.invalid/{i}',
                            'name':'history','extra':'x'*2000}) for i in range(1100)])
    store.put_many([('tasks',{'id':f'unrelated-{i}','status':'completed','asset_ids':[other['id']]}) for i in range(1100)])
    store.put_many([('schedules',{'id':str(i),'enabled':True,'task':{'asset_ids':[asset['id']]}}) for i in range(105)])
    store.put('schedules',{'id':'unrelated','enabled':True,'task':{'asset_ids':[other['id']]}})
    store.put('schedules',{'id':'already-paused','enabled':False,'task':{'asset_ids':[asset['id']]}})
    monkeypatch.setattr(store,'all',lambda *_:pytest.fail('whole-workspace read'))
    assert client.post('/api/assets',json=payload).status_code == 409
    assert client.put('/api/assets/'+asset['id'],json={**payload,'name':'edited'}).status_code == 200
    assert client.put('/api/assets/'+asset['id'],json={**payload,'url':other['url']}).status_code == 409
    batch = [{**payload,'url':'https://scoped.invalid/new'},payload]
    assert client.post('/api/assets/import',json=batch).status_code == 409
    assert not store.asset_url_exists('https://scoped.invalid/new')
    store.put('tasks',{'id':'active','status':'running','asset_ids':[asset['id']]})
    assert client.post('/api/assets/'+asset['id']+'/archive',json={'archived':True}).status_code == 409
    store.patch('tasks','active',status='completed')
    assert client.put('/api/assets/'+asset['id'],json={**payload,'url':'https://scoped.invalid/changed'}).status_code == 409
    response = client.post('/api/assets/'+asset['id']+'/archive',json={'archived':True})
    assert response.status_code == 200 and response.json()['archived_at']
    assert all(not store.get('schedules',str(i))['enabled'] for i in range(105))
    assert store.get('schedules','unrelated')['enabled']
    assert not store.get('schedules','already-paused')['enabled']
    assert client.post('/api/assets',json=payload).status_code == 409  # Archived URLs still reserved.
    assert client.post('/api/assets/'+asset['id']+'/archive',json={'archived':False}).status_code == 200
    assert all(not store.get('schedules',str(i))['enabled'] for i in range(105))
