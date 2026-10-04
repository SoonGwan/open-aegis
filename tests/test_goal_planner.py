"""Natural-language provider decomposition becomes a reviewed, separately approved plan."""
import copy
import json
import pytest
from aegis import goal_planner
from aegis.usage import usage_summary
from tests.test_validation import client, lab, register, task, finish
from tests.test_identity import add, login


def source(client, lab):
    return task(client,register(client,lab[0]),['security_headers'])


def provider(monkeypatch, reply=None):
    prompts=[]
    monkeypatch.setenv('AEGIS_LLM_API_KEY','owned-goal-key-only')
    monkeypatch.setenv('AEGIS_LLM_MODEL','owned-goal-model')
    def completion(base,key,payload,**kwargs):
        prompt=json.loads(payload['messages'][1]['content']);prompts.append(prompt)
        ids=[a['id'] for a in prompt['assets']]
        objectives=[{'id':'g1','title':'세션 쿠키 속성 확인','rationale':'인증 세션 목표에 맞춘 쿠키 설정 검토',
            'asset_ids':ids,'checks':['cookie_policy'],'expected_evidence':'쿠키의 필수 보안 속성 검사 결과', 'missing_inputs':[]},
            {'id':'g2','title':'교차 출처 정책 검토','rationale':'API 공개 범위 목표와 응답 선언 정책 비교',
             'asset_ids':ids,'checks':['cors_policy'],'expected_evidence':'응답의 선언된 허용 출처','missing_inputs':['실제 보호 데이터 여부는 별도로 확인해야 합니다.']}]
        plan={'objectives':objectives,'worker_dependencies':{}}
        if reply is not None:plan=reply(copy.deepcopy(plan),prompt)
        return {'choices':[{'message':{'content':json.dumps(plan)}}],
                'usage':{'prompt_tokens':30,'completion_tokens':15,'total_tokens':45}}
    monkeypatch.setattr(goal_planner,'completion',completion)
    return prompts


def draft(client, original, request_id='c'*32, mode='ai'):
    path='/api/tasks/'+original['id']+'/goal-plans'
    data={'request_id':request_id,'mode':mode,'goal':'인증 세션 쿠키 설정과 API 교차 출처 정책을 확인해주세요.'}
    response=client.post(path,json=data)
    assert response.status_code==200,response.text
    return path,data,response.json()


def test_goal_decomposition_is_reviewed_before_target_execution_and_usage_is_preserved(client,lab,monkeypatch):
    original=source(client,lab);prompts=provider(monkeypatch)
    path,data,result=draft(client,original)
    assert result['mode']=='ai' and [r['checks'] for r in result['decomposition']['objectives']]==[['cookie_policy'],['cors_policy']]
    assert prompts[0]['goal']==data['goal'] and lab[0] not in json.dumps(prompts)
    assert lab[1].requests==[] and client.app.state.store.count('tasks')==1
    assert client.post(path,json=data).json()['id']==result['id'] and len(prompts)==1
    assert client.post(path,json={**data,'goal':'different goal'}).status_code==409
    assert client.get(path+'/'+result['id']).json()==result
    summary=usage_summary(client.app.state.store,source='planner')
    assert summary['calls']==1 and summary['reported_tokens']['total_tokens']=='45'
    calls=client.app.state.store.page('llm_calls')['items']
    assert calls[0]['state']=='committed' and calls[0]['record_kind']=='goal_plans'
    accept=path+'/'+result['id']+'/accept';body={'fingerprint':result['fingerprint']}
    accepted=client.post(accept,json=body)
    assert accepted.status_code==200,accepted.text
    planned=accepted.json()
    assert planned['status']=='pending' and not planned['approved_at'] and lab[1].requests==[]
    assert planned['checks']==['cookie_policy','cors_policy']
    assert client.post(accept,json=body).json()['id']==planned['id'] and client.app.state.store.count('tasks')==2
    assert client.post('/api/tasks/'+planned['id']+'/approve').status_code==200
    execution=finish(client,planned['id'])
    assert lab[1].requests==['/'] and len(prompts)==1
    assert all(row['status']=='completed' for row in execution['coverage'])
    assert execution['task']['goal_plan']['draft_id']==result['id']
    progress=client.get('/api/tasks/'+planned['id']+'/goal-progress').json()
    assert progress['goal_verified'] is False
    assert all(r['execution_status']=='completed' and r['completed']==r['expected']==1 and not r['goal_verified'] for r in progress['objectives'])


