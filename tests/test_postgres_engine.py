"""Owned PostgreSQL engine execution and cross-connection finding decisions."""
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from aegis.engine import Engine
from aegis.runtime import ExecutionPolicy
from aegis.findings import record_observation,update_triage,apply_retest,TriageConflict
from aegis.auth import new_user
from aegis.coverage import planned_slots
from aegis.tool_contracts import contracts_for
from aegis.postgres_store import PostgresStore
from aegis.store import Store
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_store import stores,seed
from tests.test_validation import lab


def plan(id,asset,checks=None,**extra):
    checks=checks or ['security_headers']
    return {'id':id,'name':'Owned native task','status':'pending','asset_ids':[asset['id']],
            'scope_snapshot':[asset],'checks':checks,'tool_contracts':contracts_for(checks),
            'created_at':time.time(),'workers':1,'planner':'rules','goal':'Owned validation','done':0,'errors':0,**extra}


def wait_task(store,id):
    end=time.monotonic()+8
    while time.monotonic()<end:
        row=store.get('tasks',id)
        if row['status'] in ('completed','failed','stopped','interrupted'):return row
        time.sleep(.02)
    pytest.fail('Owned PostgreSQL task did not terminate')


def test_native_engine_runs_approved_scope_and_persists_findings(stores,lab):
    _,pg=stores;url,handler=lab
    asset={'id':'owned','name':'Owned lab','url':url,'type':'web','revision':1,'archived_at':None}
    task=plan('task',asset,checks=['security_headers','endpoint_inventory'])
    pg.put_many([('assets',asset),('tasks',task),*[('coverage',row) for row in planned_slots(task)]])
    engine=Engine(pg,allow_private=True,policy=ExecutionPolicy(target_rps=20,request_retries=0))
    try:
        assert not handler.requests
        engine.start(task['id']);result=wait_task(pg,task['id'])
        assert result['status']=='completed' and result['done']==1 and result['errors']==0
        assert pg.count('findings')>0 and pg.count('evidence')==pg.count('findings')
        assert pg.count('traffic')>0 and pg.count('observations')>0
        assert pg.page('coverage',filters={'task_id':task['id'],'status':'completed'})['total']==2
        metrics=engine.metrics();assert metrics['tasks']['completed']==1 and metrics['queue_watchdog']['errors']==0
        assert pg.audit_integrity()['valid']
        first=pg.page('findings')['items'][0]
        assert pg.page('evidence',filters={'finding_id':first['id']})['total']==1
        missing=next(row for row in pg.page('findings')['items'] if row['code']=='missing-nosniff')
        handler.hardened=True
        retest=plan('retest',asset,retest_of=missing['id'],retest_triage_revision=missing['triage_revision'])
        pg.put_many([('tasks',retest),*[('coverage',row) for row in planned_slots(retest)]])
        engine.start('retest');assert wait_task(pg,'retest')['status']=='completed'
        assert pg.get('findings',missing['id'])['status']=='resolved'
        assert pg.page('retests',filters={'finding_id':missing['id']})['items'][0]['conclusion']=='resolved'
        assert pg.audit_integrity()['valid']
    finally:engine.shutdown()


def test_native_engine_recovery_revision_refusal_queue_timeout_and_pending_stop(stores,lab):
    _,pg=stores;url,handler=lab
    asset={'id':'owned','name':'Owned lab','url':url,'type':'web','revision':1}
    interrupted=plan('interrupted',asset,status='running')
    stale=plan('stale',asset);pending=plan('pending',asset)
    pg.put_many([('assets',{**asset,'revision':2}),('tasks',interrupted),('tasks',stale),('tasks',pending),
                 *[('coverage',row) for row in planned_slots(interrupted)]])
    engine=Engine(pg,allow_private=True,policy=ExecutionPolicy(queue_timeout=1))
    try:
        assert pg.get('tasks','interrupted')['status']=='interrupted'
        assert pg.get('coverage','interrupted:owned:security_headers')['status']=='interrupted'
        with pytest.raises(ValueError,match='수정'):engine.start('stale')
        assert not handler.requests
        assert engine.stop('pending')['status']=='rejected' and not handler.requests
        expired=plan('expired',asset,status='queued',approved_at=time.time()-10)
        pg.put_many([('tasks',expired),*[('coverage',row) for row in planned_slots(expired)]])
        result=wait_task(pg,'expired')
        assert result['status']=='failed' and result['termination_reason']=='queue_timeout'
        assert engine.metrics()['timeouts']==1 and engine.metrics()['queue_watchdog']['errors']==0
        assert not handler.requests and pg.audit_integrity()['valid']
    finally:engine.shutdown()


def test_metrics_and_oldest_bounded_overdue_queries_match_sqlite(stores):
    seed(stores,[('tasks',{'id':str(i),'status':'queued' if i%2 else 'completed','approved_at':i,'termination_reason':'timeout' if i%7==0 else None}) for i in range(250)])
    sqlite,pg=stores
    assert pg.task_metrics()==sqlite.task_metrics()
    assert pg.overdue_task_ids(1000)==sqlite.overdue_task_ids(1000) and len(pg.overdue_task_ids(1000))==100
    assert pg.overdue_task_ids(5)==sqlite.overdue_task_ids(5)
    with pytest.raises(ValueError):pg.overdue_task_ids(1000,limit=101)


