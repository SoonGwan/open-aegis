"""Atomic organizational changes preserve execution snapshots and worker results."""
import copy
import pytest
from tests.test_mcp_registry import client
from tests.test_postgres_transfer import postgres
from tests.test_validation import lab,register,task,finish
from tests.test_identity import add,login

BASE='/api/task-categories'
ASSIGN='/api/tasks/category-assignment'


@pytest.mark.parametrize('operation',['create','assign'])
def test_short_request_id_rejected_before_category_mutation(client,lab,operation):
    category=create(client);planned=task(client,register(client,lab[0]),['security_headers']);store=client.app.state.store
    if operation=='create':response=client.post(BASE,json={'name':'Other','request_id':'short'})
    else:response=client.post(ASSIGN,json=request(category,[planned],request_id='short'))
    assert response.status_code==422,response.text
    assert store.count('task_categories')==1 and store.count('task_category_history')==store.count('task_category_operations')==0
    assert store.get('tasks',planned['id'])==planned and not lab[1].requests


def create(client,name='Deployment',request_id='category-create-001'):
    response=client.post(BASE,json={'name':name,'request_id':request_id});assert response.status_code==200,response.text
    return response.json()['category']


def request(category,tasks,**changes):
    return {'category_id':category['id'] if category else None,'task_ids':[t['id'] for t in tasks],
        'expected_revisions':{t['id']:t.get('category_revision',0) for t in tasks},'request_id':'category-assign-001',**changes}


def test_category_revisions_archive_unique_names_and_replayed_create(client):
    category=create(client);route=BASE+'/'+category['id']
    assert client.post(BASE,json={'name':'DEPLOYMENT','request_id':'category-other-001'}).status_code==409
    renamed=client.put(route,json={'name':'Release checks','expected_revision':1}).json();assert renamed['revision']==2
    assert client.put(route,json={'name':'Old edit','expected_revision':1}).status_code==409
    archived=client.post(route+'/archive',json={'expected_revision':2,'archived':True}).json();assert archived['revision']==3
    assert client.get(BASE).json()['total']==0
    assert client.get(BASE,params={'status':'archived'}).json()['total']==1
    assert client.post(route+'/archive',json={'expected_revision':3,'archived':False}).json()['revision']==4
    history=client.get(route+'/history').json();assert history['total']==4
    assert next(r['snapshot'] for r in history['items'] if r['revision']==1)==category
    replay=client.post(BASE,json={'name':'Deployment','request_id':'category-create-001'}).json()
    assert replay['replayed'] and replay['category']['revision']==4


def test_bulk_assignment_atomic_history_replay_clear_and_execution_scope_unchanged(client,lab):
    asset=register(client,lab[0]);tasks=[task(client,asset,['security_headers']) for _ in range(2)];category=create(client)
    original=copy.deepcopy(tasks);data=request(category,tasks)
    response=client.post(ASSIGN,json=data);assert response.status_code==200,response.text
    result=response.json();assert not result['execution_authorized'] and len(result['assignments'])==2
    changed=[]
    for before in original:
        after=client.get('/api/tasks/'+before['id']).json()['task'];changed.append(after)
        assert {k:v for k,v in after.items() if k not in ('category_ref','category_revision')}==before
        assert after['category_revision']==1 and after['category_ref']['name']=='Deployment'
        history=client.get('/api/tasks/'+before['id']+'/category-history').json()
        assert history['total']==1 and history['items'][0]['before'] is None
    replay=client.post(ASSIGN,json={**data,'task_ids':list(reversed(data['task_ids']))}).json();assert replay['replayed']
    assert client.app.state.store.count('task_category_history')==2
    assert client.post(ASSIGN,json={**data,'category_id':None}).status_code==409
    assert client.post(ASSIGN,json=request(None,changed,request_id='category-clear-001')).status_code==200
    assert all(client.get('/api/tasks/'+t['id']).json()['task']['category_ref'] is None for t in tasks)
    assert not lab[1].requests and client.app.state.store.audit_integrity()['valid']


@pytest.mark.parametrize('change',['stale','missing','archived'])
def test_one_invalid_member_rolls_back_entire_batch(client,lab,change):
    asset=register(client,lab[0]);tasks=[task(client,asset,['security_headers']) for _ in range(2)];category=create(client)
    payload=request(category,tasks)
    if change=='stale':payload['expected_revisions'][tasks[1]['id']]=1
    elif change=='missing':payload['task_ids'][1]='missing';payload['expected_revisions']={tasks[0]['id']:0,'missing':0}
    else:client.post(BASE+'/'+category['id']+'/archive',json={'expected_revision':1,'archived':True})
    response=client.post(ASSIGN,json=payload);assert response.status_code==(404 if change=='missing' else 409),response.text
    store=client.app.state.store
    assert [store.get('tasks',t['id']) for t in tasks]==tasks
    assert store.count('task_category_operations')==store.count('task_category_history')==0 and not lab[1].requests


