import json

from tests.test_validation import client
from tests.test_message_pages import seed


def finding(store):
    record = {'id':'cited-finding', 'task_ids':['chat-task'], 'severity':'high',
              'title':'Stored finding', 'asset_name':'Owned asset', 'remediation':'Stored fix',
              'confidence':'configuration', 'status':'open', 'evidence_ids':['secret-proof'],
              'raw_response':'must-not-copy-raw', 'fingerprint':'private-fingerprint'}
    store.put('findings', record)
    return record


def test_citations_snapshot_fields_survive_source_changes_and_retry(client):
    store = client.app.state.store
    seed(store, 0)
    finding(store)
    path = '/api/tasks/chat-task/messages'
    payload = {'content':'검증 요약', 'request_id':'cited-retry-00001'}
    response = client.post(path, json=payload)
    assert response.status_code == 200
    reply = response.json()
    provenance = reply['provenance']
    assert provenance['version'] == 1 and provenance['mode'] == 'recorded_rules'
    assert provenance['observed_at'] <= reply['created_at']
    assert provenance['finding_total'] == 1
    assert provenance['citations'] == [
        {'label':'작업', 'kind':'task', 'id':'chat-task', 'title':'chat-task',
         'snapshot':{'status':'completed','assets':0,'done':0,'completed_checks':0,'errors':0}},
        {'label':'발견 1','kind':'finding','id':'cited-finding','title':'Stored finding',
         'snapshot':{'severity':'high','confidence':'configuration','status':'open'}}]
    assert '[작업]' in reply['content'] and '[발견 1]' in reply['content']
    serialized = json.dumps(reply)
    for forbidden in ('secret-proof', 'must-not-copy-raw', 'private-fingerprint', 'Stored fix'):
        assert forbidden not in serialized
    store.patch('tasks','chat-task',status='failed',errors=9)
    store.patch('findings','cited-finding',title='Changed title',status='resolved')
    assert client.post(path,json=payload).json() == reply
    saved = client.get(path+'/page').json()['items']
    assert next(m for m in saved if m['role']=='assistant') == reply
    fresh = client.post(path,json={'content':'수정 우선순위'}).json()
    citation = fresh['provenance']['citations'][1]
    assert citation['title']=='Changed title'
    assert citation['snapshot']=={'severity':'high','asset_name':'Owned asset','remediation':'Stored fix'}


def test_summary_uses_one_sqlite_snapshot_across_concurrent_updates(client, monkeypatch):
    store = client.app.state.store
    seed(store,0)
    finding(store)
    store.patch('tasks','chat-task',created_at=1,checks=['security_headers'],
                asset_ids=['owned-asset'],scope_snapshot=[{'id':'owned-asset','revision':1}])
    store.put('coverage',{'id':'chat-task:owned-asset:security_headers','task_id':'chat-task',
                         'asset_id':'owned-asset','check':'security_headers','status':'completed'})
    get = store.get
    changed = []
    def racing_get(kind, key, **kwargs):
        record = get(kind,key,**kwargs)
        if kind=='tasks' and key=='chat-task' and not changed:
            changed.append(True)
            # Commit to the same database on another connection after the first read.
            store.patch('tasks','chat-task',status='failed',errors=7)
            store.patch('findings','cited-finding',title='Concurrent title',status='resolved')
            store.patch('coverage','chat-task:owned-asset:security_headers',status='failed')
        return record
    monkeypatch.setattr(store,'get',racing_get)
    reply = client.post('/api/tasks/chat-task/messages',json={'content':'검증 요약'}).json()
    assert changed
    assert reply['provenance']['citations'][0]['snapshot']['status']=='completed'
    assert reply['provenance']['citations'][0]['snapshot']['completed_checks']==1
    assert reply['provenance']['citations'][1]['title']=='Stored finding'
    assert reply['provenance']['citations'][1]['snapshot']['status']=='open'
    assert get('findings','cited-finding')['title']=='Concurrent title'


def test_summary_explains_bounded_selection_and_missing_task(client):
    store=client.app.state.store
    seed(store,0)
    record=finding(store)
    for i in range(9):
        store.put('findings',{**record,'id':f'cited-{i}'})
    store.put('findings',{**record,'id':'foreign','task_ids':['other'],'title':'Foreign title'})
    reply=client.post('/api/tasks/chat-task/messages',json={'content':'검증 요약'}).json()
    assert len(reply['provenance']['citations'])==9
    assert reply['provenance']['finding_total']==10
    assert '10개 중 우선순위가 높은 8개' in reply['content']
    assert 'Foreign title' not in json.dumps(reply)
    assert client.post('/api/tasks/missing/messages',json={'content':'검증 요약'}).status_code==404
