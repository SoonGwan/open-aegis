"""Objective evidence must use source proof; retests remain separately approved history."""
import copy
import pytest
from tests.test_validation import client,lab,register,task,finish
from tests.test_goal_planner import provider,draft
from tests.test_identity import add,login


def executed_goal(client,lab,monkeypatch):
    asset=register(client,lab[0]);original=task(client,asset,['security_headers'])
    def headers(plan,prompt):
        plan['objectives']=plan['objectives'][:1]
        plan['objectives'][0]['checks']=['security_headers']
        return plan
    provider(monkeypatch,headers);path,_,result=draft(client,original)
    goal=client.post(path+'/'+result['id']+'/accept',json={'fingerprint':result['fingerprint']}).json()
    assert client.post('/api/tasks/'+goal['id']+'/approve').status_code==200
    execution=finish(client,goal['id'])
    return goal,execution,'/api/tasks/'+goal['id']+'/goal-objectives/g1/findings'


def test_objective_links_source_proof_and_resolved_retest_without_goal_verification(client,lab,monkeypatch):
    goal,execution,path=executed_goal(client,lab,monkeypatch)
    before=list(lab[1].requests)
    response=client.get(path,params={'limit':1});assert response.status_code==200,response.text
    page=response.json();assert page['total']==len(execution['findings']) and page['has_more']
    assert len(page['items'])==1 and page['goal_verified'] is False
    assert page['items'][0]['evidence_count']==1 and page['items'][0]['latest_retest'] is None
    all_ids=[page['items'][0]['id']]
    for offset in range(1,page['total']):
        next_page=client.get(path,params={'limit':1,'offset':offset,'snapshot':page['snapshot']}).json()
        all_ids.extend(row['id'] for row in next_page['items'])
    assert set(all_ids)=={f['id'] for f in execution['findings']} and len(all_ids)==len(set(all_ids))
    finding=next(f for f in execution['findings'] if f['code']=='missing-nosniff')
    exact=client.get(path,params={'search':finding['title']}).json()
    assert exact['total']==1 and exact['items'][0]['id']==finding['id']
    assert client.get(path,params={'search':'%_'}).json()['total']==0
    assert lab[1].requests==before
    lab[1].hardened=True
    pending=client.post('/api/findings/'+finding['id']+'/retest').json()
    assert lab[1].requests==before
    assert client.get(path,params={'search':finding['title']}).json()['items'][0]['retests_count']==0
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==200
    finish(client,pending['id'])
    after=client.get(path,params={'search':finding['title']}).json()['items'][0]
    assert after['status']=='resolved' and after['retests_count']==1
    assert after['latest_retest']['conclusion']=='resolved' and after['latest_retest']['task_id']==pending['id']
    assert 'evidence_ids' not in after and 'task_ids' not in after
    progress=client.get('/api/tasks/'+goal['id']+'/goal-progress').json()
    assert progress['goal_verified'] is False and progress['objectives'][0]['completed']==1


@pytest.mark.parametrize('damage',['proof_task','proof_asset','proof_check','proof_fingerprint','proof_reference','finding_task'])
def test_objective_refuses_metadata_only_or_mismatched_evidence(client,lab,monkeypatch,damage):
    goal,execution,path=executed_goal(client,lab,monkeypatch);store=client.app.state.store
    finding=store.get('findings',execution['findings'][0]['id']);proof=store.get('evidence',finding['evidence_ids'][0])
    if damage=='proof_reference':store.patch('findings',finding['id'],evidence_ids=[])
    elif damage=='finding_task':store.patch('findings',finding['id'],task_ids=[])
    else:
        key={'proof_task':'task_id','proof_asset':'asset_id','proof_check':'check','proof_fingerprint':'fingerprint'}[damage]
        store.patch('evidence',proof['id'],**{key:'owned-wrong-reference'})
    result=client.get(path).json()
    assert finding['id'] not in {r['id'] for r in result['items']}
    assert result['total']==len(execution['findings'])-1


@pytest.mark.parametrize('damage',['unapproved','finding','asset','check','scope','scope_shape','scope_element','conclusion'])
def test_objective_ignores_unmatched_retest_history(client,lab,monkeypatch,damage):
    goal,execution,path=executed_goal(client,lab,monkeypatch);store=client.app.state.store
    finding=execution['findings'][0]
    retest=client.post('/api/findings/'+finding['id']+'/retest').json()
    assert client.post('/api/tasks/'+retest['id']+'/approve').status_code==200
    finish(client,retest['id'])
    if damage=='unapproved':store.patch('tasks',retest['id'],approved_at=None)
    elif damage=='finding':store.patch('tasks',retest['id'],retest_of='other-finding')
    elif damage=='asset':store.patch('tasks',retest['id'],asset_ids=['other-asset'])
    elif damage=='check':store.patch('tasks',retest['id'],checks=['other-check'])
    elif damage=='scope':store.patch('tasks',retest['id'],scope_snapshot=[])
    elif damage=='scope_shape':store.patch('tasks',retest['id'],scope_snapshot='invalid-scope')
    elif damage=='scope_element':store.patch('tasks',retest['id'],scope_snapshot=['invalid-element'])
    else:
        result=store.page('retests',filters={'finding_id':finding['id']})['items'][0]
        store.patch('retests',result['id'],conclusion='invented')
    row=next(r for r in client.get(path).json()['items'] if r['id']==finding['id'])
    assert row['latest_retest'] is None and row['retests_count']==0


def test_objective_evidence_roles_bounds_and_readonly(client,lab,monkeypatch):
    goal,execution,path=executed_goal(client,lab,monkeypatch)
    viewer=add(client,'viewer','goal-evidence-viewer');login(client,'goal-evidence-viewer')
    store=client.app.state.store;before=store.count('events');requests=list(lab[1].requests)
    assert client.get(path).status_code==200
    for params in ({'limit':101},{'offset':-1},{'snapshot':-1},{'search':'x'*201}):
        assert client.get(path,params=params).status_code==422
    assert client.get(path.replace('/g1/','/g12/')).status_code==404
    assert store.count('events')==before and lab[1].requests==requests
