"""Owned remote observed responses: selected cells, provenance and atomic writes."""
import copy
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from aegis.mcp_executor import ExecutionRejected, Runner
from aegis.mcp_scope import OBSERVATION_CHECK, ScopeGrantError, issue_grant, sign_claim, verify_claim
from tests.test_mcp_execution import KEY, service
from tests.test_mcp_task_execution import workspace, register, plan, finished
from tests.test_postgres_transfer import postgres


@pytest.fixture
def observed_target():
    state = {'requests': [], 'failed': set(), 'delay': 0, 'hardened': False, 'redirect': None}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):pass
        def do_GET(self):
            state['requests'].append(self.path)
            if self.path != '/approved':time.sleep(state['delay'])
            raw = ('<html>' + ''.join(f'<a href="/approved/child-{i}">child</a>' for i in range(10)) + '</html>').encode()
            redirect = state['redirect'] if self.path != '/approved' else None
            self.send_response(302 if redirect else 503 if self.path in state['failed'] else 200)
            self.send_header('Content-Type', 'text/html');self.send_header('Content-Length', str(len(raw)))
            if redirect:self.send_header('Location', redirect)
            if state['hardened']:
                for key,value in [('Content-Security-Policy',"default-src 'self'"),('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),('Referrer-Policy','no-referrer')]:self.send_header(key,value)
            self.end_headers()
            try:self.wfile.write(raw)
            except (BrokenPipeError,ConnectionResetError):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}/approved',state
    server.shutdown();server.server_close();thread.join(3);assert not thread.is_alive()


def selection(client, target, checks=('security_headers','cookie_policy'), *, batch=True, count=2):
    register(client, ['endpoint_inventory'] + ([OBSERVATION_CHECK] if batch else []))
    source=plan(client,target[0],['endpoint_inventory'])
    assert client.post('/api/tasks/'+source['id']+'/approve').status_code==200
    assert finished(client,source['id'])['status']=='completed'
    path='/api/tasks/'+source['id']+'/observation-plan'
    review=client.get(path);assert review.status_code==200,review.text
    context=review.json()['context'];assert len(context['items'])==10
    body={'fingerprint':context['fingerprint'],'observation_ids':[r['id'] for r in context['items'][:count]],
          'checks':list(checks),'request_id':'a'*32}
    return source,path,body


def create(client,path,body):
    response=client.post(path,json=body);assert response.status_code==200,response.text
    return response.json()


def run(client,task):
    response=client.post('/api/tasks/'+task['id']+'/approve');assert response.status_code==200,response.text
    return finished(client,task['id'])


def test_ten_urls_four_checks_one_remote_batch_reuses_responses_and_preserves_source(workspace,observed_target):
    client=workspace;url,state=observed_target
    source,path,body=selection(client,observed_target,('security_headers','transport_security','cookie_policy','cors_policy'),count=10)
    before=list(state['requests']);task=create(client,path,body)
    assert task['remote_execution']['mode']=='observation-response' and task['remote_connection_id']=='owned-server'
    assert [row['name'] for row in task['remote_execution']['tools']]==['validate_observation_responses']
    assert state['requests']==before and task['status']=='pending'
    assert client.post(path,json=body).json()['id']==task['id']
    result=run(client,task);assert result['status']=='completed',result
    requests=state['requests'][len(before):]
    assert len(requests)==10 and set(requests)=={f'/approved/child-{i}' for i in range(10)}
    detail=client.get('/api/tasks/'+task['id']).json()
    assert len(detail['coverage'])==4 and all(row['status']=='completed' and len(row['targets'])==10 for row in detail['coverage'])
    store=client.app.state.store
    receipts=[r for r in store.all('mcp_execution_receipts') if r['task_id']==task['id']]
    assert len(receipts)==1 and len(receipts[0]['coverage_ids'])==4 and len(receipts[0]['traffic_ids'])==10
    findings=[r for r in store.all('findings') if task['id'] in r['task_ids']]
    assert findings and all(r['code'].startswith('observed-') and r['observation_source_task_id']==source['id'] for r in findings)
    assert {r['observation_id'] for r in findings}==set(body['observation_ids'])
    assert client.get('/api/overview').json()['coverage_summary']['completed']==1
    assert client.get('/api/tasks/'+task['id']+'/next-plan').json()['reason']=='no_remaining_observation_checks'
    assert store.audit_integrity()['valid']
    raw=json.dumps(store.all('tasks')+store.all('mcp_execution_attempts')+receipts+store.events())
    assert KEY.decode() not in raw and '"grant":' not in raw


def test_unregistered_batch_refuses_creation_and_disabled_batch_refuses_approval(workspace,observed_target):
    client=workspace;_,path,body=selection(client,observed_target,batch=False)
    before=list(observed_target[1]['requests'])
    assert client.post(path,json=body).status_code==409
    row=register(client,[OBSERVATION_CHECK])[0]
    task=create(client,path,body)
    assert client.post('/api/integrations/mcp/tools/'+row['id']+'/disable',json={'revision':row['revision']}).status_code==200
    assert client.post('/api/tasks/'+task['id']+'/approve').status_code==409
    assert observed_target[1]['requests']==before


@pytest.mark.parametrize('todo_boundary',['settled','after_review'])
def test_partial_batch_keeps_proof_and_only_failed_cells_are_repeated_after_new_approval(workspace,observed_target,todo_boundary):
    from tests.test_event_planner import drain,wait_review
    client=workspace;source,path,body=selection(client,observed_target)
    task=create(client,path,body);target=task['observation_execution']['targets'][0]
    planner=client.app.state.event_planner
    if todo_boundary=='after_review':
        planner.close();drain(planner)
    from urllib.parse import urlsplit
    observed_target[1]['failed'].add(urlsplit(target['url']).path)
    result=run(client,task);assert result['status']=='failed'
    store=client.app.state.store
    rows=client.get('/api/tasks/'+task['id']).json()['coverage']
    assert all({r['status'] for r in row['targets']}=={'completed','failed'} for row in rows)
    assert store.count('evidence')>0 and store.audit_integrity()['valid']
    if todo_boundary=='settled':
        wait_review(store,task['id'],lambda review:review.get('automatic_todo',{}).get('status') in {'created','existing'})
    proposal=client.get('/api/tasks/'+task['id']+'/next-plan').json()
    cells=proposal['observation_cells']['cells']
    assert len(cells)==2 and {r['observation_id'] for r in cells}=={target['id']}
    if todo_boundary=='after_review':
        assert proposal['shared_todo_context']['items']==[]
        before=list(observed_target[1]['requests']);tasks=store.count('tasks')
        source_before=store.get('tasks',task['id'])
        drain(planner)
        fresh=client.get('/api/tasks/'+task['id']+'/next-plan').json()
        assert {key for key in proposal if proposal[key]!=fresh[key]}=={'fingerprint','shared_todo_context'}
        assert len(fresh['shared_todo_context']['items'])==1
        assert store.get('tasks',task['id'])==source_before
        assert client.post('/api/tasks/'+task['id']+'/next-plan',json={'fingerprint':proposal['fingerprint']}).status_code==409
        assert store.count('tasks')==tasks and observed_target[1]['requests']==before
        proposal=fresh
    response=client.post('/api/tasks/'+task['id']+'/next-plan',json={'fingerprint':proposal['fingerprint']})
    assert response.status_code==200,response.text
    follow=response.json();assert follow['remote_execution']['mode']=='observation-response'
    before=list(observed_target[1]['requests']);observed_target[1]['failed'].clear()
    assert run(client,follow)['status']=='completed'
    assert observed_target[1]['requests'][len(before):]==[urlsplit(target['url']).path]
    assert client.get('/api/tasks/'+follow['id']+'/next-plan').json()['reason']=='no_remaining_observation_checks'


def test_observed_finding_retest_preserves_remote_location_url_and_human_state(workspace,observed_target):
    client=workspace;_,path,body=selection(client,observed_target,('security_headers',),count=1)
    task=create(client,path,body);run(client,task);store=client.app.state.store
    finding=next(r for r in store.all('findings') if task['id'] in r['task_ids'])
    old_proof=list(finding['evidence_ids']);response=client.post('/api/findings/'+finding['id']+'/retest')
    assert response.status_code==200,response.text
    retry=response.json();assert retry['remote_connection_id']=='owned-server'
    before=list(observed_target[1]['requests']);observed_target[1]['hardened']=True
    assert run(client,retry)['status']=='completed'
    assert len(observed_target[1]['requests'])==len(before)+1
    detail=client.get('/api/findings/'+finding['id']).json()
    assert detail['finding']['status']=='resolved'
    assert all(store.get('evidence',id) for id in old_proof)


@pytest.mark.parametrize('change',['url','cells','source','context','live_revision'])
def test_tampered_pending_selection_rejected_without_network(workspace,observed_target,change):
    client=workspace;_,path,body=selection(client,observed_target)
    task=create(client,path,body);store=client.app.state.store;damaged=copy.deepcopy(task)
    if change=='url':damaged['observation_execution']['targets'][0]['url']=observed_target[0]+'/unselected'
    elif change=='cells':damaged['checks']=['api_authorization']
    elif change=='source':damaged['observation_execution']['source_task_id']='unrelated-source'
    elif change=='context':damaged['worker_observation_context']['fingerprint']='f'*64
    else:store.patch('assets',task['asset_ids'][0],revision=2)
    if change!='live_revision':store.put('tasks',damaged)
    before=list(observed_target[1]['requests'])
    assert client.post('/api/tasks/'+task['id']+'/approve').status_code==409
    assert observed_target[1]['requests']==before


def test_source_stop_revokes_active_observed_batch_and_prevents_more_urls(workspace,observed_target,service):
    client=workspace;_,path,body=selection(client,observed_target,count=10)
    task=create(client,path,body);before=len(observed_target[1]['requests']);observed_target[1]['delay']=2
    assert client.post('/api/tasks/'+task['id']+'/approve').status_code==200
    end=time.monotonic()+8
    while len(observed_target[1]['requests'])==before and time.monotonic()<end:time.sleep(.02)
    assert len(observed_target[1]['requests'])==before+1
    assert client.post('/api/tasks/'+task['id']+'/stop').status_code==200
    assert finished(client,task['id'])['status']=='stopped'
    store=client.app.state.store
    attempt=next(r for r in store.all('mcp_execution_attempts') if r['task_id']==task['id'])
    assert attempt['check']==OBSERVATION_CHECK and attempt['cancellation']['state']=='acknowledged'
    assert not service[0].gate.locked() and len(observed_target[1]['requests'])==before+1
    assert not any(r['task_id']==task['id'] for r in store.all('mcp_execution_receipts'))
    assert all(r['status']=='cancelled' for r in client.get('/api/tasks/'+task['id']).json()['coverage'])


def test_redirect_outside_approved_scope_is_not_followed(workspace,observed_target):
    client=workspace;_,path,body=selection(client,observed_target,count=1)
    task=create(client,path,body);before=len(observed_target[1]['requests']);observed_target[1]['redirect']='/outside'
    assert run(client,task)['status']=='failed'
    assert '/outside' not in observed_target[1]['requests']
    assert len(observed_target[1]['requests'])<=before+2


@pytest.mark.parametrize('fault',['id','url','check','missing','status','extra','traffic','secret'])
def test_invalid_batch_response_cannot_partially_admit_any_evidence(workspace,observed_target,monkeypatch,fault):
    from aegis import mcp_task_execution
    client=workspace;_,path,body=selection(client,observed_target)
    task=create(client,path,body);store=client.app.state.store
    before={kind:store.count(kind) for kind in ('evidence','findings','traffic','mcp_execution_receipts')}
    original=mcp_task_execution.invoke
    def damaged(*args,**kwargs):
        response=original(*args,**kwargs);output=response['structuredContent'];row=output['result'][0]
        if fault=='id':row['observation_id']='f'*64
        elif fault=='url':row['url']=observed_target[0]+'/unselected'
        elif fault=='check':row['check']='api_authorization'
        elif fault=='missing':output['result'].pop()
        elif fault=='status':row['status']=True
        elif fault=='extra':row['unreviewed']='value'
        elif fault=='traffic':
            for entry in output['traffic']:entry['url']=observed_target[0]
        else:row['findings'][0]['evidence']['reflection']=KEY.decode()
        return response
    monkeypatch.setattr(mcp_task_execution,'invoke',damaged)
    assert run(client,task)['status']=='failed'
    assert {kind:store.count(kind) for kind in before}==before
    assert store.audit_integrity()['valid']


def test_admission_audit_failure_rolls_back_every_observed_cell(workspace,observed_target,monkeypatch):
    client=workspace;_,path,body=selection(client,observed_target)
    task=create(client,path,body);store=client.app.state.store;original=store.event
    before={kind:store.count(kind) for kind in ('evidence','findings','finding_history','traffic','mcp_execution_receipts')}
    def reject(task_id,message,*args,**kwargs):
        if message=='승인된 원격 검증 결과를 원자적으로 기록했습니다.':raise RuntimeError('owned audit write failure')
        return original(task_id,message,*args,**kwargs)
    monkeypatch.setattr(store,'event',reject)
    assert run(client,task)['status']=='failed'
    assert {kind:store.count(kind) for kind in before}==before
    attempt=next(r for r in store.all('mcp_execution_attempts') if r['task_id']==task['id'])
    assert attempt['state']=='unconfirmed' and attempt['cancellation']['state']=='acknowledged'
    assert store.audit_integrity()['valid']


@pytest.mark.parametrize('fault',['outside','duplicate_url','empty_cells','api_check','mode','query'])
def test_signed_but_invalid_batch_scope_is_rejected_before_target_get(workspace,observed_target,tmp_path,fault):
    from aegis.observation_execution import approval_contract
    client=workspace;_,path,body=selection(client,observed_target)
    task=create(client,path,body)
    task.update(status='running',approved_at=time.time(),observation_execution_contract=approval_contract(task))
    token=issue_grant(task,task['asset_ids'][0],OBSERVATION_CHECK,'owned-server',KEY,allow_private=True)
    claim=verify_claim(token,KEY,'owned-server');value=claim.model_dump()
    if fault=='outside':value['observation']['targets'][0]['url']=observed_target[0].replace('/approved','/outside')
    elif fault=='duplicate_url':value['observation']['targets'][1]['url']=value['observation']['targets'][0]['url']
    elif fault=='empty_cells':value['observation']['cells']=[]
    elif fault=='api_check':value['observation']['cells'][0]['check']='api_authorization'
    elif fault=='mode':value['check_id']='security_headers'
    else:value['observation']['targets'][0]['url']+='?private=1'
    # Trusted signing primitive intentionally permits constructing malformed test
    # values; the server must revalidate their entire shape before consuming it.
    from types import SimpleNamespace
    damaged=sign_claim(SimpleNamespace(model_dump=lambda: value),KEY)
    runner=Runner('owned-server',KEY,tmp_path/'isolated-ledger.db',allow_private=True)
    before=list(observed_target[1]['requests'])
    with pytest.raises(ExecutionRejected):runner.execute('validate_observation_responses',{'grant':damaged})
    assert observed_target[1]['requests']==before
    assert not runner.gate.locked()


def test_batch_server_replay_is_refused_and_identical_local_receipt_is_idempotent(workspace,observed_target,service,monkeypatch):
    from aegis import mcp_task_execution
    from aegis.mcp_result_store import admit
    from tests.test_mcp_execution import call
    client=workspace;_,path,body=selection(client,observed_target)
    task=create(client,path,body);captured={}
    original_issue,original_invoke=mcp_task_execution.issue_grant,mcp_task_execution.invoke
    def issuing(task,*args,**kwargs):
        captured['task']=copy.deepcopy(task)
        captured['token']=original_issue(task,*args,**kwargs)
        return captured['token']
    def invoking(*args,**kwargs):
        captured['response']=original_invoke(*args,**kwargs)
        return captured['response']
    monkeypatch.setattr(mcp_task_execution,'issue_grant',issuing);monkeypatch.setattr(mcp_task_execution,'invoke',invoking)
    assert run(client,task)['status']=='completed'
    store=client.app.state.store
    receipt=next(r for r in store.all('mcp_execution_receipts') if r['task_id']==task['id'])
    counts={kind:store.count(kind) for kind in ('findings','evidence','coverage','traffic','mcp_execution_receipts')}
    events=store.events()
    assert admit(store,captured['task'],task['asset_ids'][0],OBSERVATION_CHECK,captured['token'],KEY,
        'owned-server',captured['response'],allow_private=True,attempt_id=receipt['attempt_id'])==receipt
    assert counts=={kind:store.count(kind) for kind in counts} and events==store.events()
    sdk=service[1];sdk.initialize();sdk.list_tools();before=list(observed_target[1]['requests'])
    assert call(sdk,captured['token'],OBSERVATION_CHECK)['isError'] is True
    assert observed_target[1]['requests']==before


def test_shared_batch_budget_exhaustion_reports_unexecuted_url_without_more_gets(workspace,observed_target):
    from dataclasses import replace
    client=workspace
    client.app.state.engine.policy=replace(client.app.state.engine.policy,request_budget=1)
    _,path,body=selection(client,observed_target)
    task=create(client,path,body);before=len(observed_target[1]['requests'])
    assert run(client,task)['status']=='failed'
    assert len(observed_target[1]['requests'])==before+1
    coverage=client.get('/api/tasks/'+task['id']).json()['coverage']
    assert all({row['status'] for row in cell['targets']}=={'completed','failed'} for cell in coverage)


def test_reviewed_runtime_check_order_is_bound_into_batch_authority(workspace,observed_target,monkeypatch):
    from aegis import mcp_task_execution
    client=workspace;_,path,body=selection(client,observed_target)
    task=create(client,path,body);captured=[]
    original=mcp_task_execution.issue_grant
    def issue(*args,**kwargs):
        token=original(*args,**kwargs);captured.append(verify_claim(token,KEY,'owned-server'));return token
    monkeypatch.setattr(mcp_task_execution,'issue_grant',issue)
    monkeypatch.setattr(client.app.state.engine,'plan',lambda task,control:list(reversed(task['checks'])))
    assert run(client,task)['status']=='completed'
    assert list(dict.fromkeys(cell.check for cell in captured[0].observation.cells))==list(reversed(body['checks']))


def test_restarted_source_marks_one_batch_unknown_without_replaying_any_url(workspace,observed_target):
    from aegis.engine import Engine
    from aegis.remote_mcp import _digest
    from aegis.observation_execution import approval_contract
    client=workspace;_,path,body=selection(client,observed_target)
    task=create(client,path,body);store=client.app.state.store
    store.patch('tasks',task['id'],status='running',approved_at=time.time(),observation_execution_contract=approval_contract(task))
    attempt_id=_digest([task['id'],task['asset_ids'][0],OBSERVATION_CHECK,'owned-server'])
    store.put('mcp_execution_attempts',{'id':attempt_id,'task_id':task['id'],'state':'dispatching'})
    before=list(observed_target[1]['requests'])
    # Match the application's shutdown order before replacing its runtime owner.
    # An admitted background read must keep fencing takeover until it completes.
    client.app.state.notification_deliveries.close()
    client.app.state.event_planner.close()
    assert not client.app.state.event_planner.thread.is_alive()
    client.app.state.engine.shutdown()
    if getattr(store,'backend',None)=='postgres':
        from aegis.postgres_store import PostgresStore
        recovered=PostgresStore(store._dsn,store.schema)
    else:
        from aegis.store import Store
        recovered=Store(store.path)
    engine=Engine(recovered,allow_private=True)
    try:
        assert recovered.get('tasks',task['id'])['status']=='interrupted'
        assert recovered.get('mcp_execution_attempts',attempt_id)['state']=='unconfirmed'
        assert recovered.get('mcp_execution_attempts',attempt_id)['termination_reason']=='source_restart'
        assert observed_target[1]['requests']==before and recovered.audit_integrity()['valid']
    finally:engine.shutdown()
