"""Goal rounds retain declared objectives and require fresh explicit approval."""
import copy
import pytest
from tests.test_validation import client,lab,finish
from tests.test_goal_evidence import executed_goal
from tests.test_identity import add,login


def test_completed_goal_never_expands_to_unrequested_catalog_checks(client,lab,monkeypatch):
    goal,execution,_=executed_goal(client,lab,monkeypatch);before=list(lab[1].requests)
    path='/api/tasks/'+goal['id']+'/next-plan'
    result=client.get(path);assert result.status_code==200,result.text
    plan=result.json()
    assert not plan['available'] and plan['reason']=='no_remaining_goal_checks'
    assert plan['basis']['missing_checks']==[] and plan['goal_plan']==goal['goal_plan']
    assert lab[1].requests==before


def test_goal_retry_round_retains_objectives_order_and_result_links(client,lab,monkeypatch):
    goal,execution,_=executed_goal(client,lab,monkeypatch);store=client.app.state.store
    coverage=execution['coverage'][0];store.patch('coverage',coverage['id'],status='failed')
    path='/api/tasks/'+goal['id']+'/next-plan';plan=client.get(path).json()
    assert plan['available'] and plan['reason']=='goal_results_followup'
    assert plan['task']['checks']==goal['checks'] and plan['goal_plan']==goal['goal_plan']
    before=list(lab[1].requests)
    following=client.post(path,json={'fingerprint':plan['fingerprint']})
    assert following.status_code==200,following.text
    task=following.json()
    assert task['goal_plan']==goal['goal_plan'] and task['planning_round']==1 and task['status']=='pending'
    assert lab[1].requests==before
    replacement=client.post('/api/tasks/'+task['id']+'/replan').json()
    assert replacement['goal_plan']==task['goal_plan'] and replacement['planning_round']==1
    assert client.post('/api/tasks/'+replacement['id']+'/approve').status_code==200
    finish(client,replacement['id'])
    next_result=client.get('/api/tasks/'+replacement['id']+'/next-plan').json()
    assert not next_result['available'] and next_result['reason']=='no_remaining_goal_checks'
    progress=client.get('/api/tasks/'+replacement['id']+'/goal-progress').json()
    assert progress['goal_verified'] is False and progress['objectives'][0]['completed']==1
    assert client.post(path,json={'fingerprint':plan['fingerprint']}).json()['id']==replacement['id']


def test_goal_todo_requests_require_new_draft_for_extra_checks(client,lab,monkeypatch):
    goal,execution,_=executed_goal(client,lab,monkeypatch)
    path='/api/tasks/'+goal['id']
    created=client.post(path+'/todos',json={'request_id':'b'*32,'title':'쿠키도 확인','check_ids':['cookie_policy']})
    assert created.status_code==200,created.text
    proposal=client.get(path+'/next-plan').json()
    assert not proposal['available'] and proposal['reason']=='goal_scope_change_required'
    assert proposal['basis']['todo_outside_goal_checks']==['cookie_policy']
    assert client.post(path+'/next-plan',json={'fingerprint':proposal['fingerprint']}).status_code==409
    assert client.app.state.store.count('tasks')==2


def test_goal_scope_mutation_invalidates_followup_review(client,lab,monkeypatch):
    goal,execution,_=executed_goal(client,lab,monkeypatch);store=client.app.state.store
    store.patch('coverage',execution['coverage'][0]['id'],status='failed')
    path='/api/tasks/'+goal['id']+'/next-plan';plan=client.get(path).json()
    changed=copy.deepcopy(goal['goal_plan']);changed['decomposition']['objectives'][0]['title']='Changed objective'
    store.patch('tasks',goal['id'],goal_plan=changed)
    assert client.post(path,json={'fingerprint':plan['fingerprint']}).status_code==409
    assert store.count('tasks')==2


def test_sparse_goal_round_preserves_pairs_dependencies_and_discloses_repeated_parent(client,lab,monkeypatch):
    from aegis import engine
    from tests.test_validation import register
    from tests.test_goal_planner import provider,draft
    first=register(client,lab[0]);second=register(client,lab[0]+'other/')
    original=client.post('/api/tasks',json={'name':'Sparse goal round','asset_ids':[first['id'],second['id']],
        'checks':['security_headers'],'workers':2}).json()
    def sparse(plan,prompt):
        plan['objectives'][0]['asset_ids']=[first['id']]
        plan['objectives'][1]['asset_ids']=[second['id']]
        plan['worker_dependencies']={second['id']:[first['id']]}
        return plan
    prompts=provider(monkeypatch,sparse);path,_,drafted=draft(client,original)
    goal=client.post(path+'/'+drafted['id']+'/accept',json={'fingerprint':drafted['fingerprint']}).json()
    original_run=engine.run_check
    def failing(check,*args):
        if check=='cors_policy':raise ValueError('Owned source check failure')
        return original_run(check,*args)
    monkeypatch.setattr(engine,'run_check',failing)
    assert client.post('/api/tasks/'+goal['id']+'/approve').status_code==200
    source_result=finish(client,goal['id'])
    assert [r['status'] for r in source_result['coverage']]==['completed','failed']
    monkeypatch.setattr(engine,'run_check',original_run)
    path='/api/tasks/'+goal['id']+'/next-plan';proposal=client.get(path).json()
    assert proposal['available'] and proposal['basis']['retry_checks']==['cors_policy']
    assert proposal['basis']['repeated_completed_cells']==[goal['id']+':'+first['id']+':cookie_policy']
    pending=client.post(path,json={'fingerprint':proposal['fingerprint']}).json()
    assert pending['goal_plan']==goal['goal_plan']
    assert pending['worker_dependencies']=={second['id']:[first['id']]}
    assert lab[1].requests==['/','/other/']
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==200
    result=finish(client,pending['id'])
    assert {(r['asset_id'],r['check']) for r in result['coverage']}=={(first['id'],'cookie_policy'),(second['id'],'cors_policy')}
    assert all(r['status']=='completed' for r in result['coverage'])
    assert lab[1].requests==['/','/other/','/','/other/'] and len(prompts)==1
    assert client.get('/api/tasks/'+pending['id']+'/next-plan').json()['reason']=='no_remaining_goal_checks'
