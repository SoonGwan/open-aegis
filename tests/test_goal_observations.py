"""Owned objective-linked observed URLs require separate approval and proof."""
import copy
import pytest
from aegis import goal_planner, goal_observations, observation_execution
from aegis.worker_observations import record_link
from tests.test_validation import client,lab,register,finish
from tests.test_goal_planner import provider,draft
from tests.test_identity import add,login


def goal_source(client,lab,monkeypatch):
    assets=[register(client,lab[0]),register(client,lab[0]+'other/')]
    original=client.post('/api/tasks',json={'name':'Owned goal observations','asset_ids':[a['id'] for a in assets],
        'checks':['endpoint_inventory'],'workers':2}).json()
    def goals(plan,prompt):
        for objective,asset in zip(plan['objectives'],assets):
            objective['asset_ids']=[asset['id']]
            objective['checks']=['security_headers','endpoint_inventory']
        return plan
    provider(monkeypatch,goals);path,_,reviewed=draft(client,original)
    goal=client.post(path+'/'+reviewed['id']+'/accept',json={'fingerprint':reviewed['fingerprint']}).json()
    assert client.post('/api/tasks/'+goal['id']+'/approve').status_code==200
    finish(client,goal['id'])
    store=client.app.state.store
    record_link(store,store.get('tasks',goal['id']),assets[1],'endpoint_inventory',lab[0]+'other/private')
    path='/api/tasks/'+goal['id']+'/goal-objectives/g1/observation-plan'
    preview=client.get(path);assert preview.status_code==200,preview.text
    preview=preview.json();assert preview['context']['items']
    selected={'fingerprint':preview['fingerprint'],'observation_ids':[row['id'] for row in preview['context']['items']],
              'checks':['security_headers'],'request_id':'a'*32}
    return goal,assets,path,preview,selected


def test_goal_observation_filters_asset_and_declared_checks_then_executes_only_selected_url(client,lab,monkeypatch):
    goal,assets,path,preview,body=goal_source(client,lab,monkeypatch)
    assert preview['checks']==['security_headers'] and preview['goal_verified'] is False
    assert {row['asset_id'] for row in preview['context']['items']}=={assets[0]['id']}
    assert preview['context']['counts']['excluded']>=1
    before=list(lab[1].requests);before_progress=client.get('/api/tasks/'+goal['id']+'/goal-progress').json()
    before_coverage=client.get('/api/overview').json()['coverage_summary']
    result=client.post(path,json=body);assert result.status_code==200,result.text
    pending=result.json();assert pending['status']=='pending' and pending['approved_at'] is None
    assert pending['goal_observation']['objective_id']=='g1' and pending['goal_observation']['source_task_id']==goal['id']
    assert pending['goal_observation']['source_plan_fingerprint']==goal['goal_plan']['fingerprint']
    assert pending['asset_ids']==[assets[0]['id']] and not pending.get('goal_plan')
    assert lab[1].requests==before
    assert client.post(path,json=body).json()['id']==pending['id']
    assert client.post(path,json={**body,'checks':['cookie_policy']}).status_code==409
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==200
    execution=finish(client,pending['id'])
    assert lab[1].requests[len(before):]==['/api/account']
    assert execution['coverage'][0]['targets'][0]['status']=='completed'
    assert client.get('/api/tasks/'+goal['id']+'/goal-progress').json()==before_progress
    assert client.get('/api/overview').json()['coverage_summary']==before_coverage
    assert client.get('/api/tasks/'+pending['id']+'/next-plan').json()['reason']=='no_remaining_observation_checks'


@pytest.mark.parametrize('damage',['other_asset','undeclared_check','source_approval','goal_title','scope','missing_objective'])
def test_goal_observation_rejects_outside_or_changed_objective_without_requests(client,lab,monkeypatch,damage):
    goal,assets,path,preview,body=goal_source(client,lab,monkeypatch);store=client.app.state.store
    if damage=='other_asset':
        other=client.get('/api/tasks/'+goal['id']+'/goal-objectives/g2/observation-plan').json()
        body['observation_ids']=[row['id'] for row in other['context']['items']]
    elif damage=='undeclared_check':body['checks']=['cookie_policy']
    elif damage=='source_approval':store.patch('tasks',goal['id'],approved_at=True)
    elif damage=='goal_title':
        plan=copy.deepcopy(goal['goal_plan']);plan['decomposition']['objectives'][0]['title']='Changed reviewed objective'
        plan['fingerprint']=goal_planner.fingerprint(plan);store.patch('tasks',goal['id'],goal_plan=plan)
    elif damage=='scope':store.patch('assets',assets[0]['id'],revision=2)
    else:path=path.replace('/g1/','/g12/')
    before=list(lab[1].requests);count=store.count('tasks')
    assert client.post(path,json=body).status_code==(404 if damage=='missing_objective' else 409)
    assert store.count('tasks')==count and lab[1].requests==before


