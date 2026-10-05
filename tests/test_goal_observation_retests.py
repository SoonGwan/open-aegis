"""Owned observed finding retests retain verified objective origin and URL."""
import copy
import pytest
from aegis import goal_planner,goal_observations
from tests.test_goal_observations import goal_source
from tests.test_validation import client,lab,finish
from aegis.worker_observations import record_link


def observed_finding(client,lab,monkeypatch):
    goal,assets,path,preview,body=goal_source(client,lab,monkeypatch)
    store=client.app.state.store
    record_link(store,store.get('tasks',goal['id']),assets[0],'endpoint_inventory',lab[0]+'login')
    preview=client.get(path).json()
    body.update(fingerprint=preview['fingerprint'],observation_ids=[row['id'] for row in preview['context']['items'] if row['url']==lab[0]+'login'])
    plan=client.post(path,json=body).json()
    assert client.post('/api/tasks/'+plan['id']+'/approve').status_code==200
    result=finish(client,plan['id'])
    finding=next(row for row in result['findings'] if row['check']=='security_headers')
    return goal,plan,store.get('findings',finding['id'])


def test_observed_retest_inherits_objective_executes_same_url_and_keeps_original_evidence(client,lab,monkeypatch):
    goal,plan,finding=observed_finding(client,lab,monkeypatch)
    path='/api/findings/'+finding['id']+'/retest'
    evidence=client.get('/api/findings/'+finding['id']).json()['evidence']
    progress=client.get('/api/tasks/'+goal['id']+'/goal-progress').json()
    before=list(lab[1].requests)
    result=client.post(path);assert result.status_code==200,result.text
    pending=result.json()
    assert pending['approved_at'] is None and pending['status']=='pending'
    assert isinstance(pending.get('goal_observation'),dict)
    assert all(pending['goal_observation'][key]==plan['goal_observation'][key] for key in goal_observations.ORIGIN)
    assert pending['observation_execution']['observation_ids']==[finding['observation_id']]
    assert client.post(path).json()['id']==pending['id'] and lab[1].requests==before
    # Replacement and recovery must keep the objective even for a finding retest.
    replacement=client.post('/api/tasks/'+pending['id']+'/replan')
    assert replacement.status_code==200,replacement.text
    replacement=replacement.json()
    assert replacement['goal_observation']==pending['goal_observation']
    assert client.post(path).json()['id']==replacement['id']
    lab[1].hardened=True
    assert client.post('/api/tasks/'+replacement['id']+'/approve').status_code==200
    finish(client,replacement['id'])
    assert lab[1].requests[len(before):]==['/login']
    detail=client.get('/api/findings/'+finding['id']).json()
    assert detail['finding']['status']=='resolved' and detail['evidence']==evidence
    assert detail['retests'][0]['goal_observation']==replacement['goal_observation']
    assert client.get('/api/tasks/'+goal['id']+'/goal-progress').json()==progress


@pytest.mark.parametrize('damage',['objective','proof_url','proof_task','source_approval','source_origin','active_origin'])
def test_changed_or_damaged_observed_retest_origin_cannot_create_or_request(client,lab,monkeypatch,damage):
    goal,plan,finding=observed_finding(client,lab,monkeypatch);store=client.app.state.store
    path='/api/findings/'+finding['id']+'/retest'
    if damage=='objective':
        changed=copy.deepcopy(goal['goal_plan']);changed['decomposition']['objectives'][0]['title']='Changed objective'
        changed['fingerprint']=goal_planner.fingerprint(changed);store.patch('tasks',goal['id'],goal_plan=changed)
    elif damage.startswith('proof_'):
        proof=store.get('evidence',finding['evidence_ids'][-1])
        if damage=='proof_url':proof['observation']['requested_url']=lab[0]+'other/'
        else:proof['task_id']=goal['id']
        store.put('evidence',proof)
    elif damage=='source_approval':store.patch('tasks',plan['id'],approved_at=True)
    elif damage=='source_origin':store.patch('tasks',plan['id'],goal_observation=None)
    else:
        active=client.post(path).json();store.patch('tasks',active['id'],goal_observation=None)
    before=list(lab[1].requests);count=store.count('tasks')
    assert client.post(path).status_code==409
    assert store.count('tasks')==count and lab[1].requests==before


def test_observed_retest_final_write_rechecks_proof_and_rolls_back(client,lab,monkeypatch):
    goal,plan,finding=observed_finding(client,lab,monkeypatch);store=client.app.state.store
    proof=store.get('evidence',finding['evidence_ids'][-1]);before=list(lab[1].requests)
    count=store.count('tasks');cells=store.count('coverage')
    original=goal_observations.prepare
    def race(*args,**kwargs):
        db=kwargs.get('connection')
        if db is not None:
            changed=copy.deepcopy(proof);changed['observation']['requested_url']=lab[0]+'other/'
            store.put_many([('evidence',changed)],connection=db)
        return original(*args,**kwargs)
    monkeypatch.setattr(goal_observations,'prepare',race)
    assert client.post('/api/findings/'+finding['id']+'/retest').status_code==409
    assert store.count('tasks')==count and store.count('coverage')==cells
    assert store.get('evidence',proof['id'])==proof and lab[1].requests==before


def test_latest_general_observed_proof_does_not_invent_old_goal_origin(client,lab,monkeypatch):
    goal,plan,finding=observed_finding(client,lab,monkeypatch)
    path='/api/tasks/'+goal['id']+'/observation-plan'
    preview=client.get(path).json()
    ordinary=client.post(path,json={'fingerprint':preview['context']['fingerprint'],
        'observation_ids':[finding['observation_id']], 'checks':['security_headers'],'request_id':'b'*32}).json()
    assert not ordinary.get('goal_observation')
    assert client.post('/api/tasks/'+ordinary['id']+'/approve').status_code==200
    finish(client,ordinary['id']);before=list(lab[1].requests)
    retest=client.post('/api/findings/'+finding['id']+'/retest')
    assert retest.status_code==200,retest.text
    assert not retest.json().get('goal_observation') and lab[1].requests==before
