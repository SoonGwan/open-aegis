"""Owned DAG execution consumes persisted predecessor evidence without widening scope."""
import time
import pytest
from tests.test_validation import client,lab,register,finish
from tests.test_runtime import peer


def create(client,assets,dependencies,checks=None):
    return client.post('/api/tasks',json={'name':'Owned dependent Workers','asset_ids':[a['id'] for a in assets],
        'workers':2,'checks':checks or ['endpoint_inventory','security_headers'],'worker_dependencies':dependencies})


def test_owned_dependency_order_handoff_and_no_requests_before_approval(client,lab):
    url,handler=lab
    parent=register(client,url,name='Parent');child=register(client,url+'api/account',name='Child')
    plan=create(client,[child,parent],{child['id']:[parent['id']]}).json()
    assert plan['status']=='pending' and handler.requests==[]
    assert client.post('/api/tasks/'+plan['id']+'/approve').status_code==200
    result=finish(client,plan['id'])
    assert result['task']['status']=='completed' and result['task']['errors']==0 and result['task']['done']==2
    assert handler.requests==['/','/api/account']
    assert all(row['status']=='completed' for row in result['coverage'])
    events=client.app.state.store.event_page(plan['id'],asset_id=child['id'])['items']
    handoff=next(row for row in events if 'dependency_inputs' in row['detail'])['detail']['dependency_inputs'][0]
    assert handoff['source_worker_id']==plan['id']+':'+parent['id']
    assert handoff['checks_completed']==plan['checks'] and len(handoff['observation_ids'])==1
    observed=client.app.state.store.get('observations',handoff['observation_ids'][0])
    assert observed['asset_id']==parent['id'] and observed['url']==url+'api/account'
    assert result['task']['worker_dependency_contract']['dependencies']==plan['worker_dependencies']


def test_failed_predecessor_blocks_child_and_descendant_without_requests(client,lab):
    url,handler=lab;handler.fault=True
    assets=[register(client,url+path,name=path or 'root') for path in ('','api/account','last')]
    parent,child,last=assets
    plan=create(client,assets,{child['id']:[parent['id']],last['id']:[child['id']]}).json()
    client.post('/api/tasks/'+plan['id']+'/approve')
    result=finish(client,plan['id'])
    assert result['task']['status']=='failed' and result['task']['done']==3
    assert handler.requests==['/','/']  # Existing one-retry policy applies only to the parent.
    children=[row for row in result['coverage'] if row['asset_id']!=parent['id']]
    assert all(row['status']=='failed' and row['error_type']=='WorkerDependencyBlocked' for row in children)


@pytest.mark.parametrize('case',['self','cycle','foreign','duplicate','wrong_type'])
def test_invalid_dependencies_refused_before_work(client,lab,case):
    url,handler=lab;a=register(client,url);b=register(client,url+'api/account')
    deps={'self':{a['id']:[a['id']]},'cycle':{a['id']:[b['id']],b['id']:[a['id']]},
          'foreign':{a['id']:['missing']},'duplicate':{b['id']:[a['id'],a['id']]},'wrong_type':{b['id']:'bad'}}[case]
    assert create(client,[a,b],deps).status_code==422
    assert client.app.state.store.count('tasks')==0 and handler.requests==[]


def test_changed_dependency_contract_before_worker_run_is_not_executed(client,lab,monkeypatch):
    url,handler=lab;a=register(client,url);b=register(client,url+'api/account')
    plan=create(client,[a,b],{b['id']:[a['id']]}).json()
    engine=client.app.state.engine
    original=engine.run
    def altered(id):
        client.app.state.store.patch('tasks',id,worker_dependencies={})
        return original(id)
    monkeypatch.setattr(engine,'run',altered)
    assert client.post('/api/tasks/'+plan['id']+'/approve').status_code==200
    result=finish(client,plan['id'])
    assert result['task']['status']=='failed' and handler.requests==[]
    assert result['task']['termination_reason']=='worker_dependency_changed'


