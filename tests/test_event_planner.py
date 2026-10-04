"""Owned execution/events prove automatic preparation, atomic recovery and no approval."""
import copy
import time
import pytest
from aegis.event_planner import EventPlanner, STATE_ID
from tests.test_validation import client, lab, register, task, finish
from tests.test_next_plan import completed
from tests.test_todos import payload
from tests.test_identity import add, login
from fastapi.testclient import TestClient
from aegis.app import create_app


def wait_review(store, id, predicate=lambda row: row['status']=='ready'):
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        row=store.get('plan_reviews',id)
        if row and predicate(row):return row
        time.sleep(.02)
    pytest.fail('Automatic plan was not prepared from committed events')


def drain(planner):
    for _ in range(500):
        if not planner.step():return
    pytest.fail('Owned event stream did not drain')


def test_automatic_terminal_and_human_events_prepare_without_query_or_execution(client,lab):
    original,_=completed(client,lab)
    store=client.app.state.store;requests=list(lab[1].requests)
    prepared=wait_review(store,original['id'])
    assert prepared['proposal']['task']['checks'] and not prepared['execution_authorized']
    route='/api/tasks/'+original['id']
    assert client.get(route+'/planner').json()['proposal']==prepared['proposal']
    todo=client.post(route+'/todos',json=payload(check_ids=['security_headers'])).json()
    updated=wait_review(store,original['id'],lambda r:r['proposal'] and r['proposal']['basis']['todo_requested_checks']==['security_headers'])
    assert updated['event_seq']>prepared['event_seq']
    assert updated['proposal']['shared_todo_context']['items'][0]['id']==todo['id']
    assert store.count('tasks')==1 and lab[1].requests==requests
    viewer=add(client,'viewer')
    with login(client.app,viewer['username']) as read:
        assert read.get(route+'/planner').status_code==200
        assert read.post(route+'/next-plan',json={'fingerprint':updated['proposal']['fingerprint']}).status_code==403
    assert client.get('/api/runtime').json()['event_planner']['alive']


def test_stale_saved_review_cannot_authorize_and_drain_refreshes_it(client,lab):
    original,path=completed(client,lab);store=client.app.state.store
    planner=client.app.state.event_planner;planner.close();drain(planner)
    saved=store.get('plan_reviews',original['id'])
    client.post('/api/tasks/'+original['id']+'/todos',json=payload(check_ids=['security_headers']))
    review=client.get('/api/tasks/'+original['id']+'/planner').json()
    assert review['stale'] and review['proposal']==saved['proposal']
    assert client.post(path,json={'fingerprint':saved['proposal']['fingerprint']}).status_code==409
    drain(planner)
    assert not client.get('/api/tasks/'+original['id']+'/planner').json()['stale']


def test_proposal_and_event_position_roll_back_together_then_replay(client,lab,monkeypatch):
    original,_=completed(client,lab);store=client.app.state.store
    planner=client.app.state.event_planner;planner.close();drain(planner)
    before=store.get('plan_reviews',original['id']);position=store.get('planner_state',STATE_ID)
    store.event(original['id'],'Owned committed retry trigger')
    put_many=store.put_many
    def reject_position(records,**kwargs):
        if any(kind=='planner_state' for kind,_ in records):raise RuntimeError('owned cursor rollback')
        return put_many(records,**kwargs)
    with monkeypatch.context() as m:
        m.setattr(store,'put_many',reject_position)
        with pytest.raises(RuntimeError,match='owned cursor rollback'):planner.step()
    assert store.get('planner_state',STATE_ID)==position
    assert store.get('plan_reviews',original['id'])==before
    assert planner.step() and store.get('plan_reviews',original['id'])['event_seq']>before['event_seq']
    assert not planner.step()


def test_asset_fanout_is_paged_and_resumes_in_new_processor(client,lab):
    original,_=completed(client,lab);store=client.app.state.store
    planner=client.app.state.event_planner;planner.close();drain(planner)
    source=store.get('tasks',original['id'])
    for index in range(30):store.put('tasks',{**copy.deepcopy(source),'id':f'owned-fanout-{index}'})
    store.event(None,'Owned asset revision trigger',detail={'asset_id':source['asset_ids'][0]})
    assert planner.step()
    position=store.get('planner_state',STATE_ID)
    assert position['fanout']['offset']==25 and store.count('plan_reviews')==26
    resumed=EventPlanner(store,lambda:client.app.state.engine.policy.public())
    drain(resumed)
    assert store.count('plan_reviews')==31
    assert store.get('planner_state',STATE_ID)['fanout'] is None
    assert all(store.get('plan_reviews',f'owned-fanout-{i}')['status']=='ready' for i in range(30))


