import json
import uuid
import pytest
from tests.test_validation import client
from aegis import todos

ACTOR={'id':'owned-user','username':'owned','name':'Owned operator','role':'operator'}

def seed(store):
    asset={'id':'todo-asset','name':'Owned synthetic','url':'https://todo-fixture.invalid/',
           'revision':1,'authorized':True,'archived_at':None}
    root={'id':'todo-root','name':'Root','status':'completed','approved_at':1.,'created_at':1.,
          'asset_ids':[asset['id']],'scope_snapshot':[asset],'checks':['security_headers'],
          'worker_dependencies':{},'workers':1,'planner':'rules','goal':'Owned synthetic',
          'next_plan_id':'todo-child','next_plan_fingerprint':'a'*64}
    child={**root,'id':'todo-child','name':'Round one','status':'failed','planning_round':1,
           'followup_of':root['id'],'followup_fingerprint':'a'*64}
    child.pop('next_plan_id');child.pop('next_plan_fingerprint')
    store.put_many([('assets',asset),('tasks',root),('tasks',child)])
    return root,child

def payload(**changes):return {'request_id':uuid.uuid4().hex,'title':'Review failed response','description':'Owned decision',**changes}


def test_shared_http_todos_survive_real_retry_replan_and_duplicate_creation(client):
    store=client.app.state.store;root,child=seed(store)
    path='/api/tasks/'+child['id']+'/todos';data=payload()
    first=client.post(path,json=data);assert first.status_code==200,first.text
    row=first.json()
    assert client.post(path,json=data).json()==row and store.count('todo_history')==1
    retry=client.post('/api/tasks/'+child['id']+'/retry').json()
    replacement=client.post('/api/tasks/'+retry['id']+'/replan').json()
    for task in (root,child,retry,replacement):
        result=client.get('/api/tasks/'+task['id']+'/todos').json()
        assert result['root_task_id']==root['id'] and result['items'][0]['id']==row['id']
        assert not result['execution_authorized']
        assert client.get('/api/tasks/'+task['id']+'/todos/'+row['id']).json()==row
    updated=client.patch('/api/tasks/'+replacement['id']+'/todos/'+row['id'],json={
        'expected_revision':1,'status':'done','resolution_note':'Reviewed manually'}).json()
    assert updated['revision']==2 and updated['status']=='done'
    assert client.post(path,json=data).json()==updated
    assert client.get(path+'/'+row['id']).json()==updated
    assert store.get('tasks',replacement['id'])['status']=='pending'
    assert store.get('tasks',replacement['id'])['approved_at'] is None and store.count('traffic')==0
    assert client.patch(path+'/'+row['id'],json={'expected_revision':1,'title':'Overwrite'}).status_code==409
    assert client.post(path,json={**data,'title':'Other request'}).status_code==409
    history=client.get(path+'/'+row['id']+'/history').json()
    assert history['total']==2 and history['items'][0]['revision']==2
    assert store.audit_integrity()['valid']


def test_todo_http_validation_roles_foreign_families_and_no_execution(client):
    from tests.test_identity import add,login
    store=client.app.state.store;root,child=seed(store)
    path='/api/tasks/'+root['id']+'/todos'
    for bad in (payload(title='   '),payload(title='x'*201),payload(command='run'),payload(request_id='bad')):
        assert client.post(path,json=bad).status_code==422
    row=client.post(path,json=payload()).json()
    for data in ({'expected_revision':True,'status':'done'}, {'expected_revision':1},
                 {'expected_revision':1,'status':None}, {'expected_revision':1,'status':'done'},
                 {'expected_revision':1,'assignee_id':'missing'}):
        assert client.patch(path+'/'+row['id'],json=data).status_code==422
    foreign={**root,'id':'foreign-root'};foreign.pop('next_plan_id');foreign.pop('next_plan_fingerprint');store.put('tasks',foreign)
    assert client.patch('/api/tasks/foreign-root/todos/'+row['id'],json={'expected_revision':1,'title':'Foreign'}).status_code==404
    assert client.get('/api/tasks/foreign-root/todos/'+row['id']).status_code==404
    assert client.get(path+'/missing').status_code==404
    viewer=add(client,'viewer')
    with login(client.app,viewer['username']) as read:
        assert read.get(path).status_code==200
        assert read.get(path+'/'+row['id']).json()==row
        assert read.post(path,json=payload()).status_code==403
        assert read.patch(path+'/'+row['id'],json={'expected_revision':1,'title':'Denied'}).status_code==403
        assert read.get(path+'/'+row['id']+'/history').status_code==200
    client.post('/api/auth/logout');assert client.get(path).status_code==401
    assert client.get(path+'/'+row['id']).status_code==401


def test_todo_change_and_audit_rollback_together_on_event_failure(client,monkeypatch):
    store=client.app.state.store;root,_=seed(store);before=store.audit_integrity()
    def failure(*args,**kwargs):raise RuntimeError('Owned injected audit failure')
    monkeypatch.setattr(store,'event',failure)
    with pytest.raises(RuntimeError):todos.create(store,root['id'],payload(),ACTOR)
    assert store.count('todos')==store.count('todo_history')==0 and store.audit_integrity()==before