@pytest.mark.parametrize('operation',['create','edit','archive','assign'])
def test_audit_failure_reverts_records_versions_all_tasks_and_receipt(client,lab,monkeypatch,operation):
    category=create(client);asset=register(client,lab[0]);tasks=[task(client,asset,['security_headers']) for _ in range(2)]
    store=client.app.state.store;client.app.state.event_planner.close()
    kinds=('task_categories','task_category_versions','tasks','task_category_history','task_category_operations')
    before={kind:store.all(kind) for kind in kinds};original=store.event;audit=store.audit_integrity()
    def fail(task_id,message,*args,**kwargs):
        if message.startswith('작업 분류'):raise RuntimeError('Owned category audit failure')
        return original(task_id,message,*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(store,'event',fail)
        with pytest.raises(RuntimeError,match='category audit failure'):
            if operation=='create':create(client,'Another','category-other-001')
            elif operation=='edit':client.put(BASE+'/'+category['id'],json={'name':'Changed','expected_revision':1})
            elif operation=='archive':client.post(BASE+'/'+category['id']+'/archive',json={'expected_revision':1,'archived':True})
            else:client.post(ASSIGN,json=request(category,tasks))
    assert {kind:store.all(kind) for kind in kinds}==before and store.audit_integrity()==audit and not lab[1].requests


def test_viewer_read_and_operator_assignment_do_not_grant_approval(client,lab):
    asset=register(client,lab[0]);planned=task(client,asset,['security_headers']);category=create(client)
    viewer=add(client,'viewer');operator=add(client,'operator')
    with login(client.app,viewer['username']) as read:
        assert read.get(BASE).status_code==200 and read.get(BASE+'/'+category['id']+'/history').status_code==200
        assert read.post(ASSIGN,json=request(category,[planned])).status_code==403
        assert read.put(BASE+'/'+category['id'],json={'name':'Changed','expected_revision':1}).status_code==403
    with login(client.app,operator['username']) as other:
        assert other.post(ASSIGN,json=request(category,[planned])).status_code==200
        assert other.post('/api/tasks/'+planned['id']+'/approve').status_code==403
    assert not lab[1].requests


def test_worker_completion_keeps_classification_and_history(client,lab):
    asset=register(client,lab[0]);planned=task(client,asset,['security_headers']);category=create(client)
    assert client.post(ASSIGN,json=request(category,[planned])).status_code==200
    assert client.post('/api/tasks/'+planned['id']+'/approve').status_code==200
    result=finish(client,planned['id'])['task']
    assert result['status']=='completed' and result['category_ref']['id']==category['id'] and result['category_revision']==1
    assert client.get('/api/tasks/'+planned['id']+'/category-history').json()['total']==1


def test_replan_inherits_classification_without_inheriting_assignment_version(client,lab):
    asset=register(client,lab[0]);planned=task(client,asset,['security_headers']);category=create(client)
    assert client.post(ASSIGN,json=request(category,[planned])).status_code==200
    response=client.post('/api/tasks/'+planned['id']+'/replan');assert response.status_code==200,response.text
    newer=response.json();assert newer['category_ref']['id']==category['id']
    assert newer['category_revision']==0 and newer['category_origin_task_id']==planned['id']
    assert newer['status']=='pending' and newer['approved_at'] is None and not lab[1].requests


def test_classification_during_inflight_request_survives_worker_completion(client,lab,monkeypatch):
    import threading
    entered=threading.Event();release=threading.Event();original=lab[1].do_GET
    def paused(self):
        entered.set();assert release.wait(4),'Owned response gate was not released'
        return original(self)
    monkeypatch.setattr(lab[1],'do_GET',paused)
    asset=register(client,lab[0]);planned=task(client,asset,['security_headers']);category=create(client)
    try:
        assert client.post('/api/tasks/'+planned['id']+'/approve').status_code==200
        assert entered.wait(3),'Owned GET did not start'
        before=client.get('/api/tasks/'+planned['id']).json()['task']
        response=client.post(ASSIGN,json=request(category,[before]));assert response.status_code==200,response.text
        during=client.get('/api/tasks/'+planned['id']).json()['task']
        assert during['status']=='running' and during['approved_at']==before['approved_at']
        assert during['scope_snapshot']==before['scope_snapshot'] and during['checks']==before['checks']
    finally:release.set()
    result=finish(client,planned['id'])['task']
    assert result['status']=='completed' and result['category_ref']['id']==category['id'] and result['category_revision']==1
    assert len(lab[1].requests)==1


def test_category_sql_search_paging_and_versions_are_bounded_without_full_scan(client,monkeypatch):
    for index in range(28):create(client,name=f'Filter class {index}',request_id=f'category-create-{index:04}')
    def forbidden(*args,**kwargs):raise AssertionError('Category reads must use bounded SQL')
    monkeypatch.setattr(client.app.state.store,'all',forbidden)
    first=client.get(BASE,params={'limit':25,'search':'Filter class'}).json()
    assert len(first['items'])==25 and first['total']==28
    second=client.get(BASE,params={'limit':25,'offset':25,'snapshot':first['snapshot'],'search':'Filter class'}).json()
    assert len(second['items'])==3
    assert not ({r['id'] for r in first['items']} & {r['id'] for r in second['items']})
    assert client.get(BASE,params={'limit':26}).status_code==422


@pytest.mark.parametrize('malformed',[{'task_ids':['one','one'],'expected_revisions':{'one':0}},
 {'task_ids':['one'],'expected_revisions':{'one':True}}, {'task_ids':['one'],'expected_revisions':{}},
 {'task_ids':['one'],'expected_revisions':{'one':0,'unselected':0}}, {'category_id':'../escape'}, {'status':'completed'}])
def test_invalid_selection_revisions_and_authority_fields_refused(client,malformed):
    response=client.post(ASSIGN,json={'task_ids':['one'],'expected_revisions':{'one':0},'category_id':None,
        'request_id':'invalid-category-001',**malformed})
    assert response.status_code==422 and client.app.state.store.count('task_category_operations')==0


def test_reclassification_of_inherited_task_sets_its_own_origin_for_next_replan(client,lab):
    asset=register(client,lab[0]);original=task(client,asset,['security_headers']);category=create(client)
    assert client.post(ASSIGN,json=request(category,[original])).status_code==200
    child=client.post('/api/tasks/'+original['id']+'/replan').json()
    assert child['category_origin_task_id']==original['id']
    other=create(client,'Another folder','category-other-001')
    assert client.post(ASSIGN,json=request(other,[child],request_id='child-reclassify-001')).status_code==200
    fresh=client.get('/api/tasks/'+child['id']).json()['task']
    assert 'category_origin_task_id' not in fresh
    history=client.get('/api/tasks/'+child['id']+'/category-history').json()['items']
    assert history[0]['before_origin_task_id']==original['id']
    next_task=client.post('/api/tasks/'+child['id']+'/replan').json()
    assert next_task['category_ref']['id']==other['id'] and next_task['category_origin_task_id']==child['id']


@pytest.mark.parametrize('change',['role','disabled'])
def test_authorization_changed_after_request_dependency_refuses_category_write(client,monkeypatch,change):
    from aegis.task_categories import Categories
    original=Categories.create;store=client.app.state.store
    def revoked(self,data,actor):
        marker='%s' if getattr(store,'backend',None)=='postgres' else '?'
        with store.write_transaction() as db:
            if change=='role':db.execute(f'UPDATE users SET role={marker} WHERE id={marker}',('viewer',actor['id']))
            else:db.execute(f'UPDATE users SET disabled={marker} WHERE id={marker}',(1,actor['id']))
        return original(self,data,actor)
    monkeypatch.setattr(Categories,'create',revoked)
    response=client.post(BASE,json={'name':'Refused','request_id':'revoked-category-001'})
    assert response.status_code==403 and store.count('task_categories')==store.count('task_category_versions')==0


def test_sql_category_filter_counts_pagination_and_archived_membership(client,lab,monkeypatch):
    asset=register(client,lab[0]);tasks=[task(client,asset,['security_headers']) for _ in range(3)]
    category=create(client)
    assert client.post(ASSIGN,json=request(category,tasks[:2])).status_code==200
    store=client.app.state.store
    monkeypatch.setattr(store,'all',lambda *a,**k:pytest.fail('category filters must stay in SQL'))
    selected=client.get('/api/records/tasks',params={'category_id':category['id'],'limit':1}).json()
    assert selected['total']==2 and len(selected['items'])==1 and selected['has_more']
    next_page=client.get('/api/records/tasks',params={'category_id':category['id'],'limit':1,'offset':1,'snapshot':selected['snapshot']}).json()
    assert next_page['total']==2 and next_page['items'][0]['id']!=selected['items'][0]['id']
    unclassified=client.get('/api/records/tasks',params={'category_id':'unclassified'}).json()
    assert unclassified['total']==1 and unclassified['items'][0]['id']==tasks[2]['id']
    assert client.post(BASE+'/'+category['id']+'/archive',json={'expected_revision':1,'archived':True}).status_code==200
    assert client.get('/api/records/tasks',params={'category_id':category['id']}).json()['total']==2
    assert client.get('/api/records/findings',params={'category_id':category['id']}).status_code==422
    assert client.get('/api/records/tasks',params={'category_id':"' OR 1=1"}).status_code==422