def test_corrupt_completed_source_coverage_blocks_handoff(client,lab,monkeypatch):
    url,handler=lab;a=register(client,url);b=register(client,url+'api/account')
    plan=create(client,[a,b],{b['id']:[a['id']]}).json()
    engine=client.app.state.engine;original=engine.validate_asset
    def corrupt(task,asset,checks,control,inputs=None):
        outcome=original(task,asset,checks,control,inputs)
        if asset['id']==a['id']:
            client.app.state.store.patch('coverage',f"{task['id']}:{a['id']}:endpoint_inventory",asset_revision=2)
        return outcome
    monkeypatch.setattr(engine,'validate_asset',corrupt)
    client.post('/api/tasks/'+plan['id']+'/approve')
    result=finish(client,plan['id'])
    assert result['task']['done']==2 and result['task']['errors']==1
    assert handler.requests==['/']
    assert all(row.get('error_type')=='WorkerDependencyBlocked' for row in result['coverage'] if row['asset_id']==b['id'])


def test_join_waits_for_all_predecessors_and_independent_worker_runs(client,lab,peer):
    url,handler=lab;held,slow=peer
    parent=register(client,held+'held',name='Held parent')
    sibling=register(client,url,name='Independent sibling')
    child=register(client,url+'api/account',name='Join child')
    plan=create(client,[child,parent,sibling],{child['id']:[parent['id'],sibling['id']]},checks=['security_headers']).json()
    client.post('/api/tasks/'+plan['id']+'/approve')
    assert slow.entered.wait(2)
    deadline=time.monotonic()+2
    while client.app.state.store.get('tasks',plan['id'])['done']<1 and time.monotonic()<deadline:time.sleep(.01)
    assert client.app.state.store.get('tasks',plan['id'])['done']==1
    assert handler.requests==['/']
    slow.release.set()
    result=finish(client,plan['id'])
    assert result['task']['status']=='completed' and result['task']['done']==3
    assert handler.requests==['/','/api/account'] and [p for p,_ in slow.calls]==['/held']
    event=next(row for row in client.app.state.store.event_page(plan['id'],asset_id=child['id'])['items'] if 'dependency_inputs' in row['detail'])
    assert {i['asset_id'] for i in event['detail']['dependency_inputs']}=={parent['id'],sibling['id']}


def test_stop_held_parent_cancels_pending_dependency_without_child_request(client,peer,monkeypatch):
    url,handler=peer
    parent=register(client,url+'held');child=register(client,url+'child')
    plan=create(client,[child,parent],{child['id']:[parent['id']]},checks=['security_headers']).json()
    import concurrent.futures, threading
    waiting, release = threading.Event(), threading.Event()
    original_wait=concurrent.futures.wait
    def observed_wait(futures,**kwargs):
        if not waiting.is_set():
            waiting.set();assert release.wait(3)
            return set(),set(futures)
        return original_wait(futures,**kwargs)
    monkeypatch.setattr(concurrent.futures,'wait',observed_wait)
    client.post('/api/tasks/'+plan['id']+'/approve')
    assert handler.entered.wait(2)
    assert waiting.wait(2)
    client.post('/api/tasks/'+plan['id']+'/stop')
    release.set()
    result=finish(client,plan['id'])
    assert result['task']['status']=='stopped' and result['task']['done']==1
    assert all(row['status']=='cancelled' for row in result['coverage'])
    assert [path for path,_ in handler.calls]==['/held']


def test_replan_preserves_dependencies_but_requires_new_approval(client,lab):
    url,handler=lab;a=register(client,url);b=register(client,url+'api/account')
    plan=create(client,[a,b],{b['id']:[a['id']]}).json()
    replacement=client.post('/api/tasks/'+plan['id']+'/replan').json()
    assert replacement['worker_dependencies']==plan['worker_dependencies']
    assert replacement['status']=='pending' and replacement['approved_at'] is None and handler.requests==[]
