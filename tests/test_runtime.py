"""Real loopback peers exercise shared limits, slow-drip I/O, retries and queue deadlines."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from fastapi.testclient import TestClient
from aegis.app import create_app
from aegis.dns import Resolver
from aegis.llm import completion
from aegis.network import Transport, ScopeError
from aegis.runtime import ExecutionPolicy, TaskControl, TaskDeadline, RequestDeadline, OriginLimiter
from tests.test_validation import client, lab, register, task, finish
from tests.test_identity import add, login


@pytest.fixture
def peer():
    class Handler(BaseHTTPRequestHandler):
        calls=[];lock=threading.Lock();entered=threading.Event();release=threading.Event();slow=False
        def do_GET(self):
            with self.lock:
                self.calls.append((self.path,time.monotonic()))
                count=sum(path==self.path for path,_ in self.calls)
            route='/drip' if self.slow else self.path.split('?',1)[0]
            if route=='/held':
                self.entered.set();self.release.wait(3)
            status=503 if route=='/flaky' and count==1 else 429 if route=='/retry-later' or (route=='/throttle' and count==1) else 200
            body=b'OK' if route not in ('/drip','/headers') else b'x'*40
            try:
                if route=='/headers':
                    self.entered.set()
                    for byte in b'HTTP/1.0 200 OK\r\nContent-Length: 2\r\n\r\nOK':
                        self.wfile.write(bytes([byte]));self.wfile.flush();time.sleep(.025)
                    return
                self.send_response(status);self.send_header('Content-Length',str(len(body)))
                if status==429:self.send_header('Retry-After','120' if route=='/retry-later' else '0')
                self.end_headers();self.entered.set()
                if route=='/drip':
                    for byte in body:
                        self.wfile.write(bytes([byte]));self.wfile.flush();time.sleep(.025)
                else:self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError):pass
        def do_POST(self):
            self.path='/drip';self.do_GET()
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}/',Handler
    Handler.release.set();server.shutdown();server.server_close();thread.join(timeout=2)


def test_shared_origin_spacing_applies_across_transports_and_tasks(peer):
    url,handler=peer
    policy=ExecutionPolicy(target_rps=10,target_parallel=2,request_retries=0)
    limiter=OriginLimiter(policy)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda path:Transport(url,True,policy=policy,limiter=limiter).get(url+path),['one','two','three','four']))
    assert all(item['status']==200 for item in results)
    starts=sorted(timestamp for _,timestamp in handler.calls)
    assert all(later-earlier>=.075 for earlier,later in zip(starts,starts[1:]))
    counters=limiter.snapshot()
    assert counters['requests']==4 and counters['throttled_requests']==3 and counters['active_requests']==0


def test_parallel_slot_is_shared_and_stop_interrupts_waiting_request(peer):
    url,handler=peer
    policy=ExecutionPolicy(target_rps=20,target_parallel=1,request_retries=0)
    limiter=OriginLimiter(policy);stop=threading.Event();control=TaskControl(stop)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(Transport(url,True,policy=policy,limiter=limiter).get,url+'held')
        assert handler.entered.wait(1)
        second=pool.submit(Transport(url,True,policy=policy,limiter=limiter,control=control).get,url+'second')
        time.sleep(.1);stop.set()
        with pytest.raises(InterruptedError):second.result(timeout=1)
        assert [path for path,_ in handler.calls]==['/held']
        handler.release.set();assert first.result(timeout=1)['status']==200
    assert limiter.snapshot()['active_requests']==0


@pytest.mark.parametrize('path',['drip','headers'])
def test_request_wall_clock_deadline_stops_slow_drip_headers_and_body(peer,path):
    url,_=peer;records=[]
    policy=ExecutionPolicy(request_timeout=.15,request_retries=0)
    started=time.monotonic()
    with pytest.raises(RequestDeadline):
        Transport(url,True,record=records.append,policy=policy,delay=0).get(url+path)
    assert time.monotonic()-started<.6
    assert records[0]['status']==0 and records[0]['error_type']=='RequestDeadline'
    assert 'body_sha256' not in records[0]


def test_task_stop_interrupts_in_flight_socket(peer):
    url,handler=peer;stop=threading.Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(Transport(url,True,policy=ExecutionPolicy(request_retries=0),control=TaskControl(stop)).get,url+'drip')
        assert handler.entered.wait(1);stop.set()
        with pytest.raises(InterruptedError):future.result(timeout=.6)


@pytest.mark.parametrize('path',['flaky','throttle'])
def test_transient_get_retry_records_every_attempt_and_preserves_budget(peer,path):
    url,handler=peer;records=[]
    policy=ExecutionPolicy(request_retries=1,retry_delay=.05,request_budget=2,target_rps=20)
    limiter=OriginLimiter(policy)
    transport=Transport(url,True,record=records.append,policy=policy,limiter=limiter)
    result=transport.get(url+path+'?secret=NEVER-PERSIST-THIS')
    assert result['status']==200
    assert 'NEVER-PERSIST-THIS' not in str(records)
    assert [row['attempt'] for row in records[-2:]]==[1,2]
    assert limiter.snapshot()['retries']==1 and transport.count==2
    with pytest.raises(ScopeError,match='예산'):transport.get(url+path)
    assert len(handler.calls)==2


def test_stalled_dns_has_bounded_workers_and_can_be_cancelled(monkeypatch):
    resolver=Resolver(workers=1,queued=1);entered=threading.Event();release=threading.Event()
    def stall(*args,**kwargs):
        entered.set();release.wait(2);return []
    monkeypatch.setattr('socket.getaddrinfo',stall)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(resolver.resolve,'fixture.invalid',80,TaskControl(),.15)
            assert entered.wait(1)
            with pytest.raises(RequestDeadline):future.result(timeout=.5)
        assert resolver.snapshot()=={'active':1,'queued':0,'workers':1,'queue_limit':1}
        started=time.monotonic()
        with pytest.raises(RequestDeadline):resolver.resolve('another.invalid',80,TaskControl(),.1)
        assert time.monotonic()-started<.4 and resolver.snapshot()['queued']<=1
        stop=threading.Event();stop.set()
        with pytest.raises(InterruptedError):resolver.resolve('third.invalid',80,TaskControl(stop),1)
    finally:
        release.set();resolver.jobs.join()


def test_execution_deadline_records_failure_and_retry_requires_new_approval(client,peer):
    url,_=peer;engine=client.app.state.engine
    engine.policy=ExecutionPolicy(task_timeout=.2,request_timeout=2,request_retries=0)
    engine.limiter=OriginLimiter(engine.policy)
    asset=register(client,url+'drip')
    plan=task(client,asset,['security_headers','cookie_policy'])
    client.post('/api/tasks/'+plan['id']+'/approve')
    result=finish(client,plan['id'])
    assert result['task']['status']=='failed' and result['task']['termination_reason']=='timeout'
    assert {row['status'] for row in result['coverage']}=={'failed'}
    assert not result['findings']
    assert client.get('/api/runtime').json()['timeouts']==1
    with login(client.app,add(client,'viewer')['username']) as viewer:
        assert viewer.get('/api/runtime').status_code==200
        assert viewer.post('/api/tasks/'+plan['id']+'/retry').status_code==403
    retried=client.post('/api/tasks/'+plan['id']+'/retry').json()
    assert retried['status']=='pending' and retried['retry_of']==plan['id'] and retried['execution_policy']==engine.policy.public()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:client.post('/api/tasks/'+plan['id']+'/retry').json()['id'],range(2)))
    assert set(results)=={retried['id']}
    assert client.get('/api/tasks/'+plan['id']).json()['task']['status']=='failed'


def test_queued_deadline_expires_without_target_requests_and_cleans_up(client,lab,monkeypatch):
    engine=client.app.state.engine;engine.policy=ExecutionPolicy(queue_timeout=1)
    monkeypatch.setattr(engine.pool,'submit',lambda *_:Future())
    asset=register(client,lab[0]);plan=task(client,asset,['security_headers'])
    client.post('/api/tasks/'+plan['id']+'/approve')
    metrics=client.get('/api/runtime').json()
    assert metrics['tasks']['queued']==1 and metrics['policy']['queue_timeout']==1
    result=finish(client,plan['id'])
    assert result['task']['termination_reason']=='queue_timeout' and result['task']['status']=='failed'
    assert result['coverage'][0]['status']=='failed' and lab[1].requests==[]
    assert not engine.stops and not engine.futures


def test_policy_change_requires_new_review_and_retry_uses_current_asset_revision(client,lab):
    engine=client.app.state.engine;asset=register(client,lab[0]);plan=task(client,asset,['security_headers'])
    engine.policy=ExecutionPolicy(target_rps=1)
    assert client.post('/api/tasks/'+plan['id']+'/approve').status_code==409
    client.app.state.store.patch('tasks',plan['id'],status='interrupted')
    revised=client.put('/api/assets/'+asset['id'],json={**asset,'authorized':True,'name':'Updated fixture'}).json()
    assert 'revision' in revised
    fresh=client.post('/api/tasks/'+plan['id']+'/retry').json()
    assert fresh['scope_snapshot'][0]['revision']==revised['revision']
    assert fresh['execution_policy']['target_rps']==1
    assert client.post('/api/tasks/'+fresh['id']+'/retry').status_code==409
    client.post('/api/assets/'+asset['id']+'/archive',json={'archived':True})
    assert client.post('/api/tasks/'+plan['id']+'/retry').status_code==409


def test_provider_slow_body_obeys_execution_deadline_without_following_redirects(peer):
    url,_=peer;control=TaskControl(deadline=time.monotonic()+.15)
    with pytest.raises(TaskDeadline):completion(url+'v1','PRIVATE-FIXTURE-KEY',{},allow_local=True,control=control)


@pytest.mark.parametrize('name,value',[('TARGET_RPS','nan'),('CONCURRENT_TASKS','0'),('REQUEST_RETRIES','3'),('TASK_TIMEOUT','0'),('PENDING_LIMIT','one')])
def test_invalid_execution_policy_fails_without_exposing_values(monkeypatch,name,value):
    monkeypatch.setenv('AEGIS_'+name,value)
    with pytest.raises(ValueError,match='AEGIS_'+name):ExecutionPolicy.from_env()


@pytest.fixture
def tls_peer(tmp_path,monkeypatch):
    import subprocess
    import ssl
    cert=tmp_path/'cert.pem';key=tmp_path/'key.pem'
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','2',
                    '-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost,IP:127.0.0.1',
                    '-keyout',str(key),'-out',str(cert)],check=True,capture_output=True)
    monkeypatch.setenv('SSL_CERT_FILE',str(cert))
    class Handler(BaseHTTPRequestHandler):
        calls=[]
        def do_GET(self):
            self.calls.append(self.path)
            body=b'<html>fixture</html>';self.send_response(200)
            self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_POST(self):
            import json
            self.calls.append(self.path)
            assert self.path=='/v1/chat/completions'
            assert self.headers.get('Authorization')=='Bearer tls-provider-fixture-key'
            request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            supplied=json.loads(request['messages'][1]['content'])['checks']
            body=json.dumps({'choices':[{'message':{'content':json.dumps({'checks':list(reversed(supplied))})}}],
                             'usage':{'prompt_tokens':32,'completion_tokens':16,'total_tokens':48}}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert,key)
    server.socket=context.wrap_socket(server.socket,server_side=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'https://127.0.0.1:{server.server_port}/',Handler
    server.shutdown();server.server_close();thread.join(timeout=2)


def test_real_tls_verification_and_provider_plan_with_usage(client,tls_peer,lab,monkeypatch):
    url,handler=tls_peer
    response=Transport(url,True,delay=0).get()
    assert response['status']==200 and response['certificate']['notAfter']
    monkeypatch.setenv('AEGIS_LLM_API_KEY','tls-provider-fixture-key')
    monkeypatch.setenv('AEGIS_LLM_MODEL','fixture-model')
    monkeypatch.setenv('AEGIS_LLM_BASE_URL',url+'v1')
    asset=register(client,lab[0]);checks=['security_headers','cookie_policy']
    plan=client.post('/api/tasks',json={'name':'TLS provider fixture','asset_ids':[asset['id']],'checks':checks,'planner':'ai'}).json()
    client.post('/api/tasks/'+plan['id']+'/approve');result=finish(client,plan['id'])
    assert result['task']['status']=='completed' and result['task']['plan']==list(reversed(checks))
    usage=next(event['detail']['tokens'] for event in result['events'] if 'tokens' in event['detail'])
    assert usage['total_tokens']==48 and handler.calls==['/','/v1/chat/completions']
    assert usage['status']=='reported'
    call=result['task']['llm_usage']
    assert call['tokens']==usage and call['outcome']=='accepted'
    exported=client.get('/api/reports/export',params={'format':'json','task_id':plan['id']}).json()
    assert exported['tasks'][0]['llm_usage']==call
    markdown=client.get('/api/reports/export',params={'format':'markdown','task_id':plan['id']})
    assert markdown.status_code==200 and 'AI 계획 호출 기록' in markdown.text
    assert '"total_tokens": 48' in markdown.text and '"status": "reported"' in markdown.text
    assert 'tls-provider-fixture-key' not in str(result)


def test_real_tls_hostname_mismatch_never_retries_credentials(tls_peer,monkeypatch):
    import socket
    import ssl
    url,handler=tls_peer;records=[]
    port=int(url.split(':')[-1].rstrip('/'))
    monkeypatch.setattr(socket,'getaddrinfo',lambda *args,**kwargs:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',port))])
    with pytest.raises(ssl.SSLCertVerificationError):
        Transport(f'https://wrong-host.invalid:{port}/',True,record=records.append,delay=0).get(headers={'Authorization':'Bearer private-fixture-value'})
    assert handler.calls==[] and len(records)==1 and records[0]['attempt']==1
    assert 'private-fixture-value' not in str(records)


def test_dns_wrapper_preserves_cancellation_and_timeout_types(monkeypatch):
    from aegis.network import resolve
    class Failed:
        def resolve(self,*args,**kwargs):raise TaskDeadline('fixture timeout')
    monkeypatch.setattr('aegis.network.resolver',lambda:Failed())
    with pytest.raises(TaskDeadline):resolve('fixture.invalid',80)


def test_shutdown_cancels_queue_and_refuses_new_approval(client,lab,monkeypatch):
    engine=client.app.state.engine
    monkeypatch.setattr(engine.pool,'submit',lambda *_:Future())
    asset=register(client,lab[0]);queued=task(client,asset,['security_headers']);pending=task(client,asset,['security_headers'])
    client.post('/api/tasks/'+queued['id']+'/approve');engine.shutdown()
    result=client.get('/api/tasks/'+queued['id']).json()
    assert result['task']['status']=='stopped' and result['coverage'][0]['status']=='cancelled'
    assert not engine.stops and not engine.queue_thread.is_alive()
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==409
    assert client.get('/api/health').status_code==503


def test_long_retry_after_is_respected_by_not_retrying_early(peer):
    url,handler=peer;policy=ExecutionPolicy(request_retries=2)
    limiter=OriginLimiter(policy)
    assert Transport(url,True,policy=policy,limiter=limiter).get(url+'retry-later')['status']==429
    assert len(handler.calls)==1 and limiter.snapshot()['retries']==0


def test_retest_execution_deadline_is_inconclusive_and_preserves_accepted_decision(client,peer):
    url,handler=peer
    asset=register(client,url);plan=task(client,asset,['security_headers'])
    client.post('/api/tasks/'+plan['id']+'/approve');result=finish(client,plan['id'])
    finding=result['findings'][0]
    accepted=client.patch('/api/findings/'+finding['id'],json={'expected_revision':1,'status':'accepted','acceptance_reason':'Reviewed local control'}).json()
    engine=client.app.state.engine;engine.policy=ExecutionPolicy(task_timeout=.2,request_retries=0)
    engine.limiter=OriginLimiter(engine.policy);handler.slow=True
    retest=client.post('/api/findings/'+finding['id']+'/retest').json()
    client.post('/api/tasks/'+retest['id']+'/approve');result=finish(client,retest['id'])
    assert result['task']['termination_reason']=='timeout'
    detail=client.get('/api/findings/'+finding['id']).json()
    assert detail['finding']['status']=='accepted' and detail['finding']['triage_revision']==accepted['triage_revision']
    assert detail['retests'][0]['conclusion']=='inconclusive' and detail['retests'][0]['triage_effect']=='unchanged'


def test_shutdown_interrupts_running_io_and_marks_server_shutdown(client,peer):
    url,handler=peer;asset=register(client,url+'drip');plan=task(client,asset,['security_headers'])
    client.post('/api/tasks/'+plan['id']+'/approve');assert handler.entered.wait(1)
    started=time.monotonic();client.app.state.engine.shutdown()
    assert time.monotonic()-started<.6
    result=client.get('/api/tasks/'+plan['id']).json()
    assert result['task']['status']=='stopped' and result['task']['termination_reason']=='shutdown'
    assert result['coverage'][0]['status']=='cancelled'
