"""Owned cancellation recovery: durable intent, exact authority, no RPC replay."""
import copy
import hashlib
import json
import threading
import time

import pytest

from aegis import mcp_revocations as revocations
from aegis.engine import Engine
from aegis.mcp_executor import ExecutionRejected
from aegis.mcp_registry import Registry
from aegis.mcp_scope import issue_grant
from aegis.mcp_task_execution import Executors, recover_attempts
from aegis.remote_mcp import _digest
from tests.test_mcp_execution import KEY, BEARER, service, target
from tests.test_mcp_task_execution import workspace, register, plan, finished
from tests.test_postgres_transfer import postgres


def pending(client, url):
    client.app.state.engine.remote.revocations.close()
    register(client, ['security_headers'])
    task = plan(client, url, ['security_headers'])
    task.update(status='running', approved_at=time.time(), plan=task['checks'])
    store = client.app.state.store
    store.put('tasks', task)
    asset = task['asset_ids'][0]
    token = issue_grant(task, asset, 'security_headers', 'owned-server', KEY, allow_private=True)
    attempt = {'id': _digest([task['id'], asset, 'security_headers', 'owned-server']),
               'task_id': task['id'], 'asset_id': asset, 'check': 'security_headers',
               'server_id': 'owned-server', 'state': 'dispatching', 'created_at': time.time(),
               'grant_sha256': hashlib.sha256(token.encode()).hexdigest(),
               'contract_sha256': _digest(task['remote_execution']), 'request_budget': 24}
    row = revocations.prepare(attempt, token, KEY, task['remote_execution'])
    store.put_many([('mcp_execution_attempts', attempt), (revocations.KIND, row)])
    return task, attempt, row, token


def activate(client, task, attempt):
    recover_attempts(client.app.state.store, task)
    return client.app.state.store.get(revocations.KIND, attempt['id'])


def worker(client):
    return revocations.Recovery(client.app.state.engine.remote)


def stop_application_runtime(client):
    # Match lifespan shutdown before replacing the application's native owner.
    # An admitted background transaction correctly fences a new engine until joined.
    state=client.app.state
    state.model_connection.close()
    state.model_catalog.close()
    state.notification_deliveries.close()
    state.event_planner.close()
    assert not state.event_planner.thread.is_alive()
    state.engine.shutdown()


def test_dormant_intent_never_cancels_a_live_call_and_admitted_result_removes_it(workspace, target):
    client = workspace
    register(client, ['security_headers'])
    task = plan(client, target[0], ['security_headers'])
    assert client.post('/api/tasks/'+task['id']+'/approve').status_code == 200
    assert finished(client, task['id'])['status'] == 'completed'
    assert client.app.state.store.count(revocations.KIND) == 0
    assert len(target[1]['requests']) == 1
    task, attempt, row, token = pending(client, target[0]+'/dormant')
    assert revocations.candidates(client.app.state.store, time.time()+1) == []
    raw = json.dumps(row)
    assert token not in raw and KEY.decode() not in raw and BEARER not in raw
    assert row['ready'] is False


def test_restarted_engine_activates_exact_cancel_and_acknowledges_without_target_get(workspace, target, service):
    client = workspace; task, attempt, row, token = pending(client, target[0])
    source = client.app.state.store
    stop_application_runtime(client)
    if getattr(source, 'backend', None) == 'postgres':
        from aegis.postgres_store import PostgresStore
        store = PostgresStore(source._dsn, source.schema)
    else:
        from aegis.store import Store
        store = Store(source.path)
    engine = Engine(store, allow_private=True)
    registry = Registry.from_env(store, threading.Event())
    engine.remote = Executors.from_env(registry)
    recovery = engine.remote.revocations
    try:
        assert store.get('tasks', task['id'])['status'] == 'interrupted'
        assert store.get(revocations.KIND, row['id'])['ready'] is True
        recovery.start()
        deadline = time.monotonic()+8
        while store.count(revocations.KIND) and time.monotonic()<deadline:time.sleep(.03)
        result = store.get('mcp_execution_attempts', attempt['id'])
        assert result['state'] == 'unconfirmed'
        assert result['cancellation']['state'] == 'acknowledged' and result['cancellation']['recovered'] is True
        assert store.count(revocations.KIND) == 0 and not target[1]['requests']
        with pytest.raises(ExecutionRejected):service[0].execute('validate_security_headers', {'grant': token})
        assert not target[1]['requests'] and store.audit_integrity()['valid']
    finally:engine.shutdown()


