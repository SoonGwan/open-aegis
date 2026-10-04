import copy
import pytest
from tests.test_validation import client,lab,finish
from tests.test_goal_evidence import executed_goal
from tests.test_identity import add,login


def test_goal_retest_origin_is_pending_idempotent_replanned_and_persisted_with_result(client,lab,monkeypatch):
    goal,execution,_=executed_goal(client,lab,monkeypatch)
    finding=next(f for f in execution['findings'] if f['code']=='missing-nosniff')
    path='/api/tasks/'+goal['id']+'/goal-objectives/g1/findings/'+finding['id']+'/retest'
    before=list(lab[1].requests);body={'request_id':'f'*32}
    response=client.post(path,json=body);assert response.status_code==200,response.text
    pending=response.json();ref=pending['goal_retest']
    assert pending['status']=='pending' and pending['approved_at'] is None and lab[1].requests==before
    assert ref['source_task_id']==goal['id'] and ref['objective_id']=='g1' and ref['finding_id']==finding['id']
    assert client.post(path,json=body).json()['id']==pending['id']
    assert client.post(path,json={'request_id':'e'*32}).status_code==409
    replacement=client.post('/api/tasks/'+pending['id']+'/replan')
    assert replacement.status_code==200,replacement.text
    assert replacement.json()['goal_retest']==ref
    lab[1].hardened=True;active=replacement.json()
    assert client.post('/api/tasks/'+active['id']+'/approve').status_code==200
    finish(client,active['id'])
    result=client.get('/api/findings/'+finding['id']).json()['retests'][0]
    assert result['conclusion']=='resolved' and result['goal_retest']==ref
    # The original nonce returns its durable original task, even after replacement.
    assert client.post(path,json=body).json()['id']==pending['id']


def test_goal_retest_requires_matching_source_proof_and_operator(client,lab,monkeypatch):
    goal,execution,_=executed_goal(client,lab,monkeypatch);finding=execution['findings'][0]
    path='/api/tasks/'+goal['id']+'/goal-objectives/g1/findings/'+finding['id']+'/retest'
    add(client,'viewer')
    before=list(lab[1].requests)
    with login(client.app,'viewer') as read:
        assert read.post(path,json={'request_id':'e'*32}).status_code==403
    store=client.app.state.store;store.patch('findings',finding['id'],evidence_ids=[])
    assert client.post(path,json={'request_id':'e'*32}).status_code==409
    assert lab[1].requests==before


def test_goal_retest_final_write_checks_origin_and_rolls_back(client,lab,monkeypatch):
    from aegis import goal_retests
    goal,execution,_=executed_goal(client,lab,monkeypatch);finding=execution['findings'][0]
    path='/api/tasks/'+goal['id']+'/goal-objectives/g1/findings/'+finding['id']+'/retest'
    prepare=goal_retests.prepare;store=client.app.state.store;count=store.count('tasks')
    def changed(*args,**kwargs):
        value=prepare(*args,**kwargs)
        if kwargs.get('connection') is not None:value['source_plan_fingerprint']='owned-changed-origin'
        return value
    monkeypatch.setattr(goal_retests,'prepare',changed)
    assert client.post(path,json={'request_id':'e'*32}).status_code==409
    assert store.count('tasks')==count


def test_goal_retest_origin_tampering_refuses_approval(client,lab,monkeypatch):
    goal,execution,_=executed_goal(client,lab,monkeypatch);finding=execution['findings'][0]
    path='/api/tasks/'+goal['id']+'/goal-objectives/g1/findings/'+finding['id']+'/retest'
    pending=client.post(path,json={'request_id':'e'*32}).json();ref=copy.deepcopy(pending['goal_retest'])
    ref['objective_id']='g12';client.app.state.store.patch('tasks',pending['id'],goal_retest=ref)
    before=list(lab[1].requests)
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==409
    assert lab[1].requests==before


def restart_goal_retest(folder,lab,monkeypatch):
    from fastapi.testclient import TestClient
    from aegis.app import create_app
    with TestClient(create_app(folder,allow_private=True)) as first:
        assert first.post('/api/auth/setup',json={'password':'aegis-test-password-only'}).status_code==200
        goal,execution,_=executed_goal(first,lab,monkeypatch)
        finding=execution['findings'][0]
        path='/api/tasks/'+goal['id']+'/goal-objectives/g1/findings/'+finding['id']+'/retest'
        pending=first.post(path,json={'request_id':'b'*32}).json()
        assert pending['status']=='pending'
    before=list(lab[1].requests)
    with TestClient(create_app(folder,allow_private=True)) as second:
        assert second.post('/api/auth/login',json={'username':'admin','password':'aegis-test-password-only'}).status_code==200
        stored=second.get('/api/tasks/'+pending['id']).json()['task']
        assert stored['goal_retest']==pending['goal_retest'] and stored['status']=='pending'
        assert second.post(path,json={'request_id':'b'*32}).json()['id']==pending['id']
        assert lab[1].requests==before
        assert second.post('/api/tasks/'+pending['id']+'/approve').status_code==200
        finish(second,pending['id'])
        result=second.get('/api/findings/'+finding['id']).json()['retests'][0]
        assert result['goal_retest']==pending['goal_retest']


def test_goal_retest_origin_survives_application_restart(tmp_path,lab,monkeypatch):
    restart_goal_retest(tmp_path/'restart',lab,monkeypatch)
