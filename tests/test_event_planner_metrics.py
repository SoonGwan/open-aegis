"""Read-only progress reports actual queued rows and untrusted cursor states."""
import copy
import pytest
from aegis.event_planner import STATE_ID,EventPlanner
from tests.test_validation import client,lab
from tests.test_next_plan import completed
from tests.test_event_planner import drain


def settled(client,lab):
    original,_=completed(client,lab);store=client.app.state.store
    planner=client.app.state.event_planner;planner.close();drain(planner)
    return original,store,planner


def test_runtime_progress_counts_sparse_events_without_loading_payloads_or_writing(client,lab,monkeypatch):
    original,store,planner=settled(client,lab)
    before=store.get('planner_state',STATE_ID)['after']
    with store.write_transaction() as db:
        if hasattr(store,'path'):db.execute("UPDATE sqlite_sequence SET seq=? WHERE name='events'",(before+1000,))
        else:db.execute("SELECT setval(pg_get_serial_sequence('events','seq'),%s,true)",(before+1000,))
    store.event(original['id'],'Owned sparse backlog')
    state=store.get('planner_state',STATE_ID);audit=store.audit_integrity();requests=list(lab[1].requests)
    with monkeypatch.context() as patch:
        patch.setattr(store,'events',lambda *a,**kw:pytest.fail('Metrics must aggregate without loading event payloads'))
        progress=client.get('/api/runtime').json()['event_planner']['progress']
    assert progress['status']=='current' and progress['after']==before
    assert progress['latest_event_seq']==before+1001 and progress['pending_events']==1
    assert progress['first_pending_seq']==before+1001 and progress['oldest_pending_seconds']>=0
    assert store.get('planner_state',STATE_ID)==state and store.audit_integrity()==audit and lab[1].requests==requests
    drain(planner)
    progress=planner.metrics()['progress']
    assert progress['pending_events']==0 and progress['oldest_pending_seconds'] is None and progress['asset_page'] is None


def test_policy_replay_reports_all_existing_events_without_resetting_saved_cursor(client,lab):
    original,store,planner=settled(client,lab);state=store.get('planner_state',STATE_ID)
    policy={**client.app.state.engine.policy.public(),'request_budget':12}
    changed=EventPlanner(store,lambda:policy);progress=changed.metrics()['progress']
    assert progress['status']=='replay_required' and progress['after']==0
    assert progress['pending_events']==len(store.events(limit=1000))
    assert store.get('planner_state',STATE_ID)==state
    drain(changed);assert changed.metrics()['progress']['status']=='current'


@pytest.mark.parametrize('damage',['format','boolean','ahead','fanout'])
def test_invalid_cursor_is_unknown_not_empty_and_metrics_never_repairs_it(client,lab,damage):
    original,store,planner=settled(client,lab);state=copy.deepcopy(store.get('planner_state',STATE_ID))
    if damage=='format':state['format']='invalid'
    if damage=='boolean':state['after']=True
    if damage=='ahead':state['after']+=999
    if damage=='fanout':state['fanout']={'event_seq':state['after']+1,'offset':False,'snapshot':None}
    store.put('planner_state',state);audit=store.audit_integrity()
    report=client.get('/api/runtime');assert report.status_code==200
    progress=report.json()['event_planner']['progress']
    assert progress['status']=='invalid' and progress['after'] is None and progress['pending_events'] is None
    assert progress['oldest_pending_seconds'] is None and progress['asset_page'] is None
    assert store.get('planner_state',STATE_ID)==state and store.audit_integrity()==audit


def test_pending_asset_page_remains_visible_until_fanout_commit(client,lab):
    original,store,planner=settled(client,lab);source=store.get('tasks',original['id'])
    for i in range(30):store.put('tasks',{**copy.deepcopy(source),'id':f'owned-metric-page-{i}'})
    store.event(None,'Owned pending asset event',detail={'asset_id':source['asset_ids'][0]})
    assert planner.step();progress=planner.metrics()['progress']
    assert progress['pending_events']==1 and progress['asset_page']=={'event_seq':progress['first_pending_seq'],'task_offset':25}
    assert progress['status']=='current';drain(planner)
    assert planner.metrics()['progress']['pending_events']==0