@pytest.mark.parametrize('damage',['tool','asset','cycle','fields','text','key'])
def test_invalid_provider_decomposition_is_explicit_catalog_fallback(client,lab,monkeypatch,damage):
    original=source(client,lab)
    def bad(plan,prompt):
        if damage=='tool':plan['objectives'][0]['checks']=['arbitrary-shell']
        elif damage=='asset':plan['objectives'][0]['asset_ids']=['other-tenant']
        elif damage=='cycle':plan['worker_dependencies']={prompt['assets'][0]['id']:[prompt['assets'][0]['id']]}
        elif damage=='fields':plan['commands']=['invented-command']
        elif damage=='text':plan['objectives'][0]['title']='x'*201
        else:plan['objectives'][0]['title']='owned-goal-key-only'
        return plan
    prompts=provider(monkeypatch,bad)
    _,_,result=draft(client,original)
    assert result['mode']=='rules_fallback' and result['llm_usage']['outcome']=='invalid_plan'
    assert len(result['decomposition']['objectives'])==6 and lab[1].requests==[] and len(prompts)==1
    assert 'arbitrary-shell' not in json.dumps(result['decomposition'])
    assert 'owned-goal-key-only' not in json.dumps(result['decomposition'])


@pytest.mark.parametrize('damage',['asset','policy','goal','draft'])
def test_changed_review_basis_or_draft_refuses_acceptance(client,lab,monkeypatch,damage):
    original=source(client,lab);provider(monkeypatch)
    path,_,result=draft(client,original);store=client.app.state.store
    if damage=='asset':store.patch('assets',original['asset_ids'][0],revision=2)
    elif damage=='policy':client.app.state.engine.policy=client.app.state.engine.policy.__class__(target_rps=1)
    elif damage=='goal':store.patch('tasks',original['id'],goal='Changed human goal')
    else:
        plan=copy.deepcopy(result['decomposition']);plan['objectives'][0]['checks']=['security_headers']
        store.patch('goal_plans',result['id'],decomposition=plan)
    assert client.post(path+'/'+result['id']+'/accept',json={'fingerprint':result['fingerprint']}).status_code==409
    assert store.count('tasks')==1 and lab[1].requests==[]


def test_rules_mode_and_viewer_never_call_provider_and_missing_configuration_is_refused(client,lab,monkeypatch):
    original=source(client,lab)
    monkeypatch.delenv('AEGIS_LLM_API_KEY',raising=False);monkeypatch.delenv('AEGIS_LLM_MODEL',raising=False)
    path='/api/tasks/'+original['id']+'/goal-plans'
    data={'request_id':'d'*32,'goal':'세션 보안 확인','mode':'ai'}
    assert client.post(path,json=data).status_code==409
    result=client.post(path,json={**data,'mode':'rules'}).json()
    assert result['mode']=='rules' and result['llm_usage'] is None
    viewer=add(client,'viewer')
    with login(client.app,viewer['username']) as read:
        assert read.get(path+'/'+result['id']).status_code==200
        assert read.post(path,json={**data,'mode':'rules'}).status_code==403
        assert read.post(path+'/'+result['id']+'/accept',json={'fingerprint':result['fingerprint']}).status_code==403
    assert lab[1].requests==[] and client.app.state.store.count('llm_calls')==0


def test_goal_plan_execution_tampering_is_refused_before_requests(client,lab,monkeypatch):
    original=source(client,lab);provider(monkeypatch)
    path,_,result=draft(client,original)
    plan=client.post(path+'/'+result['id']+'/accept',json={'fingerprint':result['fingerprint']}).json()
    client.app.state.store.patch('tasks',plan['id'],checks=['security_headers'])
    assert client.post('/api/tasks/'+plan['id']+'/approve').status_code==409 and lab[1].requests==[]


