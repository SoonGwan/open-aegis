"""Actual sparse goal rounds retain untouched evidence and skip unrelated requests."""
import copy
import pytest
from aegis import engine, goal_planner
from tests.test_validation import client, lab, register, finish
from tests.test_goal_planner import provider, draft


def failed_goal(client, lab, monkeypatch):
    assets = [register(client,lab[0]),register(client,lab[0]+'other/')]
    original = client.post('/api/tasks',json={'name':'Owned selective goal','asset_ids':[a['id'] for a in assets],
        'checks':['security_headers'],'workers':2}).json()
    provider(monkeypatch)
    path,_,planned = draft(client,original)
    goal = client.post(path+'/'+planned['id']+'/accept',json={'fingerprint':planned['fingerprint']}).json()
    original_check = engine.run_check
    def check(kind,asset,*args):
        if kind == 'cors_policy' and asset['id'] == assets[1]['id']:
            raise ValueError('Owned one-cell failure')
        return original_check(kind,asset,*args)
    monkeypatch.setattr(engine,'run_check',check)
    assert client.post('/api/tasks/'+goal['id']+'/approve').status_code==200
    result = finish(client,goal['id'])
    assert sum(row['status']=='failed' for row in result['coverage'])==1
    monkeypatch.setattr(engine,'run_check',original_check)
    return goal,assets,result


def test_selected_goal_round_skips_other_asset_retains_coverage_and_cumulative_progress(client,lab,monkeypatch):
    goal,assets,source = failed_goal(client,lab,monkeypatch)
    path='/api/tasks/'+goal['id']+'/next-plan'
    proposal=client.get(path).json()
    assert proposal['goal_selection']['cells']==[{'asset_id':assets[1]['id'],'check':'cors_policy'}]
    assert proposal['basis']['repeated_completed_cells']==[]
    before=list(lab[1].requests)
    pending=client.post(path,json={'fingerprint':proposal['fingerprint']}).json()
    assert pending['goal_plan']==goal['goal_plan'] and pending['goal_selection']==proposal['goal_selection']
    assert lab[1].requests==before
    assert client.get('/api/tasks/'+pending['id']+'/goal-progress').json()['objectives'][0]['completed']==2
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==200
    result=finish(client,pending['id'])
    assert [(row['asset_id'],row['check'],row['status']) for row in result['coverage']]==[(assets[1]['id'],'cors_policy','completed')]
    assert lab[1].requests[len(before):]==['/other/']
    summary=client.get('/api/overview').json()['coverage_summary']
    assert summary['completed']==4
    progress=client.get('/api/tasks/'+pending['id']+'/goal-progress').json()
    assert all(row['completed']==row['expected']==2 for row in progress['objectives'])
    assert progress['goal_verified'] is False
    reused=progress['objectives'][0]['cells']
    assert all(row['source_task_id']==goal['id'] for row in reused)
    assert client.get('/api/tasks/'+pending['id']+'/next-plan').json()['reason']=='no_remaining_goal_checks'
    assert client.app.state.store.get('coverage',source['coverage'][0]['id'])==source['coverage'][0]


def test_goal_selection_survives_replan_retry_and_same_request_replay(client,lab,monkeypatch):
    goal,assets,_=failed_goal(client,lab,monkeypatch)
    path='/api/tasks/'+goal['id']+'/next-plan'; proposal=client.get(path).json()
    pending=client.post(path,json={'fingerprint':proposal['fingerprint']}).json()
    replacement=client.post('/api/tasks/'+pending['id']+'/replan').json()
    assert replacement['goal_selection']==pending['goal_selection']
    store=client.app.state.store
    store.patch('tasks',replacement['id'],status='interrupted')
    retried=client.post('/api/tasks/'+replacement['id']+'/retry').json()
    assert retried['goal_selection']==pending['goal_selection']
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).json()['id']==retried['id']
    before=list(lab[1].requests)
    assert client.post('/api/tasks/'+retried['id']+'/approve').status_code==200
    finish(client,retried['id'])
    assert lab[1].requests[len(before):]==['/other/']