def finding_fixture(store):
    asset={'id':'owned','name':'Owned'};task={'id':'first','created_at':1,'approved_at':1}
    item={'check':'security_headers','code':'owned-code','title':'Owned missing header','severity':'low','evidence':{'header':'owned'}}
    finding,_,_=record_observation(store,task,asset,item)
    return asset,task,item,finding


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_cross_store_observations_keep_one_finding_and_all_proofs(stores,postgres,backend):
    sqlite,pg=stores;store=pg if backend=='postgres' else sqlite
    other=PostgresStore(postgres['dsn'],pg.schema) if backend=='postgres' else Store(sqlite.path)
    asset,task,item,finding=finding_fixture(store)
    def observe(i):return record_observation(store if i%2 else other,{**task,'id':'task-'+str(i)},asset,item)
    with ThreadPoolExecutor(max_workers=4) as executor:results=list(executor.map(observe,range(16)))
    assert store.count('findings')==1 and store.count('evidence')==17 and store.count('finding_history')==17
    updated=store.get('findings',finding['id'])
    assert len(set(updated['evidence_ids']))==17 and len(set(updated['task_ids']))==17
    assert {row[0]['id'] for row in results}=={finding['id']}


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_cross_store_decisions_one_revision_winner_and_retest_conflict(stores,postgres,backend):
    sqlite,pg=stores;store=pg if backend=='postgres' else sqlite
    other=PostgresStore(postgres['dsn'],pg.schema) if backend=='postgres' else Store(sqlite.path)
    _,task,_,finding=finding_fixture(store);actor=new_user('owned','Owned','admin','owned-triage-password')
    store.add_user(actor)
    def decide(index):
        try:return update_triage(store if index==0 else other,finding['id'],{'expected_revision':1,'status':'accepted','acceptance_reason':'reason-'+str(index),'assignee_id':actor['id']},actor)['triage_revision']
        except TriageConflict:return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as executor:results=list(executor.map(decide,range(2)))
    assert results.count(2)==1 and results.count('conflict')==1
    current=store.get('findings',finding['id']);assert current['assignee_name']=='Owned'
    retest=apply_retest(other,{**task,'id':'retest','retest_of':finding['id'],'retest_triage_revision':1},'resolved')
    assert retest['triage_effect']=='conflict' and store.get('findings',finding['id'])==current


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_finding_batch_failure_rolls_back_observation_triage_and_retest(stores,backend,monkeypatch):
    sqlite,pg=stores;store=pg if backend=='postgres' else sqlite
    asset,task,item,finding=finding_fixture(store)
    original=store.put_many
    def fail(records,**options):
        original(records,**options)
        raise RuntimeError('Owned failure after finding batch writes')
    monkeypatch.setattr(store,'put_many',fail)
    with pytest.raises(RuntimeError):record_observation(store,{**task,'id':'second'},asset,item)
    assert store.get('findings',finding['id'])==finding and store.count('evidence')==1
    with pytest.raises(RuntimeError):update_triage(store,finding['id'],{'expected_revision':1,'status':'accepted','acceptance_reason':'Owned'}, {'id':'a','name':'a','username':'a','role':'admin'})
    assert store.get('findings',finding['id'])==finding and store.count('finding_history')==1
    with pytest.raises(RuntimeError):apply_retest(store,{**task,'retest_of':finding['id'],'retest_triage_revision':1},'resolved')
    assert store.get('findings',finding['id'])==finding and store.count('retests')==0 and store.count('finding_history')==1


def test_native_running_stop_cancels_owned_request_and_coverage(stores):
    import threading
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    _,pg=stores;entered=threading.Event();release=threading.Event();requests=[]
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path);entered.set();release.wait(2)
            try:
                self.send_response(200);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'OK')
            except (BrokenPipeError,ConnectionResetError):pass
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    asset={'id':'owned','name':'Owned held request','url':f'http://127.0.0.1:{server.server_port}/','type':'web','revision':1}
    task=plan('held',asset);pg.put_many([('assets',asset),('tasks',task),*[('coverage',row) for row in planned_slots(task)]])
    engine=Engine(pg,allow_private=True,policy=ExecutionPolicy(request_retries=0))
    try:
        engine.start('held');assert entered.wait(2)
        assert engine.stop('held')['status']=='stopping';release.set()
        result=wait_task(pg,'held');assert result['status']=='stopped' and result['termination_reason']=='operator_stop'
        assert pg.get('coverage','held:owned:security_headers')['status']=='cancelled' and pg.count('findings')==0
        assert requests==['/'] and pg.audit_integrity()['valid']
    finally:
        release.set();engine.shutdown();server.shutdown();server.server_close();thread.join(timeout=2)
