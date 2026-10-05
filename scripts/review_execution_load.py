"""Owned loopback execution/read churn and process-loss recovery rehearsal.

POSIX Python 3.11+, httpx; --postgres needs psycopg and initdb/pg_ctl.
Creates only disposable services and synthetic data. No production SLO claim.
"""
import argparse
from collections import Counter,deque
from contextlib import contextmanager
import hashlib
from http.server import ThreadingHTTPServer
import json
import os
import platform
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from examples.lab_server import LabHandler
from scripts.review_resource_load import bounded_int,process_sample

SERVER='''
import socket,sys
from pathlib import Path
from contextlib import asynccontextmanager
from aegis.app import create_app
from aegis.__main__ import AegisServer
app=create_app(sys.argv[1],allow_private=True)
original=app.router.lifespan_context
@asynccontextmanager
async def lifespan(application):
 async with original(application):yield
 Path(sys.argv[3]).write_text('complete')
app.router.lifespan_context=lifespan
AegisServer(app,host='127.0.0.1',port=0,access_log=False,log_level='warning',timeout_graceful_shutdown=5).run(sockets=[socket.socket(fileno=int(sys.argv[2]))])
'''


@contextmanager
def owned_postgres(root,enabled,environment):
    if not enabled:
        yield environment,None
        return
    binaries={name:shutil.which(name) for name in ('initdb','pg_ctl')}
    if not all(binaries.values()):raise RuntimeError('PostgreSQL initdb/pg_ctl required')
    from aegis.postgres_bootstrap import initialize
    data=root/'cluster';unix=root/'socket';unix.mkdir(mode=0o700)
    def run(args):
        subprocess.run(args,env=environment,check=True,capture_output=True,timeout=30)
    run([binaries['initdb'],'-D',str(data),'--auth=trust','--no-locale','--encoding=UTF8'])
    started=False
    try:
        run([binaries['pg_ctl'],'-D',str(data),'-l',str(root/'postgres.log'),'-o',f"-c listen_addresses='' -k {unix} -p 55439",'-w','start']);started=True
        dsn=f'host={unix} port=55439 dbname=postgres';schema='owned_execution_load'
        initialize(dsn,schema)
        yield {**environment,'AEGIS_STORAGE_BACKEND':'postgres','AEGIS_POSTGRES_DSN':dsn,'AEGIS_POSTGRES_SCHEMA':schema},dsn
    finally:
        if started:run([binaries['pg_ctl'],'-D',str(data),'-w','-m','fast','stop'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration',type=bounded_int(2,3600),default=300)
    parser.add_argument('--clients',type=bounded_int(1,8),default=2)
    parser.add_argument('--postgres',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    environment={key:value for key,value in os.environ.items() if not key.startswith(('AEGIS_','PG')) and key not in ('PYTHONPATH','PYTHONHOME')}
    environment.update(AEGIS_TARGET_RPS='20',AEGIS_REQUEST_RETRIES='0',AEGIS_REQUEST_TIMEOUT='5')
    fingerprint=hashlib.sha256()
    for path in sorted((ROOT/'aegis').rglob('*.py')):
        fingerprint.update(path.relative_to(ROOT).as_posix().encode());fingerprint.update(path.read_bytes())
    counts=Counter();latencies=deque(maxlen=2000);samples=[];errors=[];lock=threading.Lock();stopped=threading.Event()
    held=threading.Event();release=threading.Event()
    class Target(LabHandler):
        requests=[];hardened=False;fault=False;hold=False
        def do_GET(self):
            if type(self).hold:
                held.set()
                if not release.wait(15):return
            try:super().do_GET()
            except (BrokenPipeError,ConnectionResetError):pass
    target=ThreadingHTTPServer(('127.0.0.1',0),Target)
    target.daemon_threads=True
    target_thread=threading.Thread(target=target.serve_forever,daemon=True);target_thread.start()
    workers=[];process=None;client=None;logs=[];cycles=0;stage='startup'
    result={'valid':False,'backend':'postgres' if args.postgres else 'sqlite','requested_seconds':args.duration,'source_sha256':fingerprint.hexdigest()}
    try:
        with tempfile.TemporaryDirectory(prefix='aegis-execution-load-',dir='/tmp') as temporary:
            folder=Path(temporary);workspace=folder/'workspace'
            with owned_postgres(folder,args.postgres,environment) as (server_env,dsn):
                def start(generation):
                    nonlocal process,client
                    listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
                    log=(folder/f'server-{generation}.log').open('wb');logs.append(log)
                    try:
                        process=subprocess.Popen([sys.executable,'-c',SERVER,str(workspace),str(listener.fileno()),str(folder/f'clean-{generation}')],cwd=ROOT,env=server_env,pass_fds=(listener.fileno(),),stdout=log,stderr=log)
                    finally:listener.close()
                    client=httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False,timeout=15)
                    until=time.monotonic()+20
                    while True:
                        if process.poll() is not None:raise RuntimeError('Owned service startup failed')
                        try:
                            response=client.get('/api/health');response.raise_for_status();return
                        except httpx.TransportError:
                            if time.monotonic()>until:raise RuntimeError('Owned startup deadline')
                            time.sleep(.05)
                def http(method,path,body=None):
                    response=client.request(method,'/api'+path,json=body);response.raise_for_status();return response.json()
                def plan(name):return http('POST','/tasks',{'name':name,'asset_ids':[asset['id']],'checks':['security_headers','cookie_policy','endpoint_inventory']})
                def finish(id):
                    until=time.monotonic()+15
                    while time.monotonic()<until:
                        detail=http('GET','/tasks/'+id)
                        if detail['task']['status'] in ('completed','failed','interrupted','stopped'):return detail
                        time.sleep(.03)
                    raise RuntimeError('Owned task did not finish')
                def approve(task):
                    http('POST','/tasks/'+task['id']+'/approve');return finish(task['id'])
                try:
                    start(1)
                    http('POST','/auth/setup',{'password':'owned-execution-load-password-only'})
                    cookie=dict(client.cookies)
                    asset=http('POST','/assets',{'name':'Owned execution fixture','url':f'http://127.0.0.1:{target.server_port}/','authorized':True})
                    paths=['/records/tasks?limit=25','/records/findings?limit=25','/overview','/runtime','/reports/export?format=json']
                    def read_worker(index):
                        iteration=index
                        try:
                            with httpx.Client(base_url=str(client.base_url),cookies=cookie,trust_env=False,timeout=15) as reader:
                                while not stopped.is_set():
                                    path=paths[iteration%len(paths)];iteration+=1;at=time.monotonic()
                                    response=reader.get('/api'+path)
                                    if response.status_code==429 and 'export' in path:
                                        assert float(response.headers['Retry-After'])>0;key='export_limited'
                                    else:
                                        response.raise_for_status();body=response.json();key=path.split('?')[0]
                                        if 'records' in path:assert len(body['items'])<=25
                                        if path=='/runtime':assert body['queue_watchdog']['errors']==0 and body['event_planner']['errors']==0
                                    with lock:counts[key]+=1;latencies.append(time.monotonic()-at)
                                    stopped.wait(.02)
                        except Exception as exc:
                            with lock:errors.append(type(exc).__name__)
                            stopped.set()
                    for i in range(args.clients):
                        thread=threading.Thread(target=read_worker,args=(i,),daemon=True);workers.append(thread);thread.start()
                    begin=time.monotonic();baseline=process_sample(process.pid);stage='execution_and_reads'
                    while time.monotonic()-begin<args.duration and not stopped.is_set():
                        Target.hardened=False;Target.fault=False
                        before=len(Target.requests);pending=plan('Owned churn '+str(cycles))
                        assert len(Target.requests)==before
                        detail=approve(pending);assert detail['task']['status']=='completed'
                        finding=next(row for row in detail['findings'] if row['code']=='missing-nosniff')
                        current=http('GET','/findings/'+finding['id'])['finding']
                        http('PATCH','/findings/'+finding['id'],{'expected_revision':current.get('triage_revision',1),'status':'accepted','acceptance_reason':'Owned synthetic decision'})
                        Target.fault=True
                        inconclusive=approve(http('POST','/findings/'+finding['id']+'/retest'))
                        after=http('GET','/findings/'+finding['id'])
                        assert after['finding']['status']=='accepted' and after['retests'][0]['conclusion']=='inconclusive'
                        Target.fault=False;Target.hardened=True
                        resolved=approve(http('POST','/findings/'+finding['id']+'/retest'))
                        after=http('GET','/findings/'+finding['id'])
                        assert after['finding']['status']=='resolved' and after['retests'][0]['conclusion']=='resolved'
                        assert resolved['task']['status']=='completed'
                        cycles+=1;samples.append({'elapsed':round(time.monotonic()-begin,3),**process_sample(process.pid)})
                        stopped.wait(.2)
                    elapsed=time.monotonic()-begin;stopped.set()
                    for thread in workers:
                        thread.join(20);assert not thread.is_alive()
                    assert not errors and cycles>0
                    assert all(counts[path.split('?')[0]]>0 for path in paths)
                    steady=http('GET','/runtime');assert steady['exports']['active']==0
                    assert steady['queue_watchdog']['errors']==steady['event_planner']['errors']==0
                    # Exercise concurrently admitted work sharing the target limiter.
                    stage='concurrent_approvals';before_burst=len(Target.requests)
                    burst=[plan('Owned admission burst '+str(i)) for i in range(6)]
                    assert len(Target.requests)==before_burst
                    for item in burst:http('POST','/tasks/'+item['id']+'/approve')
                    assert all(finish(item['id'])['task']['status']=='completed' for item in burst)
                    # Lose both running and queued work, keeping one unapproved control.
                    stage='process_loss';pending=plan('Owned never-approved recovery control')
                    lost=[plan('Owned held GET during process loss '+str(i)) for i in range(4)]
                    interrupted=lost[0]
                    Target.hold=True;release.clear();held.clear()
                    for item in lost:http('POST','/tasks/'+item['id']+'/approve')
                    assert held.wait(5)
                    before_crash=http('GET','/runtime')
                    assert before_crash['tasks']['running']==2 and before_crash['tasks']['queued']==2
                    old_cookie=dict(client.cookies);process.kill();process.wait(timeout=10);assert process.returncode==-9
                    client.close();client=None
                    Target.hold=False;release.set();time.sleep(.1)
                    count_after_loss=len(Target.requests)
                    stage='restart_recovery';start(2);client.cookies.update(old_cookie)
                    assert http('GET','/auth/status')['authenticated']
                    assert all(http('GET','/tasks/'+item['id'])['task']['status']=='interrupted' for item in lost)
                    assert http('GET','/tasks/'+pending['id'])['task']['status']=='pending'
                    time.sleep(.3);assert len(Target.requests)==count_after_loss
                    retry=http('POST','/tasks/'+interrupted['id']+'/retry');assert retry['status']=='pending'
                    assert len(Target.requests)==count_after_loss
                    completed=approve(retry);assert completed['task']['status']=='completed'
                    stage='planner_catchup';until=time.monotonic()+10
                    while True:
                        page=http('GET','/tasks/'+retry['id']+'/planner')
                        if page.get('status') in ('ready','no_proposal'):break
                        if time.monotonic()>until:raise RuntimeError('Event planner failed to catch up')
                        time.sleep(.05)
                    stage='audit_and_shutdown';audit=http('POST','/audit/verify',{});assert audit['status']=='verified'
                    runtime=http('GET','/runtime');assert runtime['queue_watchdog']['errors']==runtime['event_planner']['errors']==0
                    assert not any(runtime['tasks'].get(s,0) for s in ('running','queued','stopping'))
                    assert runtime['tasks']['completed']==cycles*2+7 and runtime['tasks']['failed']==cycles
                    assert runtime['tasks']['interrupted']==4 and runtime['tasks']['pending']==1
                    process.terminate();process.wait(timeout=15);assert process.returncode in (0,-15,143)
                    assert (folder/'clean-2').read_text()=='complete'
                    if args.postgres:
                        from aegis.postgres_maintenance import PostgresLease
                        with PostgresLease(dsn,'owned_execution_load'):pass
                        assert not workspace.exists()
                    else:
                        from aegis.maintenance import WorkspaceLease
                        with WorkspaceLease(workspace):pass
                    ordered=sorted(latencies)
                    result.update(valid=True,elapsed_seconds=round(elapsed,3),cycles=cycles,approved_churn_tasks=cycles*3,approved_burst_tasks=6,
                        python=sys.version.split()[0],platform=platform.system(),architecture=platform.machine(),
                        owned_target_requests=len(Target.requests),read_responses=dict(counts),read_errors=errors,
                        sampled_latency_seconds={'p50':ordered[int((len(ordered)-1)*.5)],'p95':ordered[int((len(ordered)-1)*.95)]},
                        baseline=baseline,sample_peak_rss_kib=max([baseline['rss_kib'],*[s['rss_kib'] for s in samples]]),samples=samples,
                        runtime_steady=steady,runtime_before_loss=before_crash,runtime_after_recovery=runtime,
                        recovery={'process_loss_exit':-9,'running_before_loss':2,'queued_before_loss':2,'recovered_interrupted':4,'unapproved_status':'pending','automatic_target_requests':0,'retry_new_approval_completed':True,'clean_shutdown_marker':True,'lease_reacquired':True},audit=audit)
                finally:
                    stopped.set();release.set()
                    for thread in workers:thread.join(20)
                    if process is not None and process.poll() is None:
                        process.terminate()
                        try:process.wait(timeout=15)
                        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
                    if client is not None:client.close()
                    for log in logs:log.close()
        result['temporary_resources_removed']=True
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2))
        print(json.dumps({k:result[k] for k in ('valid','backend','elapsed_seconds','cycles','approved_churn_tasks','owned_target_requests','read_responses','sample_peak_rss_kib','temporary_resources_removed')}))
    except Exception as error:
        result.update(valid=False,failure_type=type(error).__name__,failure_stage=stage,
            cycles=cycles,read_responses=dict(counts),read_errors=list(errors),owned_target_requests=len(Target.requests))
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2))
        raise
    finally:
        release.set();target.shutdown();target.server_close();target_thread.join(timeout=2)


if __name__=='__main__':main()