@pytest.mark.parametrize('damage',['duplicate','outside','source','fingerprint','remove_approved','plan_removed'])
def test_invalid_or_removed_goal_selection_cannot_be_approved(client,lab,monkeypatch,damage):
    goal,assets,_=failed_goal(client,lab,monkeypatch)
    path='/api/tasks/'+goal['id']+'/next-plan'; proposal=client.get(path).json()
    pending=client.post(path,json={'fingerprint':proposal['fingerprint']}).json()
    value=copy.deepcopy(pending['goal_selection'])
    if damage=='duplicate':value['cells']*=2
    elif damage=='outside':value['cells'][0]['check']='security_headers'
    elif damage=='source':value['source_task_id']='other-task'
    elif damage=='fingerprint':value['fingerprint']='0'*64
    elif damage=='remove_approved':value=None
    changes={'goal_selection':value}
    if damage=='remove_approved':changes['goal_selection_contract']=pending['goal_selection']
    if damage=='plan_removed':changes['goal_plan']=None
    client.app.state.store.patch('tasks',pending['id'],**changes)
    before=list(lab[1].requests)
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==409
    assert lab[1].requests==before


def test_goal_todo_repeats_only_requested_pairs_and_records_repeated_completion(client,lab,monkeypatch):
    goal,assets,_=failed_goal(client,lab,monkeypatch)
    path='/api/tasks/'+goal['id']
    assert client.post(path+'/todos',json={'request_id':'a'*32,'title':'Repeat cookie checks','check_ids':['cookie_policy']}).status_code==200
    proposal=client.get(path+'/next-plan').json()
    assert len(proposal['goal_selection']['cells'])==3
    assert len(proposal['basis']['repeated_completed_cells'])==2
    assert {'asset_id':assets[0]['id'],'check':'cors_policy'} not in proposal['goal_selection']['cells']


def test_goal_selection_changed_after_approval_fails_contract_before_execution(client,lab,monkeypatch):
    from aegis import goal_selection
    from aegis.planning_history import PlanningConflict
    goal,assets,_=failed_goal(client,lab,monkeypatch)
    path='/api/tasks/'+goal['id']+'/next-plan';proposal=client.get(path).json()
    pending=client.post(path,json={'fingerprint':proposal['fingerprint']}).json()
    approved={**pending,'approved_at':1,'goal_selection_contract':copy.deepcopy(pending['goal_selection'])}
    goal_planner.require_task(approved)
    approved['goal_selection']['cells'].append({'asset_id':assets[1]['id'],'check':'cookie_policy'})
    approved['goal_selection']['cells'].reverse()
    approved['goal_selection']['fingerprint']=goal_planner.digest({key:value for key,value in approved['goal_selection'].items() if key!='fingerprint'})
    with pytest.raises(PlanningConflict):goal_planner.require_task(approved)
    assert len(lab[1].requests)==2


def test_scope_change_invalidates_selection_review_and_revalidates_only_stale_pairs(client,lab,monkeypatch):
    goal,assets,_=failed_goal(client,lab,monkeypatch)
    path='/api/tasks/'+goal['id']+'/next-plan';old=client.get(path).json()
    store=client.app.state.store;store.patch('assets',assets[0]['id'],revision=2)
    assert client.post(path,json={'fingerprint':old['fingerprint']}).status_code==409
    assert store.count('tasks')==2
    fresh=client.get(path).json()
    assert {(row['asset_id'],row['check']) for row in fresh['goal_selection']['cells']}=={
        (assets[0]['id'],'cookie_policy'),(assets[0]['id'],'cors_policy'),(assets[1]['id'],'cors_policy')}
    pending=client.post(path,json={'fingerprint':fresh['fingerprint']}).json()
    progress=client.get('/api/tasks/'+pending['id']+'/goal-progress').json()
    assert [row['completed'] for row in progress['objectives']]==[1,0]
    before=list(lab[1].requests)
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==200
    result=finish(client,pending['id'])
    assert len(result['coverage'])==3 and sorted(lab[1].requests[len(before):])==['/','/other/']
    assert all(row['completed']==row['expected']==2 for row in client.get('/api/tasks/'+pending['id']+'/goal-progress').json()['objectives'])


def test_damaged_approved_selection_blocks_accepted_request_replay_without_erasing_results(client,lab,monkeypatch):
    goal,assets,_=failed_goal(client,lab,monkeypatch)
    path='/api/tasks/'+goal['id']+'/next-plan';proposal=client.get(path).json()
    pending=client.post(path,json={'fingerprint':proposal['fingerprint']}).json()
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==200
    result=finish(client,pending['id']);store=client.app.state.store
    store.patch('tasks',pending['id'],goal_selection_contract=None)
    before=list(lab[1].requests)
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).status_code==409
    assert client.get('/api/tasks/'+pending['id']+'/next-plan').status_code==409
    assert store.get('coverage',result['coverage'][0]['id'])==result['coverage'][0]
    assert lab[1].requests==before
