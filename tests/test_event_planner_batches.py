"""Bounded event replay preserves latest triggers, atomicity and asset fanout order."""
import copy
import pytest
from aegis.event_planner import STATE_ID,EventPlanner
from tests.test_validation import client,lab
from tests.test_next_plan import completed
from tests.test_event_planner import drain


def setup(client,lab):
    original,_=completed(client,lab);store=client.app.state.store
    planner=client.app.state.event_planner;planner.close();drain(planner)
    return store.get('tasks',original['id']),store,planner


def clone(store,original,id):
    row={**copy.deepcopy(original),'id':id};store.put('tasks',row);return row


def last(store):return store.events(after=0,limit=1000)[-1]['seq']


def test_batch_prepares_each_affected_task_from_its_latest_trigger(client,lab):
    original,store,planner=setup(client,lab)
    other=clone(store,original,'owned-batch-other')
    store.event(original['id'],'Owned earlier trigger')
    store.event(other['id'],'Owned independent task trigger');other_seq=last(store)
    store.event(original['id'],'Owned latest trigger');latest=last(store)
    requests=list(lab[1].requests);tasks=store.count('tasks')
    assert planner.step()
    independent=store.get('plan_reviews',other['id'])
    assert independent is not None,'Committed task prefix must prepare the independent task'
    assert independent['event_seq']==other_seq
    assert store.get('plan_reviews',original['id'])['event_seq']==latest
    assert store.get('planner_state',STATE_ID)['after']==latest
    assert not planner.step() and store.count('tasks')==tasks and lab[1].requests==requests
    assert all(not store.get('plan_reviews',id)['execution_authorized'] for id in (original['id'],other['id']))


def test_batch_cursor_failure_rolls_back_all_task_reviews_and_audit(client,lab,monkeypatch):
    original,store,planner=setup(client,lab);other=clone(store,original,'owned-batch-rollback')
    store.event(original['id'],'Owned batch first');store.event(other['id'],'Owned batch second')
    before=[store.get('plan_reviews',id) for id in (original['id'],other['id'])]
    cursor=store.get('planner_state',STATE_ID);audit=store.audit_integrity();put=store.put_many
    def reject(records,**kwargs):
        if any(kind=='planner_state' for kind,_ in records):raise RuntimeError('owned batch cursor failure')
        return put(records,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(store,'put_many',reject)
        with pytest.raises(RuntimeError,match='batch cursor failure'):planner.step()
    assert before==[store.get('plan_reviews',id) for id in (original['id'],other['id'])]
    assert cursor==store.get('planner_state',STATE_ID) and audit==store.audit_integrity()
    assert planner.step() and store.get('plan_reviews',other['id'])['status']=='ready'
    assert store.audit_integrity()['valid']


def test_batch_stops_before_asset_event_and_resumes_fanout_before_later_triggers(client,lab):
    original,store,planner=setup(client,lab)
    for i in range(30):clone(store,original,f'owned-batch-fanout-{i}')
    store.event(original['id'],'Owned before asset');before_asset=last(store)
    store.event(None,'Owned asset boundary',detail={'asset_id':original['asset_ids'][0]});asset_seq=last(store)
    store.event(original['id'],'Owned after asset');after_asset=last(store)
    assert planner.step() and store.get('planner_state',STATE_ID)['after']==before_asset
    assert planner.step();state=store.get('planner_state',STATE_ID)
    assert state['after']==before_asset and state['fanout']['offset']==25
    resumed=EventPlanner(store,lambda:client.app.state.engine.policy.public())
    assert resumed.step();state=store.get('planner_state',STATE_ID)
    assert state['after']==asset_seq and state['fanout'] is None
    assert resumed.step() and store.get('planner_state',STATE_ID)['after']==after_asset
    assert store.count('plan_reviews')==31 and not resumed.step()


def test_batch_keeps_a_bounded_durable_prefix_and_processes_remaining_tasks(client,lab):
    original,store,planner=setup(client,lab);ids=[];seqs=[]
    for i in range(28):
        row=clone(store,original,f'owned-bounded-batch-{i}');ids.append(row['id'])
        store.event(row['id'],'Owned bounded trigger');seqs.append(last(store))
    assert planner.step()
    assert store.get('planner_state',STATE_ID)['after']==seqs[24]
    assert all(store.get('plan_reviews',id) for id in ids[:25])
    assert not any(store.get('plan_reviews',id) for id in ids[25:])
    assert planner.step() and store.get('planner_state',STATE_ID)['after']==seqs[-1]
    assert all(store.get('plan_reviews',id) for id in ids) and not planner.step()