@pytest.mark.parametrize('fault', ['key', 'endpoint', 'bearer', 'claim', 'hash', 'attempt', 'expired'])
def test_changed_or_expired_authority_does_not_send_cancel(workspace, target, monkeypatch, fault):
    client=workspace;task,attempt,row,token=pending(client,target[0]);store=client.app.state.store
    row=activate(client,task,attempt); recovery=worker(client); calls=[]
    monkeypatch.setattr(revocations,'cancel',lambda *args,**kwargs:calls.append(args))
    if fault=='key':monkeypatch.setenv('AEGIS_MCP_SCOPE_OWNED','changed-signing-key-0123456789abcdefgh')
    elif fault=='endpoint':
        endpoint=recovery.executors.registry.connections['owned-server']
        recovery.executors.registry.connections['owned-server']=endpoint.model_copy(update={'url':endpoint.url+'/changed'})
    elif fault=='bearer':monkeypatch.setenv('FIXTURE_SCOPE_BEARER','changed-transport-token-0123456789abcdefgh')
    elif fault=='claim':row['claim']['asset']['url']=target[0]+'/unapproved';store.put(revocations.KIND,row)
    elif fault=='hash':row['grant_sha256']='f'*64;store.put(revocations.KIND,row)
    elif fault=='attempt':store.patch('mcp_execution_attempts',attempt['id'],asset_id='changed-asset')
    else:monkeypatch.setattr(revocations,'now',lambda:row['claim']['expires_at']+1)
    recovery.process(row)
    result=store.get('mcp_execution_attempts',attempt['id'])
    assert not calls and not target[1]['requests'] and store.count(revocations.KIND)==0
    assert result['cancellation']['state']=='unconfirmed' and 'recovery_reason' in result['cancellation']
    assert store.audit_integrity()['valid']


def test_transient_confirmation_loss_retries_identical_token_without_execution(workspace, target, monkeypatch, service):
    client=workspace;task,attempt,row,token=pending(client,target[0]);store=client.app.state.store
    row=activate(client,task,attempt);recovery=worker(client);original=revocations.cancel;calls=[]
    def lost(endpoint,grant,**kwargs):
        calls.append(grant)
        result=original(endpoint,grant,**kwargs)
        if len(calls)==1:raise ValueError('owned acknowledgement loss')
        return result
    monkeypatch.setattr(revocations,'cancel',lost)
    recovery.process(row)
    pending_row=store.get(revocations.KIND,row['id'])
    assert pending_row['tries']==1 and pending_row['due_key']>row['due_key']
    assert store.get('mcp_execution_attempts',attempt['id'])['cancellation']['state']=='unconfirmed'
    recovery.process(pending_row)
    assert calls==[token,token] and store.count(revocations.KIND)==0
    assert store.get('mcp_execution_attempts',attempt['id'])['cancellation']['state']=='acknowledged'
    assert not target[1]['requests'] and store.audit_integrity()['valid']


def test_false_acknowledgement_and_retry_limit_remain_unconfirmed(workspace, target, monkeypatch):
    client=workspace;task,attempt,row,token=pending(client,target[0]);store=client.app.state.store
    row=activate(client,task,attempt);recovery=worker(client);calls=[]
    def invalid(*args,**kwargs):calls.append(1);return {'cancelled':True}
    monkeypatch.setattr(revocations,'cancel',invalid)
    for _ in range(8):
        row=store.get(revocations.KIND,attempt['id']);recovery.process(row)
    result=store.get('mcp_execution_attempts',attempt['id'])
    assert len(calls)==8 and result['cancellation']['state']=='unconfirmed'
    assert result['cancellation']['recovery_reason']=='retry_limit' and store.count(revocations.KIND)==0
    assert not target[1]['requests']


def test_confirmation_audit_failure_keeps_durable_intent_for_idempotent_retry(workspace, target, monkeypatch):
    client=workspace;task,attempt,row,token=pending(client,target[0]);store=client.app.state.store
    row=activate(client,task,attempt);recovery=worker(client);original=store.event
    def failing(*args,**kwargs):raise RuntimeError('owned audit failure')
    monkeypatch.setattr(store,'event',failing)
    with pytest.raises(RuntimeError):recovery.process(row)
    assert store.get(revocations.KIND,row['id'])==row
    assert 'cancellation' not in store.get('mcp_execution_attempts',row['id'])
    monkeypatch.setattr(store,'event',original);recovery.process(row)
    assert store.count(revocations.KIND)==0 and store.audit_integrity()['valid'] and not target[1]['requests']