def test_provider_result_save_failure_recovery_prevents_repeated_billable_call(client,lab,monkeypatch):
    original=source(client,lab);prompts=provider(monkeypatch)
    store=client.app.state.store;put=store.put_many
    def refuse(records,**kwargs):
        if any(kind=='goal_plans' and record['state']=='ready' for kind,record in records):raise RuntimeError('owned result save failure')
        return put(records,**kwargs)
    monkeypatch.setattr(store,'put_many',refuse)
    with pytest.raises(RuntimeError,match='owned result save failure'):draft(client,original)
    monkeypatch.setattr(store,'put_many',put);goal_planner.recover(store)
    _,_,result=draft(client,original)
    assert result['state']=='interrupted' and len(prompts)==1
    assert store.page('llm_calls')['items'][0]['state']=='uncommitted'


def test_goal_dependencies_execute_declared_worker_order_and_preserve_goal_on_replan(client,lab,monkeypatch):
    first=register(client,lab[0]);second=register(client,lab[0]+'other/')
    original=client.post('/api/tasks',json={'name':'Owned two-asset goal','asset_ids':[first['id'],second['id']],
        'checks':['security_headers'],'workers':2}).json()
    def dependency(plan,prompt):
        for row in plan['objectives']:row['checks']=['security_headers']
        plan['worker_dependencies']={second['id']:[first['id']]}
        return plan
    provider(monkeypatch,dependency)
    path,_,result=draft(client,original)
    planned=client.post(path+'/'+result['id']+'/accept',json={'fingerprint':result['fingerprint']}).json()
    replacement=client.post('/api/tasks/'+planned['id']+'/replan')
    assert replacement.status_code==200,replacement.text
    assert replacement.json()['goal_plan']==planned['goal_plan']
    planned=replacement.json()
    assert client.post('/api/tasks/'+planned['id']+'/approve').status_code==200
    finish(client,planned['id'])
    assert lab[1].requests==['/','/other/']
    progress=client.get('/api/tasks/'+planned['id']+'/goal-progress').json()
    assert all(row['completed']==row['expected']==2 for row in progress['objectives'])


def test_final_goal_accept_write_rechecks_source(client,lab,monkeypatch):
    original=source(client,lab);provider(monkeypatch)
    path,_,result=draft(client,original)
    store=client.app.state.store;capture=goal_planner.snapshot
    def changed(*args,**kwargs):
        value=capture(*args,**kwargs)
        if kwargs.get('connection') is not None:value['source']['goal']='owned concurrent changed goal'
        return value
    monkeypatch.setattr(goal_planner,'snapshot',changed)
    assert client.post(path+'/'+result['id']+'/accept',json={'fingerprint':result['fingerprint']}).status_code==409
    assert store.count('tasks')==1 and not store.get('goal_plans',result['id']).get('accepted_task_id')
    assert lab[1].requests==[]


def test_missing_goal_scope_is_not_zero_over_zero_completion(client,lab,monkeypatch):
    original=source(client,lab);provider(monkeypatch)
    path,_,result=draft(client,original)
    plan=client.post(path+'/'+result['id']+'/accept',json={'fingerprint':result['fingerprint']}).json()
    client.app.state.store.patch('tasks',plan['id'],scope_snapshot=[])
    assert client.get('/api/tasks/'+plan['id']+'/goal-progress').status_code==409
    assert client.post('/api/tasks/'+plan['id']+'/approve').status_code==409
    assert lab[1].requests==[]


