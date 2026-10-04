"""Owned completed observations affect relevance, never new URL/tool authority."""
import copy
import json
import pytest
from aegis import observation_context as context
from aegis.planning_history import PlanningConflict
from aegis.worker_observations import record_link
from tests.test_validation import client,lab,register,finish
from tests.test_next_plan import completed


def test_real_observation_freezes_with_proposal_and_stale_snapshot_is_refused(client,lab):
    original,path=completed(client,lab,['endpoint_inventory','security_headers']);store=client.app.state.store
    proposal=client.get(path).json();snapshot=proposal['worker_observation_context']
    assert snapshot['counts']=={'total':1,'inspected':1,'included':1,'excluded':0,'omitted':0}
    assert snapshot['items'][0]['category']=='api_path'
    before=list(lab[1].requests)
    source=store.get('tasks',original['id']);asset=source['scope_snapshot'][0]
    record_link(store,source,asset,'endpoint_inventory',lab[0]+'login')
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).status_code==409
    fresh=client.get(path).json();accepted=client.post(path,json={'fingerprint':fresh['fingerprint']}).json()
    assert accepted['worker_observation_context']==fresh['worker_observation_context']
    record_link(store,source,asset,'endpoint_inventory',lab[0]+'admin')
    assert store.get('tasks',accepted['id'])['worker_observation_context']['counts']['included']==2
    assert client.post(path,json={'fingerprint':fresh['fingerprint']}).json()['id']==accepted['id']
    assert accepted['status']=='pending' and lab[1].requests==before


@pytest.mark.parametrize('damage',['provenance','coverage','revision','query','key','id_type'])
def test_unconfirmed_incomplete_or_changed_scope_is_excluded(client,lab,damage):
    original,path=completed(client,lab,['endpoint_inventory']);store=client.app.state.store
    source=store.get('tasks',original['id']);asset=source['scope_snapshot'][0]
    row=store.page('observations',filters={'task_id':original['id']})['items'][0]
    if damage=='provenance':store.patch('observations',row['id'],verified=True)
    elif damage=='coverage':store.patch('coverage',f"{original['id']}:{asset['id']}:endpoint_inventory",status='failed')
    elif damage=='revision':store.patch('assets',asset['id'],revision=2)
    elif damage=='query':
        store.patch('observations',row['id'],verified=True)
        record_link(store,source,asset,'endpoint_inventory',lab[0]+'api?token=owned-private-marker')
    elif damage=='id_type':
        marker='%s' if getattr(store,'backend',None)=='postgres' else '?'
        with store.write_transaction() as db:
            db.execute(f"UPDATE records SET data={marker} WHERE kind='observations' AND id={marker}",
                       (json.dumps({**row,'id':['malformed']}),row['id']))
    else:
        data=store.get('observations',row['id']);store.put('observations',{**data,'id':'wrong-key'})
        store.patch('observations',row['id'],verified=True)
    snapshot=client.get(path).json()['worker_observation_context']
    assert snapshot['items']==[] and snapshot['counts']['excluded']==snapshot['counts']['inspected']
    assert context.priorities(snapshot)==[]


def test_sampling_counts_are_explicit_and_frozen_validation_refuses_tampering(client,lab):
    original,_=completed(client,lab,['endpoint_inventory']);store=client.app.state.store
    source=store.get('tasks',original['id']);asset=source['scope_snapshot'][0]
    for i in range(105):record_link(store,source,asset,'endpoint_inventory',lab[0]+f'api/items/{i}')
    snapshot=context.snapshot(store,original['id'])
    assert snapshot['counts']=={'total':106,'inspected':100,'included':100,'excluded':0,'omitted':6}
    assert context.priorities(snapshot)==['cors_policy','api_authorization']
    for field,value in [('category','forged'),('url',lab[0]+'foreign'),('scope_revision',True)]:
        forged=copy.deepcopy(snapshot);forged['items'][0][field]=value
        with pytest.raises(PlanningConflict):context.require(forged)
    forged=copy.deepcopy(snapshot);forged['counts']['excluded']=True
    with pytest.raises(PlanningConflict):context.require(forged)


def test_context_byte_budget_refuses_overflow_without_truncating_fields(client,lab):
    original,_=completed(client,lab,['endpoint_inventory']);store=client.app.state.store
    source=store.get('tasks',original['id']);asset=source['scope_snapshot'][0]
    for i in range(50):record_link(store,source,asset,'endpoint_inventory',lab[0]+'api/'+str(i)+'x'*1500)
    with pytest.raises(PlanningConflict,match='64KiB'):context.snapshot(store,original['id'])
    assert store.count('observations')==51


def test_malformed_observation_page_refuses_planning_without_partial_context(client,lab):
    original,path=completed(client,lab,['endpoint_inventory']);store=client.app.state.store
    row=store.page('observations',filters={'task_id':original['id']})['items'][0]
    store.patch('observations',row['id'],asset_id=['malformed'])
    assert client.get(path).status_code==409
    assert store.count('tasks')==1


def test_approved_provider_reads_frozen_categories_without_urls_or_extra_checks(client,lab,monkeypatch):
    prompts=[]
    monkeypatch.setenv('AEGIS_LLM_API_KEY','owned-provider-key')
    monkeypatch.setenv('AEGIS_LLM_MODEL','owned-observation-model')
    def provider(base,key,request,**kwargs):
        prompt=json.loads(request['messages'][1]['content']);prompts.append(prompt)
        return {'choices':[{'message':{'content':json.dumps({'checks':prompt['checks']})}}]}
    monkeypatch.setattr('aegis.engine.completion',provider)
    asset=register(client,lab[0])
    original=client.post('/api/tasks',json={'name':'Owned observation AI','asset_ids':[asset['id']],
        'checks':['endpoint_inventory','security_headers'],'planner':'ai'}).json()
    client.post('/api/tasks/'+original['id']+'/approve');finish(client,original['id'])
    path='/api/tasks/'+original['id']+'/next-plan';proposal=client.get(path).json()
    accepted=client.post(path,json={'fingerprint':proposal['fingerprint']}).json()
    source=client.app.state.store.get('tasks',original['id'])
    record_link(client.app.state.store,source,source['scope_snapshot'][0],'endpoint_inventory',lab[0]+'login')
    client.post('/api/tasks/'+accepted['id']+'/approve');finish(client,accepted['id'])
    prompt=prompts[-1]
    assert len(prompt['worker_observations'])==1 and prompt['worker_observations'][0]['category']=='api_path'
    assert set(prompt['worker_observations'][0])=={'id','task_id','asset_id','scope_revision','category'}
    assert lab[0] not in json.dumps(prompt) and 'url' not in json.dumps(prompt['worker_observations'])
    assert set(prompt['checks'])==set(accepted['checks'])
    result=client.app.state.store.get('tasks',accepted['id'])
    assert result['plan'][:2]==['cors_policy','api_authorization']
    assert result['llm_usage']['observation_context_fingerprint']==proposal['worker_observation_context']['fingerprint']
    assert result['llm_usage']['observation_references']==[proposal['worker_observation_context']['items'][0]['id']]
    assert '/api/account' not in lab[1].requests and '/login' not in lab[1].requests
    corrupt=copy.deepcopy(result);corrupt['worker_observation_context']['items'][0]['category']='management_path'
    count=len(prompts)
    with pytest.raises(PlanningConflict):client.app.state.engine.plan(corrupt)
    assert len(prompts)==count
    scoped={**result,'planner':'rules','checks':['security_headers']}
    assert client.app.state.engine.plan(scoped)==['security_headers']