def test_cleanup_queries_are_bounded_and_order_due_entries_not_store_all(workspace, target, monkeypatch):
    client=workspace;task,attempt,row,token=pending(client,target[0]);store=client.app.state.store
    activate(client,task,attempt);row=store.get(revocations.KIND,row['id'])
    rows=[{**row,'id':f'owned-{i:04d}','due_key':revocations.due_key(time.time()+i-50)} for i in range(100)]
    store.put_many([(revocations.KIND,r) for r in rows])
    monkeypatch.setattr(store,'all',lambda *args:pytest.fail('unbounded read'))
    result=revocations.candidates(store,time.time())
    assert len(result)==10 and [r['id'] for r in result]==[f'owned-{i:04d}' for i in range(10)]
    assert not target[1]['requests']


def test_stop_cancels_cleanup_child_without_claiming_remote_ack(workspace, target, monkeypatch):
    client=workspace;task,attempt,row,token=pending(client,target[0]);store=client.app.state.store
    row=activate(client,task,attempt);recovery=worker(client)
    def stopped(*args,**kwargs):recovery.stop.set();raise InterruptedError()
    monkeypatch.setattr(revocations,'cancel',stopped);recovery.process(row)
    assert store.get(revocations.KIND,row['id'])==row and not target[1]['requests']
    assert 'cancellation' not in store.get('mcp_execution_attempts',row['id'])


