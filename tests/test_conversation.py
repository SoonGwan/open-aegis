import json
import pytest

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
         'snapshot':{'severity':'high','confidence':'configuration','status':'open'},'evidence':None}]
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


def seed_proofs(store):
    seed(store,0)
    finding(store)
    proof={'id':'owned-proof','task_id':'chat-task','asset_id':'owned-asset',
           'check':'security_headers','fingerprint':'owned-fingerprint','created_at':1,
           'observation':{'header':'Content-Security-Policy','present':False}}
    store.put('evidence',proof)
    store.patch('findings','cited-finding',asset_id=proof['asset_id'],check=proof['check'],
                fingerprint=proof['fingerprint'],evidence_ids=[proof['id']])
    return proof


def test_verified_evidence_excerpt_is_preserved_and_id_search_opens_exact_source(client,monkeypatch):
    store=client.app.state.store
    seed_proofs(store)
    monkeypatch.setattr(store,'all',lambda *_:pytest.fail('Unbounded citation context'))
    path='/api/tasks/chat-task/messages'
    payload={'content':'검증 요약','request_id':'proof-retry-00001'}
    reply=client.post(path,json=payload).json()
    evidence=reply['provenance']['citations'][1]['evidence']
    assert evidence['id']=='owned-proof' and evidence['task_id']=='chat-task'
    assert json.loads(evidence['excerpt'])=={'header':'Content-Security-Policy','present':False}
    assert evidence['matching_count']==1 and evidence['truncated'] is False
    assert '[증거 1]' in reply['content']
    store.patch('evidence','owned-proof',observation={'present':True})
    assert client.post(path,json=payload).json()==reply
    page=client.get('/api/findings/cited-finding/evidence',params={'search':'owned-proof'}).json()
    assert page['total']==1 and page['items'][0]['id']=='owned-proof'


@pytest.mark.parametrize('field,value',[
    ('asset_id','foreign'),('task_id','other-task'),('check','foreign'),
    ('fingerprint','foreign'),('fingerprint',None),('observation','invalid'),
    ('created_at','invalid'),('created_at',True),('created_at',-1),
])
def test_invalid_or_cross_scope_evidence_is_not_cited(client,field,value):
    store=client.app.state.store
    seed_proofs(store)
    # Even if the reference is in the finding, it must match the task and origin.
    store.patch('findings','cited-finding',task_ids=['chat-task','other-task'])
    store.patch('evidence','owned-proof',**{field:value})
    reply=client.post('/api/tasks/chat-task/messages',json={'content':'검증 요약'}).json()
    assert reply['provenance']['citations'][1]['evidence'] is None
    assert '관찰 증거를 확인할 수 없습니다' in reply['content']


def test_latest_same_task_proof_and_excerpt_limit(client):
    store=client.app.state.store
    proof=seed_proofs(store)
    store.put('evidence',{**proof,'id':'latest-owned','created_at':2,
                          'observation':{'text':'긴 관찰 값'*1000}})
    store.put('evidence',{**proof,'id':'foreign-latest','task_id':'other-task'})
    store.put('evidence',{**proof,'id':'unreferenced'})
    store.patch('findings','cited-finding',task_ids=['chat-task','other-task'],
                evidence_ids=['owned-proof','latest-owned','foreign-latest','missing'])
    reply=client.post('/api/tasks/chat-task/messages',json={'content':'검증 요약'}).json()
    evidence=reply['provenance']['citations'][1]['evidence']
    assert evidence['id']=='latest-owned' and evidence['matching_count']==2
    assert len(evidence['excerpt'])==4096 and evidence['truncated'] is True


def test_proof_read_shares_task_snapshot(client,monkeypatch):
    store=client.app.state.store
    seed_proofs(store)
    get=store.get
    changed=[]
    def racing_get(kind,key,**kwargs):
        record=get(kind,key,**kwargs)
        if kind=='tasks' and not changed:
            changed.append(True)
            store.patch('evidence','owned-proof',observation={'concurrent':True})
        return record
    monkeypatch.setattr(store,'get',racing_get)
    reply=client.post('/api/tasks/chat-task/messages',json={'content':'검증 요약'}).json()
    assert json.loads(reply['provenance']['citations'][1]['evidence']['excerpt'])['present'] is False
    assert get('evidence','owned-proof')['observation']=={'concurrent':True}
