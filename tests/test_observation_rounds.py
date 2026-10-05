"""Selective URL/check continuation sends only failed or explicitly requested GETs."""
import copy
import time
import pytest
from aegis import engine,observation_execution
from tests.test_validation import client,lab,finish
from tests.test_observation_execution import selected


def failed_round(client,lab,monkeypatch):
    source,path,body=selected(client,lab,['login'])
    body['checks']=['security_headers','cookie_policy']
    plan=client.post(path,json=body).json()
    original=engine.run_check
    def fault(check,asset,transport,response):
        if check=='security_headers' and response['url']==lab[0]+'login':raise ValueError('Owned selected cell failure')
        return original(check,asset,transport,response)
    monkeypatch.setattr(engine,'run_check',fault)
    assert client.post('/api/tasks/'+plan['id']+'/approve').status_code==200
    result=finish(client,plan['id']);monkeypatch.setattr(engine,'run_check',original)
    target=next(row for row in plan['observation_execution']['targets'] if row['url']==lab[0]+'login')
    return plan,target,result


def test_observation_followup_selects_failed_cell_only_and_reuses_other_completed_proof(client,lab,monkeypatch):
    plan,target,result=failed_round(client,lab,monkeypatch);path='/api/tasks/'+plan['id']+'/next-plan'
    preview=client.get(path);assert preview.status_code==200,preview.text
    proposal=preview.json();assert proposal['available'] and proposal['execution_authorized'] is False
    assert proposal['observation_cells']['cells']==[{'observation_id':target['id'],'check':'security_headers'}]
    before=list(lab[1].requests);summary=client.get('/api/overview').json()['coverage_summary']
    for _ in range(100):
        auto=client.get('/api/tasks/'+plan['id']+'/planner').json()
        if auto['status']=='ready' and not auto.get('stale'):break
        time.sleep(.02)
    assert auto['status']=='ready' and auto['proposal']['fingerprint']==proposal['fingerprint']
    pending=client.post(path,json={'fingerprint':proposal['fingerprint']});assert pending.status_code==200,pending.text
    pending=pending.json()
    assert pending['approved_at'] is None and lab[1].requests==before
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).json()['id']==pending['id']
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==200
    execution=finish(client,pending['id'])
    assert lab[1].requests[len(before):]==['/login']
    assert [(row['check'],len(row['targets'])) for row in execution['coverage']]==[('security_headers',1)]
    assert client.get('/api/tasks/'+pending['id']+'/next-plan').json()['reason']=='no_remaining_observation_checks'
    assert client.get('/api/overview').json()['coverage_summary']==summary


@pytest.mark.parametrize('damage',['remove','duplicate','outside','source'])
def test_observation_followup_tamper_blocks_approval_and_replay(client,lab,monkeypatch,damage):
    plan,target,result=failed_round(client,lab,monkeypatch);path='/api/tasks/'+plan['id']+'/next-plan'
    proposal=client.get(path).json();pending=client.post(path,json={'fingerprint':proposal['fingerprint']}).json()
    cells=copy.deepcopy(pending['observation_cells'])
    if damage=='remove':cells=None
    else:
        if damage=='duplicate':cells['cells']*=2
        elif damage=='outside':cells['cells'][0]['observation_id']='a'*64
        else:cells['source_task_id']='other-task'
        cells['fingerprint']=observation_execution.digest({k:v for k,v in cells.items() if k!='fingerprint'})
    client.app.state.store.patch('tasks',pending['id'],observation_cells=cells);before=list(lab[1].requests)
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==409
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).status_code==409
    assert lab[1].requests==before


def test_observation_round_todo_requests_completed_check_but_refuses_new_check(client,lab,monkeypatch):
    plan,target,result=failed_round(client,lab,monkeypatch);path='/api/tasks/'+plan['id']+'/next-plan'
    todo=client.post('/api/tasks/'+plan['id']+'/todos',json={'title':'Repeat cookie checks','request_id':'b'*32,'check_ids':['cookie_policy']})
    assert todo.status_code==200,todo.text
    proposal=client.get(path).json()
    assert proposal['available'] and len(proposal['observation_cells']['cells'])==3
    assert sum(cell['check']=='cookie_policy' for cell in proposal['observation_cells']['cells'])==2
    outside=client.post('/api/tasks/'+plan['id']+'/todos',json={'title':'New API check','request_id':'c'*32,'check_ids':['api_authorization']})
    assert outside.status_code==200,outside.text
    changed=client.get(path).json()
    assert not changed['available'] and changed['reason']=='observation_scope_change_required'
    before=list(lab[1].requests)
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).status_code==409
    assert lab[1].requests==before


def test_observation_round_replan_retry_preserves_cells_and_requires_fresh_approval(client,lab,monkeypatch):
    plan,target,result=failed_round(client,lab,monkeypatch);path='/api/tasks/'+plan['id']+'/next-plan'
    proposal=client.get(path).json();pending=client.post(path,json={'fingerprint':proposal['fingerprint']}).json()
    replacement=client.post('/api/tasks/'+pending['id']+'/replan');assert replacement.status_code==200,replacement.text
    replacement=replacement.json();assert replacement['observation_cells']==pending['observation_cells']
    client.app.state.store.patch('tasks',replacement['id'],status='interrupted')
    retry=client.post('/api/tasks/'+replacement['id']+'/retry');assert retry.status_code==200,retry.text
    retry=retry.json();assert retry['observation_cells']==pending['observation_cells'] and retry['approved_at'] is None
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).json()['id']==retry['id']
    before=list(lab[1].requests)
    assert client.post('/api/tasks/'+retry['id']+'/approve').status_code==200
    finish(client,retry['id']);assert lab[1].requests[len(before):]==['/login']