@pytest.mark.parametrize('backend', ['sqlite', 'postgres'])
def test_actual_source_sigkill_then_startup_revokes_running_remote_call_without_replay(tmp_path, request, service, target, backend):
    import os
    import socket
    import sqlite3
    import subprocess
    import sys
    from pathlib import Path
    from http.cookiejar import CookieJar
    from urllib.request import build_opener, HTTPCookieProcessor, ProxyHandler, Request
    from aegis.postgres_bootstrap import initialize
    from tests.test_postgres_transfer import schema
    root=Path(__file__).resolve().parents[1]
    environment={k:v for k,v in os.environ.items() if not k.startswith(('AEGIS_','PG')) and k not in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV')}
    environment.update(AEGIS_STORAGE_BACKEND=backend,AEGIS_LAB_MODE='1',AEGIS_REQUEST_TIMEOUT='30',AEGIS_TASK_TIMEOUT='120',AEGIS_REQUEST_RETRIES='0',
        AEGIS_MCP_CONNECTIONS=json.dumps([service[1].connection.model_dump()]),AEGIS_MCP_SCOPE_OWNED=KEY.decode(),
        AEGIS_MCP_EXECUTORS=json.dumps([{'connection_id':'owned-server','scope_key_env':'AEGIS_MCP_SCOPE_OWNED','allow_private':True}]))
    if backend=='postgres':
        cluster=request.getfixturevalue('postgres');name=schema();initialize(cluster['dsn'],name)
        environment.update(AEGIS_POSTGRES_DSN=cluster['dsn'],AEGIS_POSTGRES_SCHEMA=name)
        from aegis.postgres_store import PostgresStore
        store=PostgresStore(cluster['dsn'],name)
        def rows(kind):return store.all(kind)
    else:
        def rows(kind):
            with sqlite3.connect((tmp_path/'owned-source'/'aegis.db').resolve().as_uri()+'?mode=ro',uri=True) as db:
                return [json.loads(r[0]) for r in db.execute('SELECT data FROM records WHERE kind=?',(kind,))]
    processes=[];logs=[];owned_children=[]
    opener=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
    def call(path,body=None):
        data=json.dumps(body).encode() if body is not None else None
        req=Request(base+path,data=data,headers={'Content-Type':'application/json'} if body is not None else {})
        with opener.open(req,timeout=8) as response:return json.load(response)
    code='''import socket,sys
sys.path.insert(0,sys.argv[1])
from aegis.app import create_app
from aegis.__main__ import AegisServer
from contextlib import asynccontextmanager
from pathlib import Path
Path(sys.argv[2]).mkdir(parents=True,exist_ok=True)
app=create_app(sys.argv[2]);original=app.router.lifespan_context
@asynccontextmanager
async def lifespan(application):
 async with original(application):yield
 (Path(sys.argv[2])/'shutdown-complete').write_text('complete')
app.router.lifespan_context=lifespan
AegisServer(app,host='127.0.0.1',port=0,access_log=False,log_level='warning',timeout_graceful_shutdown=5).run(sockets=[socket.socket(fileno=int(sys.argv[3]))])
'''
    def start():
        nonlocal base
        listener=socket.socket();listener.bind(('127.0.0.1',0));base=f'http://127.0.0.1:{listener.getsockname()[1]}'
        log=(tmp_path/f'source-{len(processes)}.log').open('wb');logs.append(log)
        process=subprocess.Popen([sys.executable,'-I','-c',code,str(root),str(tmp_path/'owned-source'),str(listener.fileno())],env=environment,cwd=tmp_path,pass_fds=(listener.fileno(),),stdout=log,stderr=log)
        processes.append(process);listener.close();end=time.monotonic()+10
        while time.monotonic()<end:
            assert process.poll() is None,'owned source exited during startup'
            try:
                if call('/api/health')['status']=='ok':return process
            except OSError:pass
            time.sleep(.05)
        raise AssertionError('owned source did not become ready')
    base=''
    try:
        first=start();call('/api/auth/setup',{'password':'owned-crash-test-password'})
        review=call('/api/integrations/mcp/previews',{'connection_id':'owned-server'})
        call('/api/integrations/mcp/previews/'+review['id']+'/register',{'selected':['validate_security_headers'],'reviewed':True})
        asset=call('/api/assets',{'name':'Owned crash target','url':target[0],'authorized':True})
        task=call('/api/tasks',{'name':'Owned hard crash','asset_ids':[asset['id']],'checks':['security_headers'],'planner':'rules','remote_connection_id':'owned-server'})
        target[1]['delay']=8
        call('/api/tasks/'+task['id']+'/approve',{})
        end=time.monotonic()+10
        while not target[1]['requests'] and time.monotonic()<end:time.sleep(.02)
        assert len(target[1]['requests'])==1
        assert len(rows(revocations.KIND))==1 and rows(revocations.KIND)[0]['ready'] is False
        for line in subprocess.check_output(['ps','-axo','pid=,ppid=,command='],text=True).splitlines():
            parts=line.strip().split(None,2)
            if len(parts)==3 and int(parts[1])==first.pid and 'mcp_process' in parts[2]:owned_children.append(int(parts[0]))
        first.kill();assert first.wait(timeout=5)<0
        second=start();end=time.monotonic()+10
        while rows(revocations.KIND) and time.monotonic()<end:time.sleep(.03)
        attempts=rows('mcp_execution_attempts');assert len(attempts)==1
        assert attempts[0]['state']=='unconfirmed' and attempts[0]['termination_reason']=='source_restart'
        assert attempts[0]['cancellation']['state']=='acknowledged' and attempts[0]['cancellation']['recovered'] is True
        assert not rows(revocations.KIND) and not rows('mcp_execution_receipts') and not rows('findings') and not rows('evidence')
        assert call('/api/tasks/'+task['id'])['task']['status']=='interrupted'
        assert call('/api/audit/verify',{})['status']=='verified'
        assert not service[0].gate.locked() and len(target[1]['requests'])==1
        second.terminate();assert second.wait(timeout=10) in (0,-15)
        assert (tmp_path/'owned-source'/'shutdown-complete').read_text()=='complete'
        if backend=='postgres':store.acquire_runtime().close()
        else:
            from aegis.maintenance import WorkspaceLease
            WorkspaceLease(tmp_path/'owned-source').close()
        time.sleep(.2);assert len(target[1]['requests'])==1
    finally:
        for process in processes:
            if process.poll() is None:process.kill();process.wait(timeout=5)
        # Only cleanup children captured from the source process this test owned.
        for pid in owned_children:
            try:
                command=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True).strip()
                if 'aegis.mcp_process' in command and str(root) in command:os.kill(pid,9)
            except (OSError,subprocess.CalledProcessError):pass
        for log in logs:log.close()