def test_sparse_objective_pairs_execute_once_and_preserve_other_evidence(client,lab,monkeypatch):
    from aegis import engine
    first=register(client,lab[0]);second=register(client,lab[0]+'other/')
    # Existing evidence must survive a newer goal that doesn't select that pair.
    prior=task(client,first,['cors_policy'])
    assert client.post('/api/tasks/'+prior['id']+'/approve').status_code==200
    finish(client,prior['id']);lab[1].requests.clear()
    original=client.post('/api/tasks',json={'name':'Sparse objective scope','asset_ids':[first['id'],second['id']],
        'checks':['security_headers'],'workers':2}).json()
    def sparse(plan,prompt):
        plan['objectives'][0]['asset_ids']=[first['id']]
        plan['objectives'][1]['asset_ids']=[second['id']]
        duplicate=copy.deepcopy(plan['objectives'][0]);duplicate['id']='g3'
        plan['objectives'].append(duplicate)
        plan['worker_dependencies']={second['id']:[first['id']]}
        return plan
    provider(monkeypatch,sparse)
    executed=[];run=engine.run_check
    def recording(check,asset,*args):
        executed.append((asset['id'],check))
        return run(check,asset,*args)
    monkeypatch.setattr(engine,'run_check',recording)
    path,_,result=draft(client,original)
    assert result['execution']=='objective_pairs'
    response=client.post(path+'/'+result['id']+'/accept',json={'fingerprint':result['fingerprint']})
    assert response.status_code==200,response.text
    planned=response.json();id=planned['id']
    pending=client.get('/api/tasks/'+id).json()
    expected={(first['id'],'cookie_policy'),(second['id'],'cors_policy')}
    assert {(r['asset_id'],r['check']) for r in pending['coverage']}==expected
    assert lab[1].requests==[]
    assert client.post('/api/tasks/'+id+'/approve').status_code==200
    execution=finish(client,id)
    assert executed==[(first['id'],'cookie_policy'),(second['id'],'cors_policy')]
    assert lab[1].requests==['/','/other/']
    assert {(r['asset_id'],r['check']) for r in execution['coverage']}==expected
    assert all(r['status']=='completed' for r in execution['coverage'])
    rows=client.get('/api/tasks/'+id+'/goal-progress').json()['objectives']
    assert len(rows)==3 and all(r['completed']==r['expected']==1 for r in rows)
    overview=client.get('/api/overview').json()['coverage_summary']
    assert overview['completed']==3 and overview['counts']['not_recorded']==0
    report=client.get('/api/reports/export',params={'format':'json','task_id':id}).json()
    assert {(r['asset_id'],r['check']) for r in report['coverage']}==expected
    from aegis.worker_process import get_process
    child=get_process(client.app.state.store,id,second['id'])
    assert [r['check'] for r in child['coverage']]==['cors_policy']
    handoffs=[row for row in child['events']['items'] if row.get('detail',{}).get('dependency_inputs')]
    assert handoffs and handoffs[0]['detail']['dependency_inputs'][0]['checks_completed']==['cookie_policy']


def test_legacy_goal_draft_preserves_approved_union_matrix(client,lab,monkeypatch):
    first=register(client,lab[0]);second=register(client,lab[0]+'other/')
    original=client.post('/api/tasks',json={'name':'Legacy goal review','asset_ids':[first['id'],second['id']],
        'checks':['security_headers']}).json()
    def sparse(plan,prompt):
        plan['objectives'][0]['asset_ids']=[first['id']]
        plan['objectives'][1]['asset_ids']=[second['id']]
        return plan
    provider(monkeypatch,sparse);path,_,result=draft(client,original)
    del result['execution'];result['fingerprint']=goal_planner.fingerprint(result)
    client.app.state.store.put('goal_plans',result)
    accepted=client.post(path+'/'+result['id']+'/accept',json={'fingerprint':result['fingerprint']})
    assert accepted.status_code==200,accepted.text
    planned=accepted.json()
    assert 'execution' not in planned['goal_plan']
    assert len(client.get('/api/tasks/'+planned['id']).json()['coverage'])==4
    assert client.post('/api/tasks/'+planned['id']+'/approve').status_code==200
    assert len(finish(client,planned['id'])['coverage'])==4


def test_goal_execution_mode_tamper_is_refused(client,lab,monkeypatch):
    original=source(client,lab);provider(monkeypatch);path,_,result=draft(client,original)
    accepted=client.post(path+'/'+result['id']+'/accept',json={'fingerprint':result['fingerprint']}).json()
    plan=copy.deepcopy(accepted['goal_plan']);del plan['execution']
    client.app.state.store.patch('tasks',accepted['id'],goal_plan=plan)
    assert client.post('/api/tasks/'+accepted['id']+'/approve').status_code==409
    assert lab[1].requests==[]