def test_goal_observation_replan_retry_preserve_objective_and_require_fresh_approval(client,lab,monkeypatch):
    goal,assets,path,preview,body=goal_source(client,lab,monkeypatch)
    pending=client.post(path,json=body).json();before=list(lab[1].requests)
    replacement=client.post('/api/tasks/'+pending['id']+'/replan');assert replacement.status_code==200,replacement.text
    replacement=replacement.json()
    assert replacement['goal_observation']==pending['goal_observation']
    client.app.state.store.patch('tasks',replacement['id'],status='interrupted')
    retry=client.post('/api/tasks/'+replacement['id']+'/retry');assert retry.status_code==200,retry.text
    retry=retry.json();assert retry['goal_observation']==pending['goal_observation']
    assert lab[1].requests==before and retry['approved_at'] is None
    assert client.post('/api/tasks/'+retry['id']+'/approve').status_code==200
    finish(client,retry['id']);assert lab[1].requests[len(before):]==['/api/account']


def test_goal_observation_metadata_tampering_blocks_approval_and_request_replay(client,lab,monkeypatch):
    goal,assets,path,preview,body=goal_source(client,lab,monkeypatch)
    pending=client.post(path,json=body).json();store=client.app.state.store
    changed=copy.deepcopy(pending['goal_observation']);changed['objective_asset_ids']=[assets[1]['id']]
    changed['fingerprint']=goal_planner.digest({key:value for key,value in changed.items() if key!='fingerprint'})
    store.patch('tasks',pending['id'],goal_observation=changed)
    before=list(lab[1].requests)
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==409
    assert client.post(path,json=body).status_code==409 and lab[1].requests==before


def test_goal_observation_final_write_rechecks_goal_and_rolls_back_records(client,lab,monkeypatch):
    goal,assets,path,preview,body=goal_source(client,lab,monkeypatch);store=client.app.state.store
    before_count=store.count('tasks');before_cells=store.count('coverage');before_audit=store.audit_integrity()
    original=goal_observations.prepare
    def race(*args,**kwargs):
        db=kwargs.get('connection')
        if db is not None:
            source=store.get('tasks',goal['id'],connection=db);plan=copy.deepcopy(source['goal_plan'])
            plan['decomposition']['objectives'][0]['title']='Owned transaction race'
            plan['fingerprint']=goal_planner.fingerprint(plan)
            store.put_many([('tasks',{**source,'goal_plan':plan})],connection=db)
        return original(*args,**kwargs)
    monkeypatch.setattr(goal_observations,'prepare',race)
    assert client.post(path,json=body).status_code==409
    assert store.count('tasks')==before_count and store.count('coverage')==before_cells
    after_audit=store.audit_integrity()
    assert after_audit['valid'] and after_audit['events']==before_audit['events']+1
    event=store.events(after=before_audit['checkpoint']['seq'])[-1]
    assert event['detail']['status']==409 and event['detail']['path']==path
    assert store.get('tasks',goal['id'])['goal_plan']==goal['goal_plan']


def test_goal_observation_viewer_can_review_but_cannot_create(client,lab,monkeypatch):
    goal,assets,path,preview,body=goal_source(client,lab,monkeypatch)
    add(client,'viewer','reader');before=list(lab[1].requests)
    with login(client.app,'reader') as viewer:
        assert viewer.get(path).status_code==200 and viewer.post(path,json=body).status_code==403
    assert lab[1].requests==before


@pytest.mark.parametrize('removed',[None,{}])
def test_goal_observation_removed_reference_blocks_replay_and_approval(client,lab,monkeypatch,removed):
    goal,assets,path,preview,body=goal_source(client,lab,monkeypatch)
    pending=client.post(path,json=body).json()
    client.app.state.store.patch('tasks',pending['id'],goal_observation=removed)
    before=list(lab[1].requests)
    assert client.post(path,json=body).status_code==409
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==409
    assert lab[1].requests==before