def test_corrupt_family_is_blocked_without_poisoning_later_events(client,lab):
    original,_=completed(client,lab);store=client.app.state.store
    planner=client.app.state.event_planner;planner.close();drain(planner)
    source=store.get('tasks',original['id'])
    store.put('tasks',{**source,'id':'owned-broken','planning_round':True})
    store.event('owned-broken','Owned invalid lineage')
    store.event(original['id'],'Owned valid continuation')
    drain(planner)
    assert store.get('plan_reviews','owned-broken')['status']=='blocked'
    assert store.get('plan_reviews',original['id'])['status']=='ready'
    assert store.get('planner_state',STATE_ID)['after']==store.events(limit=1000)[-1]['seq']


def test_policy_change_replays_committed_events_without_execution(client,lab):
    original,_=completed(client,lab);store=client.app.state.store
    planner=client.app.state.event_planner;planner.close();drain(planner)
    before=store.get('plan_reviews',original['id']);requests=list(lab[1].requests)
    policy={**client.app.state.engine.policy.public(),'target_rps':1}
    resumed=EventPlanner(store,lambda:policy);drain(resumed)
    updated=store.get('plan_reviews',original['id'])
    assert updated['proposal']['fingerprint']!=before['proposal']['fingerprint']
    assert updated['proposal']['execution_policy']==policy
    assert store.count('tasks')==1 and lab[1].requests==requests


def test_root_todo_event_reaches_current_terminal_followup(client,lab):
    original,path=completed(client,lab);store=client.app.state.store
    proposal=client.get(path).json()
    child=client.post(path,json={'fingerprint':proposal['fingerprint']}).json()
    assert client.post('/api/tasks/'+child['id']+'/approve').status_code==200
    finish(client,child['id']);wait_review(store,child['id'],lambda r:r['status']=='no_proposal')
    requests=list(lab[1].requests)
    client.post('/api/tasks/'+original['id']+'/todos',json=payload(check_ids=['cookie_policy']))
    current=wait_review(store,child['id'])
    assert current['proposal']['task']['checks']==['cookie_policy']
    assert store.count('tasks')==2 and lab[1].requests==requests


def test_missing_and_corrupt_cache_do_not_fabricate_a_proposal(client,lab):
    original,_=completed(client,lab);store=client.app.state.store
    assert client.get('/api/tasks/missing/planner').status_code==404
    planner=client.app.state.event_planner;planner.close();drain(planner)
    row=store.get('plan_reviews',original['id']);store.put('plan_reviews',{**row,'source_task_id':'foreign'})
    response=client.get('/api/tasks/'+original['id']+'/planner').json()
    assert response['status']=='blocked' and response['proposal'] is None and response['stale']


def test_actual_server_restart_consumes_unprocessed_human_event(tmp_path,lab):
    app=create_app(tmp_path/'restart',allow_private=True)
    with TestClient(app) as http:
        assert http.post('/api/auth/setup',json={'password':'aegis-test-password-only'}).status_code==200
        original,_=completed(http,lab)
        wait_review(app.state.store,original['id'])
        app.state.event_planner.close();drain(app.state.event_planner)
        position=app.state.store.get('planner_state',STATE_ID)['after']
        http.post('/api/tasks/'+original['id']+'/todos',json=payload(check_ids=['security_headers']))
    requests=list(lab[1].requests)
    restarted=create_app(tmp_path/'restart',allow_private=True)
    with TestClient(restarted) as http:
        assert http.post('/api/auth/login',json={'username':'admin','password':'aegis-test-password-only'}).status_code==200
        saved=wait_review(restarted.state.store,original['id'],lambda r:r['proposal'] and r['proposal']['basis']['todo_requested_checks']==['security_headers'])
        assert saved['event_seq']>position
        assert not http.get('/api/tasks/'+original['id']+'/planner').json()['stale']
        assert restarted.state.store.count('tasks')==1 and lab[1].requests==requests
