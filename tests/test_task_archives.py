"""Terminal-task archiving preserves evidence; failed batches and retries are atomic."""
import copy
import pytest
from tests.test_mcp_registry import client
from tests.test_postgres_transfer import postgres
from tests.test_validation import lab,register,task,finish
from tests.test_identity import add,login

BASE='/api/tasks/archive-assignment'
def request(tasks,**changes):
    return {'task_ids':[t['id'] for t in tasks],'expected_revisions':{t['id']:t.get('archive_revision',0) for t in tasks},'archived':True,'request_id':'owned-task-archive-001',**changes}

def rejected(client,lab,asset=None):
    planned=task(client,asset or register(client,lab[0]),['security_headers'])
    response=client.post('/api/tasks/'+planned['id']+'/stop');assert response.status_code==200
    return response.json()

def test_actual_completed_task_archive_restore_preserves_all_execution_evidence(client,lab):
    planned=task(client,register(client,lab[0]),['security_headers'])
    assert client.post('/api/tasks/'+planned['id']+'/approve').status_code==200
    original=copy.deepcopy(finish(client,planned['id'])['task']);store=client.app.state.store
    client.app.state.event_planner.close()
    kinds=('findings','evidence','traffic','coverage','observations','plan_reviews')
    evidence={kind:store.all(kind) for kind in kinds};hits=len(lab[1].requests)
    response=client.post(BASE,json=request([original]));assert response.status_code==200,response.text
    assert not response.json()['execution_authorized']
    archived=client.get('/api/tasks/'+planned['id']).json()['task']
    assert archived['archived_at'] and archived['archive_revision']==1
    assert {k:v for k,v in archived.items() if k not in ('archive_revision','archived_at')}==original
    assert client.get('/api/records/tasks',params={'archived':True,'search':original['name']}).json()['total']==1
    assert client.get('/api/records/tasks',params={'archived':False}).json()['total']==0
    assert client.post(BASE,json=request([archived],archived=False,request_id='owned-task-restore-001')).status_code==200
    restored=client.get('/api/tasks/'+planned['id']).json()['task'];assert restored['archived_at'] is None and restored['archive_revision']==2
    assert {kind:store.all(kind) for kind in kinds}==evidence and len(lab[1].requests)==hits
    assert client.get('/api/tasks/'+planned['id']+'/archive-history').json()['total']==2 and store.audit_integrity()['valid']

def test_lost_archive_response_replay_never_rearchives_after_restore(client,lab):
    original=rejected(client,lab);payload=request([original])
    first=client.post(BASE,json=payload).json();archived=client.get('/api/tasks/'+original['id']).json()['task']
    assert client.post(BASE,json=request([archived],archived=False,request_id='owned-task-restore-001')).status_code==200
    replay=client.post(BASE,json=payload);assert replay.status_code==200 and replay.json()=={**first,'replayed':True}
    assert not client.get('/api/tasks/'+original['id']).json()['task']['archived_at']
    assert client.post(BASE,json={**payload,'archived':False}).status_code==409
    assert not lab[1].requests and client.app.state.store.count('task_archive_history')==2

@pytest.mark.parametrize('invalid',['pending','stale','missing'])
def test_one_invalid_task_rolls_back_entire_batch(client,lab,invalid):
    asset=register(client,lab[0]);first=rejected(client,lab,asset);other=task(client,asset,['security_headers'])
    if invalid!='pending':other=client.post('/api/tasks/'+other['id']+'/stop').json()
    before=[first,other];payload=request(before)
    if invalid=='stale':payload['expected_revisions'][other['id']]=1
    if invalid=='missing':payload['task_ids'][1]='missing';payload['expected_revisions']={first['id']:0,'missing':0}
    response=client.post(BASE,json=payload);assert response.status_code==(404 if invalid=='missing' else 409)
    store=client.app.state.store
    assert [store.get('tasks',t['id']) for t in before]==before
    assert store.count('task_archive_history')==store.count('task_archive_operations')==0 and not lab[1].requests

def test_audit_failure_rolls_back_all_tasks_history_and_operation(client,lab,monkeypatch):
    asset=register(client,lab[0]);tasks=[rejected(client,lab,asset),rejected(client,lab,asset)];store=client.app.state.store
    client.app.state.event_planner.close();audit=store.audit_integrity();original=store.event
    def failed(id,message,*args,**kwargs):
        if message=='작업 보관 변경':raise RuntimeError('owned archive audit failure')
        return original(id,message,*args,**kwargs)
    monkeypatch.setattr(store,'event',failed)
    with pytest.raises(RuntimeError,match='owned archive audit failure'):client.post(BASE,json=request(tasks))
    assert [store.get('tasks',t['id']) for t in tasks]==tasks
    assert store.count('task_archive_history')==store.count('task_archive_operations')==0 and store.audit_integrity()==audit

def test_viewer_cannot_archive_operator_can_and_stale_role_is_rechecked(client,lab):
    planned=rejected(client,lab);viewer=add(client,'viewer');operator=add(client,'operator')
    with login(client.app,viewer['username']) as other:
        assert other.post(BASE,json=request([planned])).status_code==403
        assert other.get('/api/tasks/'+planned['id']+'/archive-history').status_code==200
    with login(client.app,operator['username']) as other:
        assert other.post(BASE,json=request([planned])).status_code==200
    from aegis.task_archives import Archives,ArchiveInput
    client.app.state.store.update_user(operator['id'],role='viewer')
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as caught:Archives(client.app.state.store).change(ArchiveInput(**request([planned])),operator)
    assert caught.value.status_code==403 and not lab[1].requests

@pytest.mark.parametrize('change',[{'task_ids':[]},{'task_ids':['a','a'],'expected_revisions':{'a':0}},{'expected_revisions':{}},{'expected_revisions':{'a':True}},{'archived':'true'},{'request_id':'short'}])
def test_invalid_batch_contract_creates_no_receipt(client,change):
    payload={'task_ids':['a'],'expected_revisions':{'a':0},'archived':True,'request_id':'owned-task-archive-001',**change}
    assert client.post(BASE,json=payload).status_code==422
    assert client.app.state.store.count('task_archive_operations')==0
