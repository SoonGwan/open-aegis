"""Automatically committed failure notes preserve human decisions and never request tools."""
import copy
import pytest
from aegis.event_planner import STATE_ID,EventPlanner
from aegis import observation_todos,todos
from tests.test_observation_rounds import failed_round
from tests.test_validation import client,lab,finish
from tests.test_event_planner import drain,wait_review


def note(client,plan):
    rows=client.get('/api/tasks/'+plan['id']+'/todos').json()['items']
    assert len(rows)==1
    return rows[0]


def test_observation_failure_automatically_records_one_note_and_no_tool_request(client,lab,monkeypatch):
    plan,target,result=failed_round(client,lab,monkeypatch);store=client.app.state.store
    row=note(client,plan)
    assert row['automatic_origin']['source_task_id']==plan['id']
    assert row['automatic_origin']['cells']==[{'observation_id':target['id'],'check':'security_headers'}]
    assert row['check_ids']==[] and row['status']=='open' and row['revision']==1
    history=client.get('/api/tasks/'+plan['id']+'/todos/'+row['id']+'/history').json()['items']
    assert len(history)==1 and history[0]['action']=='automatically_created' and history[0]['actor']['kind']=='system'
    before=list(lab[1].requests);tasks=store.count('tasks')
    store.event(plan['id'],'Owned repeat observation trigger')
    wait_review(store,plan['id'],lambda review:review.get('automatic_todo',{}).get('status')=='existing')
    assert note(client,plan)==row and store.count('tasks')==tasks and lab[1].requests==before
    proposal=client.get('/api/tasks/'+plan['id']+'/next-plan').json()
    assert proposal['basis']['todo_requested_checks']==[] and len(proposal['observation_cells']['cells'])==1
    assert any(item['id']==row['id'] for item in proposal['shared_todo_context']['items'])


@pytest.mark.parametrize('status',['open','done','cancelled'])
def test_automatic_observation_note_does_not_overwrite_human_edit_or_completion(client,lab,monkeypatch,status):
    plan,target,result=failed_round(client,lab,monkeypatch);row=note(client,plan)
    path='/api/tasks/'+plan['id']+'/todos/'+row['id']
    changed=client.patch(path,json={'expected_revision':1,'title':'Human decision','description':'Human explanation',
        'status':status,'resolution_note':'Owned human decision'});assert changed.status_code==200,changed.text
    changed=changed.json();before=list(lab[1].requests)
    client.app.state.store.event(plan['id'],'Owned failed result reconsideration')
    planner=client.app.state.event_planner;planner.close();drain(planner)
    assert client.get(path).json()==changed and lab[1].requests==before
    assert client.get(path+'/history').json()['total']==2