def test_observation_round_creation_race_rolls_back_source_child_and_coverage(client,lab,monkeypatch):
    from aegis import next_plan
    plan,target,result=failed_round(client,lab,monkeypatch);store=client.app.state.store
    path='/api/tasks/'+plan['id']+'/next-plan';proposal=client.get(path).json()
    cells=store.count('coverage');tasks=store.count('tasks');original=next_plan.propose
    coverage_id=plan['id']+':'+plan['asset_ids'][0]+':security_headers'
    before_coverage=store.get('coverage',coverage_id)
    def race(*args,**kwargs):
        db=kwargs.get('connection')
        if db is not None:
            row=store.get('coverage',plan['id']+':'+plan['asset_ids'][0]+':security_headers',connection=db)
            changed=copy.deepcopy(row);changed['targets'][0]['status']='cancelled'
            # Changing another target status must invalidate the reviewed fingerprint.
            if changed==row:changed['targets'][0]['status']='completed'
            store.put_many([('coverage',changed)],connection=db)
        return original(*args,**kwargs)
    # Stop the event consumer to keep this owned race scoped to acceptance.
    client.app.state.event_planner.close()
    monkeypatch.setattr(next_plan,'propose',race)
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).status_code==409
    assert store.count('tasks')==tasks and store.count('coverage')==cells
    assert not store.get('tasks',plan['id']).get('next_plan_id')
    assert store.get('coverage',coverage_id)==before_coverage


def test_observation_goal_followup_preserves_objective_without_changing_goal_progress(client,lab,monkeypatch):
    from tests.test_goal_observations import goal_source
    from aegis.worker_observations import record_link
    goal,assets,path,preview,body=goal_source(client,lab,monkeypatch);store=client.app.state.store
    record_link(store,store.get('tasks',goal['id']),assets[0],'endpoint_inventory',lab[0]+'login')
    preview=client.get(path).json();body.update(fingerprint=preview['fingerprint'],observation_ids=[row['id'] for row in preview['context']['items']])
    plan=client.post(path,json=body).json();original=engine.run_check
    def fault(check,asset,transport,response):
        if response['url']==lab[0]+'login':raise ValueError('Owned goal observation failure')
        return original(check,asset,transport,response)
    monkeypatch.setattr(engine,'run_check',fault)
    assert client.post('/api/tasks/'+plan['id']+'/approve').status_code==200
    finish(client,plan['id']);monkeypatch.setattr(engine,'run_check',original)
    progress=client.get('/api/tasks/'+goal['id']+'/goal-progress').json()
    route='/api/tasks/'+plan['id']+'/next-plan';proposal=client.get(route);assert proposal.status_code==200,proposal.text
    proposal=proposal.json();pending=client.post(route,json={'fingerprint':proposal['fingerprint']})
    assert pending.status_code==200,pending.text
    pending=pending.json();assert pending['goal_observation']==plan['goal_observation']
    assert pending['observation_cells']['cells'][0]['check']=='security_headers'
    before=list(lab[1].requests)
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==200
    finish(client,pending['id']);assert lab[1].requests[len(before):]==['/login']
    assert client.get('/api/tasks/'+goal['id']+'/goal-progress').json()==progress


def test_observation_rounds_stop_at_eight_with_no_implicit_execution(client,lab,monkeypatch):
    plan,target,result=failed_round(client,lab,monkeypatch);original=engine.run_check
    def fault(check,asset,transport,response):
        if check=='security_headers' and response['url']==lab[0]+'login':raise ValueError('Owned persistent failure')
        return original(check,asset,transport,response)
    monkeypatch.setattr(engine,'run_check',fault);before=list(lab[1].requests)
    current=plan
    for number in range(1,9):
        path='/api/tasks/'+current['id']+'/next-plan';proposal=client.get(path).json()
        assert proposal['available'] and proposal['planning_round']==number
        child=client.post(path,json={'fingerprint':proposal['fingerprint']});assert child.status_code==200,child.text
        current=child.json();assert current['approved_at'] is None
        assert client.post('/api/tasks/'+current['id']+'/approve').status_code==200
        finish(client,current['id'])
    final=client.get('/api/tasks/'+current['id']+'/next-plan').json()
    assert not final['available'] and final['reason']=='round_limit' and final['round_limit']==8
    assert client.post('/api/tasks/'+current['id']+'/next-plan',json={'fingerprint':final['fingerprint']}).status_code==409
    assert lab[1].requests[len(before):]==['/login']*8


def test_observation_history_limit_is_distinct_from_round_limit(client,lab,monkeypatch):
    from aegis import observation_rounds
    plan,target,result=failed_round(client,lab,monkeypatch);route='/api/tasks/'+plan['id']+'/next-plan'
    proposal=client.get(route).json();child=client.post(route,json={'fingerprint':proposal['fingerprint']}).json()
    assert client.post('/api/tasks/'+child['id']+'/approve').status_code==200
    finish(client,child['id'])
    # Exercise the same history boundary with two real approved attempts rather
    # than inventing32 tasks; the configured production limit remains32.
    monkeypatch.setattr(observation_rounds,'MAX_HISTORY',2)
    final=client.get('/api/tasks/'+child['id']+'/next-plan').json()
    assert final['history_count']==2 and final['history_limit']==2 and final['round_limit']==8
    assert not final['available'] and final['reason']=='history_limit'