def test_ack_for_changed_attempt_cannot_overwrite_its_confirmation(workspace,target,monkeypatch):
    client=workspace;task,attempt,row,token=pending(client,target[0]);store=client.app.state.store
    row=activate(client,task,attempt);recovery=worker(client);original=revocations.cancel
    def changed(*args,**kwargs):
        result=original(*args,**kwargs)
        store.patch('mcp_execution_attempts',attempt['id'],grant_sha256='f'*64)
        return result
    monkeypatch.setattr(revocations,'cancel',changed);recovery.process(row)
    result=store.get('mcp_execution_attempts',attempt['id'])
    assert result.get('cancellation',{}).get('state')!='acknowledged'
    assert store.get(revocations.KIND,row['id'])==row and not target[1]['requests']


@pytest.mark.parametrize('stage',['dispatch','admission'])
def test_audit_failure_never_loses_cleanup_intent_or_partially_commits_it(workspace,target,monkeypatch,stage):
    client=workspace;store=client.app.state.store
    client.app.state.engine.remote.revocations.close()
    register(client,['security_headers']);task=plan(client,target[0],['security_headers'])
    original_event=store.event
    rejected='승인된 원격 검증 전송을 기록했습니다.' if stage=='dispatch' else '승인된 원격 검증 결과를 원자적으로 기록했습니다.'
    def reject(task_id,message,*args,**kwargs):
        if message==rejected:raise RuntimeError('owned atomic audit failure')
        return original_event(task_id,message,*args,**kwargs)
    monkeypatch.setattr(store,'event',reject)
    if stage=='admission':
        from aegis import mcp_task_execution
        monkeypatch.setattr(mcp_task_execution,'cancel',lambda *args,**kwargs:(_ for _ in ()).throw(ValueError('owned cancel transport loss')))
    assert client.post('/api/tasks/'+task['id']+'/approve').status_code==200
    assert finished(client,task['id'])['status']=='failed'
    assert store.count('mcp_execution_receipts')==store.count('findings')==store.count('evidence')==0
    if stage=='dispatch':
        assert store.count('mcp_execution_attempts')==store.count(revocations.KIND)==0
        assert not target[1]['requests']
    else:
        assert store.count('mcp_execution_attempts')==store.count(revocations.KIND)==1
        assert store.all(revocations.KIND)[0]['ready'] is True and len(target[1]['requests'])==1
        monkeypatch.setattr(store,'event',original_event)
        worker(client).process(store.all(revocations.KIND)[0])
        assert store.count(revocations.KIND)==0
        assert store.all('mcp_execution_attempts')[0]['cancellation']['state']=='acknowledged'
        assert len(target[1]['requests'])==1
    assert store.audit_integrity()['valid']


@pytest.mark.parametrize('workspace',['postgres'],indirect=True)
def test_lost_native_source_ownership_prevents_outbound_cleanup(workspace,target,monkeypatch):
    from aegis.maintenance import WorkspaceBusy
    from aegis.postgres_store import PostgresStore
    client=workspace;task,attempt,row,token=pending(client,target[0]);store=client.app.state.store
    row=activate(client,task,attempt);recovery=worker(client);calls=[]
    monkeypatch.setattr(revocations,'cancel',lambda *args,**kwargs:calls.append(args))
    store.owner.close()
    with pytest.raises(WorkspaceBusy):recovery.process(row)
    readonly=PostgresStore(store._dsn,store.schema)
    assert readonly.get(revocations.KIND,row['id'])==row and not calls and not target[1]['requests']
    assert 'cancellation' not in readonly.get('mcp_execution_attempts',row['id'])


def test_startup_recovers_unsaved_cleanup_even_when_source_task_already_terminated(workspace,target):
    client=workspace;task,attempt,row,token=pending(client,target[0]);source=client.app.state.store
    source.patch('tasks',task['id'],status='failed',finished_at=time.time())
    stop_application_runtime(client)
    if getattr(source,'backend',None)=='postgres':
        from aegis.postgres_store import PostgresStore
        store=PostgresStore(source._dsn,source.schema)
    else:
        from aegis.store import Store
        store=Store(source.path)
    engine=Engine(store,allow_private=True)
    try:
        assert store.get(revocations.KIND,row['id'])['ready'] is True
        assert store.get('mcp_execution_attempts',attempt['id'])['state']=='unconfirmed'
        assert store.get('tasks',task['id'])['status']=='failed' and not target[1]['requests']
    finally:engine.shutdown()