def test_automatic_note_and_review_cursor_audit_roll_back_together_then_replay(client,lab,monkeypatch):
    plan,target,result=failed_round(client,lab,monkeypatch);store=client.app.state.store
    planner=client.app.state.event_planner;planner.close();drain(planner)
    # A new failed pair is a distinct note; existing original notes remain intact.
    coverage=store.get('coverage',plan['id']+':'+plan['asset_ids'][0]+':cookie_policy')
    changed=copy.deepcopy(coverage);changed['targets'][0]['status']='failed';store.put('coverage',changed)
    store.event(plan['id'],'Owned new observed failure trigger')
    def snapshot():
        return {'todos':store.page('todos',limit=100)['items'],'todo_history':store.page('todo_history',limit=100)['items'],
            'review':store.get('plan_reviews',plan['id']),'cursor':store.get('planner_state',STATE_ID)}
    before=snapshot()
    audit=store.audit_integrity();original=store.put_many
    def reject(records,**kwargs):
        if any(kind=='planner_state' for kind,_ in records):raise RuntimeError('owned automatic-note cursor crash')
        return original(records,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(store,'put_many',reject)
        with pytest.raises(RuntimeError,match='cursor crash'):planner.step()
    assert snapshot()==before
    assert store.audit_integrity()==audit
    drain(EventPlanner(store,lambda:client.app.state.engine.policy.public()))
    assert store.count('todos')==2 and store.count('todo_history')==2
    assert store.audit_integrity()['valid']


def test_automatic_note_context_limit_is_visible_without_poisoning_proposal(client,lab,monkeypatch):
    plan,target,result=failed_round(client,lab,monkeypatch);store=client.app.state.store
    planner=client.app.state.event_planner;planner.close();drain(planner)
    coverage=store.get('coverage',plan['id']+':'+plan['asset_ids'][0]+':cookie_policy')
    changed=copy.deepcopy(coverage);changed['targets'][0]['status']='failed';store.put('coverage',changed)
    store.event(plan['id'],'Owned bounded note trigger')
    monkeypatch.setattr(todos,'MAX_CONTEXT_TODOS',1);drain(planner)
    review=client.get('/api/tasks/'+plan['id']+'/planner').json()
    assert review['automatic_todo']['status']=='limited' and review['status']=='ready'
    assert store.count('todos')==1 and review['proposal']['available']


def test_proposal_reviewed_before_automatic_note_is_stale_after_atomic_recording(client,lab,monkeypatch):
    from tests.test_observation_execution import selected
    from aegis import engine
    source,path,body=selected(client,lab,['login'])
    planner=client.app.state.event_planner;planner.close();drain(planner)
    plan=client.post(path,json=body).json();original=engine.run_check
    def fault(check,asset,transport,response):
        if response['url']==lab[0]+'login':raise ValueError('Owned unprepared failure')
        return original(check,asset,transport,response)
    monkeypatch.setattr(engine,'run_check',fault)
    assert client.post('/api/tasks/'+plan['id']+'/approve').status_code==200
    finish(client,plan['id']);route='/api/tasks/'+plan['id']+'/next-plan'
    reviewed=client.get(route).json();assert reviewed['shared_todo_context']['items']==[]
    before=list(lab[1].requests);tasks=client.app.state.store.count('tasks')
    drain(planner);assert note(client,plan)['check_ids']==[]
    assert client.post(route,json={'fingerprint':reviewed['fingerprint']}).status_code==409
    assert client.app.state.store.count('tasks')==tasks and lab[1].requests==before
    assert client.get(route).json()['fingerprint']!=reviewed['fingerprint']


def test_damaged_automatic_origin_blocks_replay_without_overwriting_record(client,lab,monkeypatch):
    plan,target,result=failed_round(client,lab,monkeypatch);store=client.app.state.store
    planner=client.app.state.event_planner;planner.close();drain(planner)
    row=note(client,plan);changed=copy.deepcopy(row);changed['automatic_origin']['source_task_id']='wrong-source'
    store.put('todos',changed);before=list(lab[1].requests)
    store.event(plan['id'],'Owned invalid automatic origin trigger');drain(planner)
    assert store.get('plan_reviews',plan['id'])['status']=='blocked'
    assert store.get('todos',row['id'])==changed and store.count('todo_history')==1 and lab[1].requests==before


def test_legacy_processing_position_replays_failure_events_after_upgrade(client,lab,monkeypatch):
    import hashlib,json
    from tests.test_observation_execution import selected
    from aegis import engine
    source,path,body=selected(client,lab,['login']);store=client.app.state.store
    planner=client.app.state.event_planner;planner.close();drain(planner)
    plan=client.post(path,json=body).json();original=engine.run_check
    def fault(check,asset,transport,response):
        if response['url']==lab[0]+'login':raise ValueError('Owned legacy observed failure')
        return original(check,asset,transport,response)
    monkeypatch.setattr(engine,'run_check',fault)
    assert client.post('/api/tasks/'+plan['id']+'/approve').status_code==200
    finish(client,plan['id']);before=list(lab[1].requests)
    legacy=hashlib.sha256(json.dumps(client.app.state.engine.policy.public(),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    store.put('planner_state',{'id':STATE_ID,'format':'aegis-event-planner-v1','after':store.events(limit=1000)[-1]['seq'],
        'policy_fingerprint':legacy,'fanout':None})
    assert store.count('todos')==0
    resumed=EventPlanner(store,lambda:client.app.state.engine.policy.public());drain(resumed)
    assert note(client,plan)['automatic_origin']['source_task_id']==plan['id']
    assert store.get('planner_state',STATE_ID)['policy_fingerprint']!=legacy
    assert lab[1].requests==before and not resumed.step()
