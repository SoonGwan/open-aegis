"""Rehearse installed transfer CLI using an owned disposable PostgreSQL cluster."""
import argparse
import hashlib
import json
import os
from http.cookiejar import CookieJar
from urllib.error import HTTPError,URLError
from urllib.request import Request,build_opener,HTTPCookieProcessor,ProxyHandler
import socket as socket_module
import time
from pathlib import Path
import shutil
import subprocess
import tempfile
import venv


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel-dir',required=True,type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    wheels=list(args.wheel_dir.resolve().glob('open_aegis-*.whl'))
    if len(wheels)!=1:parser.error('Supply one wheel')
    wheel=wheels[0]
    binaries={name:shutil.which(name) for name in ('initdb','pg_ctl','createdb','pg_dump','pg_restore')}
    if not all(binaries.values()):parser.error('PostgreSQL client and server binaries are required')
    environment={key:value for key,value in os.environ.items() if not key.startswith(('AEGIS_','PYTHON','PG')) and key!='VIRTUAL_ENV'}
    with tempfile.TemporaryDirectory(prefix='aegis-installed-pg-',dir='/tmp') as directory:
        temporary=Path(directory);installation=temporary/'installation';data=temporary/'cluster';socket=temporary/'socket';socket.mkdir(mode=0o700)
        venv.EnvBuilder(with_pip=True).create(installation)
        python=installation/'bin'/'python';cli=installation/'bin'/'aegis-transfer-storage'
        def run(command,label,env=None,input=None):
            result=subprocess.run([str(item) for item in command],cwd=temporary,env=env or environment,input=input,capture_output=True,text=True,timeout=180)
            if result.returncode:raise RuntimeError(label+' failed')
            return result.stdout
        run([python,'-m','pip','install','-r',root/'requirements.lock','-r',root/'requirements-postgres.lock'],'locked installation')
        run([python,'-m','pip','install','--no-deps',wheel],'wheel installation');run([python,'-m','pip','check'],'pip check')
        run([cli,'--help'],'transfer entry point')
        run([binaries['initdb'],'-D',data,'--auth=trust','--no-locale','--encoding=UTF8'],'initdb')
        run([binaries['pg_ctl'],'-D',data,'-l',temporary/'server.log','-o',f"-c listen_addresses='' -k {socket} -p 55439",'-w','start'],'owned PostgreSQL start')
        environment.update(AEGIS_POSTGRES_DSN=f'host={socket} port=55439 dbname=postgres',PGHOST=str(socket),PGPORT='55439')
        try:
            run([python,'-I','-c',"import os,psycopg;\nwith psycopg.connect(os.environ['AEGIS_POSTGRES_DSN']) as db:\n db.execute('CREATE ROLE owned_bootstrap_role LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT');db.execute('GRANT CONNECT,CREATE ON DATABASE postgres TO owned_bootstrap_role')"],
                'owned ordinary initialization role')
            bootstrap_env={**environment,'AEGIS_STORAGE_BACKEND':'postgres','AEGIS_POSTGRES_SCHEMA':'owned_bootstrap',
                'AEGIS_POSTGRES_DSN':environment['AEGIS_POSTGRES_DSN']+' user=owned_bootstrap_role',
                'AEGIS_DATA_DIR':str(temporary/'unused-bootstrap'),'AEGIS_SETUP_TOKEN':'owned-installed-bootstrap-token','AEGIS_HOST':'127.0.0.1'}
            initialized=json.loads(run([installation/'bin'/'aegis-init-postgres'],'installed fresh native initialization',env=bootstrap_env))
            assert initialized['created'] and initialized['users']==initialized['sessions']==0 and initialized['audit']['events']==0
            run([python,'-I','-c',"import os,psycopg;\nwith psycopg.connect(os.environ['AEGIS_POSTGRES_DSN']) as db:\n db.execute('REVOKE CREATE ON DATABASE postgres FROM owned_bootstrap_role')"],
                'revoke bootstrap database CREATE before runtime')
            with socket_module.socket() as listener:
                listener.bind(('127.0.0.1',0));bootstrap_port=listener.getsockname()[1]
            bootstrap_env['AEGIS_PORT']=str(bootstrap_port)
            with (temporary/'bootstrap-server.log').open('w') as log:
                process=subprocess.Popen([str(python),'-I','-m','aegis'],cwd=temporary,env=bootstrap_env,stdout=log,stderr=subprocess.STDOUT)
                bootstrap_base='http://127.0.0.1:'+str(bootstrap_port)
                bootstrap_client=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
                def bootstrap_http(path,body=None,expected=200):
                    headers={'Content-Type':'application/json'} if body is not None else {}
                    request=Request(bootstrap_base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
                    try:response=bootstrap_client.open(request,timeout=3)
                    except HTTPError as error:response=error
                    with response:
                        if response.status!=expected:raise RuntimeError('Installed fresh native HTTP validation failed')
                        return json.loads(response.read())
                try:
                    deadline=time.monotonic()+15
                    while True:
                        if process.poll() is not None:raise RuntimeError('Installed fresh native service exited')
                        try:assert bootstrap_http('/api/health')['status']=='ok';break
                        except (URLError,TimeoutError):
                            if time.monotonic()>=deadline:raise RuntimeError('Installed fresh native startup timed out')
                            time.sleep(.05)
                    assert bootstrap_http('/api/auth/status')['setup_required']
                    bootstrap_http('/api/assets',expected=401)
                    bootstrap_http('/api/auth/setup',{'password':'owned-installed-bootstrap-password'},expected=403)
                    assert bootstrap_http('/api/auth/setup',{'password':'owned-installed-bootstrap-password','setup_token':'owned-installed-bootstrap-token'})['user']['role']=='admin'
                    bootstrap_http('/api/auth/setup',{'password':'owned-installed-bootstrap-password','setup_token':'owned-installed-bootstrap-token'},expected=409)
                    assert bootstrap_http('/api/settings')['storage']=='postgres'
                    bootstrap_http('/api/notes',{'title':'Fresh native workspace','content':'Owned ordinary role'})
                    assert bootstrap_http('/api/audit/verify',{},expected=200)['status']=='verified'
                finally:
                    if process.poll() is None:process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5);raise RuntimeError('Installed fresh native shutdown timed out')
                assert process.returncode in (0,-15,143) and not (temporary/'unused-bootstrap').exists()
            source=temporary/'source'/'aegis.db'
            origin=json.loads(run([python,'-I','-c','''
import json,sys,time,os,psycopg
from pathlib import Path
import aegis
from aegis.store import Store
from aegis.auth import new_user
assert Path(aegis.__file__).is_relative_to(Path(sys.prefix))
with psycopg.connect(os.environ['AEGIS_POSTGRES_DSN']) as db:
    assert db.execute('SHOW fsync').fetchone()[0]=='on'
s=Store(sys.argv[1]);u=new_user('admin','합성 관리자','admin','owned-installed-transfer-password');s.add_user(u)
s.session('owned-old-cookie',time.time()+3600,u['id']);s.put('notes',{'id':'proof','title':'합성 한글 🚀','amount':'0.000000000000001'})
s.event(None,'합성 설치본 전송 검수',detail={'amount':'0.000000000000001'})
print(json.dumps({'module':aegis.__file__,'audit':s.audit_integrity()}))
''',source],'installed source creation'))
            forward=json.loads(run([cli,'sqlite-to-postgres','--source',source,'--schema','owned_transfer'],'installed transfer'))
            forward_proof=temporary/'forward.json';forward_proof.write_text(json.dumps(forward));forward_proof.chmod(0o600)
            native=json.loads(run([python,'-I','-c','''
import json,sys,time,os
from pathlib import Path
from aegis.postgres_store import PostgresStore
from aegis.postgres_transfer import postgres_manifest
from aegis import call_ledger
from aegis.llm import token_usage
from aegis.costs import estimate
from aegis.usage import usage_summary
from aegis.engine import Engine
from aegis.runtime import ExecutionPolicy
from aegis.tool_contracts import contracts_for
from aegis.coverage import planned_slots
from aegis.graph import build_graph
from aegis.reporting import report_chunks
from aegis.export_limits import ExportPolicy,ExportPool
from aegis.audit_review import AuditReview
from aegis import scopesentry as imports
from aegis.scopesentry_remote import Sources,PageInput
from aegis.postgres_maintenance import PostgresLease
from aegis.maintenance import WorkspaceBusy
from aegis.postgres_transfer import postgres_to_sqlite,connect
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import threading
s=PostgresStore(os.environ['AEGIS_POSTGRES_DSN'],'owned_transfer')
assert Path(sys.modules[s.__class__.__module__].__file__).is_relative_to(Path(sys.prefix))
proof=json.loads(Path(sys.argv[1]).read_text())
with s.transaction() as db:assert postgres_manifest(db)==proof['manifest']
assert s.audit_integrity()==proof['audit'] and not s.valid_session('owned-old-cookie')
u=s.user(username='admin');s.session('native-cookie',time.time()+300,u['id'])
assert s.valid_session('native-cookie')
s.update_user(u['id'],name='합성 PostgreSQL 관리자');assert s.valid_session('native-cookie')
s.update_user(u['id'],role='operator');assert not s.valid_session('native-cookie')
s.put('notes',{'id':'native','title':'설치본 PostgreSQL 저장','amount':'0.000000000000001'})
s.event(None,'설치본 PostgreSQL 기록',detail={'note_id':'native'})
assert s.page('notes',search='PostgreSQL')['total']==1
at=time.time();price={'status':'unconfigured','quote':None}
call_id=call_ledger.start(s,'conversation','owned','installed-model','https://owned.invalid/v1',at,price)
tokens=token_usage({'prompt_tokens':3,'completion_tokens':2,'total_tokens':5})
detail={'call_id':call_id,'model':'installed-model','started_at':at,'observed_at':time.time(),'outcome':'accepted','tokens':tokens,'cost':estimate(tokens,price,at)}
call_ledger.observe(s,call_id,detail)
s.put_message_exchange({'id':'q','task_id':'owned','role':'user','content':'합성 질문'},
                       {'id':'r','task_id':'owned','role':'assistant','content':'합성 답변','assistant_generation':detail})
pending=call_ledger.start(s,'planner','owned','installed-model','https://owned.invalid/v1',time.time(),price)
call_ledger.recover(s);assert s.get('llm_calls',pending)['state']=='interrupted'
usage=usage_summary(s,source='all',ledger='attempts')
assert usage['calls']==2 and usage['attempt_states']['committed']==1 and usage['attempt_states']['interrupted']==1
assert usage['reported_tokens']['total_tokens']=='5' and usage['costs']['states']['unconfigured']==2
assert usage_summary(s,source='all')['calls']==1
owned_requests=[];owned_source_requests=[]
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        owned_requests.append(self.path)
        self.send_response(200);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'OK')
    def do_POST(self):
        query=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        owned_source_requests.append((self.path,self.headers.get('Authorization'),query))
        raw=json.dumps({'code':200,'data':{'list':[{'id':'000000000000000000000001','type':'http','url':'https://owned-import.invalid/','body':'private-source-marker'}]}}).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
asset={'id':'owned-lab','name':'Installed owned lab','url':f'http://127.0.0.1:{server.server_port}/','type':'web','revision':1}
task={'id':'native-engine','name':'Installed approved task','status':'pending','asset_ids':[asset['id']],
      'scope_snapshot':[asset],'checks':['security_headers'],'tool_contracts':contracts_for(['security_headers']),
      'created_at':time.time(),'workers':1,'planner':'rules','goal':'Owned validation','done':0,'errors':0}
s.put_many([('assets',asset),('tasks',task),*[('coverage',row) for row in planned_slots(task)]])
engine=Engine(s,allow_private=True,policy=ExecutionPolicy(request_retries=0))
try:
    assert not owned_requests
    try:
        PostgresLease(os.environ['AEGIS_POSTGRES_DSN'],'owned_transfer')
        raise AssertionError('Duplicate owner accepted')
    except WorkspaceBusy:pass
    blocked=Path(sys.argv[1]).parent/'blocked'/'aegis.db'
    try:
        postgres_to_sqlite(os.environ['AEGIS_POSTGRES_DSN'],'owned_transfer',blocked)
        raise AssertionError('Active owner export accepted')
    except WorkspaceBusy:pass
    assert not blocked.exists()
    engine.start(task['id']);deadline=time.monotonic()+8
    while s.get('tasks',task['id'])['status'] not in ('completed','failed','stopped'):
        assert time.monotonic()<deadline
        time.sleep(.02)
    assert s.get('tasks',task['id'])['status']=='completed'
    assert s.count('findings')>0 and s.count('evidence')==s.count('findings')
    assert s.get('coverage','native-engine:owned-lab:security_headers')['status']=='completed'
    assert engine.metrics()['queue_watchdog']['errors']==0
    graph=build_graph(s,'owned-lab','native-engine')
    assert any(edge['relation']=='evidence' for edge in graph['edges']) and owned_requests==['/']
    pool=ExportPool(ExportPolicy());permit=pool.acquire()
    try:
        report=json.loads(b''.join(report_chunks(s,'json','native-engine',permit)))
        assert report['tasks'][0]['status']=='completed' and report['coverage'][0]['status']=='completed'
        assert len(report['findings'])==s.count('findings') and len(report['evidence'])==len(report['findings'])
        assert len(report['traffic'])==1 and report['finding_history']
        assert b'remediation' in b''.join(report_chunks(s,'csv','native-engine',permit))
        assert 'Installed approved task' in b''.join(report_chunks(s,'markdown','native-engine',permit)).decode()
    finally:permit.finish('completed')
    assert pool.metrics()['active']==0 and owned_requests==['/']
    before_audit=s.audit_integrity()
    verified=AuditReview(s).run(before_audit['checkpoint'])
    assert verified['status']=='verified' and verified['checkpoint']==before_audit['checkpoint']
    assert verified['checkpoint_compared'] and s.audit_integrity()==before_audit
    os.environ['OWNED_INSTALL_SENTRY_TOKEN']='owned-installed-source-secret'
    sources=Sources(s,threading.Event(),[{'id':'owned','url':f'http://127.0.0.1:{server.server_port}',
        'token_env':'OWNED_INSTALL_SENTRY_TOKEN','allow_private':True,'lab_http':True,'project':'owned'}])
    plan=sources.collect(PageInput(connection_id='owned'),u['id']);task_count=s.count('tasks')
    raw=json.dumps(s.get('import_previews',plan['id']))
    assert 'private-source-marker' not in raw and 'owned-installed-source-secret' not in raw
    decision=imports.ApplyInput(selected=['000000000000000000000001'],authorized=True)
    result=imports.apply(s,plan['id'],decision,u['id'])
    assert result['created']==result['linked']==1 and imports.apply(s,plan['id'],decision,u['id'])==result
    old_asset=s.get('assets',result['items'][0]['asset_id'])
    changed=imports.preview(s,imports.PreviewInput(source_key='owned',export=json.dumps({'_id':'000000000000000000000001','type':'http','url':'https://owned-import-changed.invalid/'})),u['id'])
    updated=imports.apply(s,changed['id'],decision,u['id'])
    assert updated['source_changed']==updated['created']==1 and s.count('asset_source_history')==1
    assert s.get('assets',old_asset['id'])==old_asset and s.count('tasks')==task_count
    assert owned_requests==['/'] and len(owned_source_requests)==1
    assert owned_source_requests[0][0]=='/api/assets/asset' and owned_source_requests[0][1]=='Bearer owned-installed-source-secret'
    assert owned_source_requests[0][2]['pageIndex']==1 and owned_source_requests[0][2]['pageSize']==50
finally:
    engine.shutdown();server.shutdown();server.server_close();thread.join(timeout=2)
assert owned_requests==['/']
retired=PostgresStore(os.environ['AEGIS_POSTGRES_DSN'],'owned_transfer');lost=retired.acquire_runtime()
try:
    with connect(os.environ['AEGIS_POSTGRES_DSN']) as db:
        identity=db.execute('SELECT backend_start FROM pg_stat_activity WHERE pid=%s',(lost.pid,)).fetchone()
        assert identity['backend_start']==lost.backend_start
        assert db.execute('SELECT pg_terminate_backend(%s) AS killed',(lost.pid,)).fetchone()['killed']
    replacement=PostgresStore(os.environ['AEGIS_POSTGRES_DSN'],'owned_transfer')
    with replacement.acquire_runtime():
        try:
            retired.put('notes',{'id':'stale-owner','title':'Must refuse'})
            raise AssertionError('Stale write accepted')
        except WorkspaceBusy:pass
        assert replacement.get('notes','stale-owner') is None
        replacement.event(None,'설치본 소유권 교체 확인')
finally:lost.close()
s=PostgresStore(os.environ['AEGIS_POSTGRES_DSN'],'owned_transfer')
s.session('owned-native-export-cookie',time.time()+300,u['id']);assert s.valid_session('owned-native-export-cookie')
with s.transaction() as db:manifest=postgres_manifest(db)
print(json.dumps({'module':sys.modules[s.__class__.__module__].__file__,'manifest':manifest,'audit':s.audit_integrity(),'usage':usage,'owned_lab_requests':len(owned_requests),'owned_source_requests':len(owned_source_requests)}))
''',forward_proof],'installed native PostgreSQL store'))
            with socket_module.socket() as listener:
                listener.bind(('127.0.0.1',0));native_port=listener.getsockname()[1]
            native_env={**environment,'AEGIS_STORAGE_BACKEND':'postgres','AEGIS_POSTGRES_SCHEMA':'owned_transfer',
                        'AEGIS_DATA_DIR':str(temporary/'unused-sqlite'),'AEGIS_HOST':'127.0.0.1','AEGIS_PORT':str(native_port)}
            with (temporary/'native-server.log').open('w') as log:
                process=subprocess.Popen([str(python),'-I','-m','aegis'],cwd=temporary,env=native_env,stdout=log,stderr=subprocess.STDOUT)
                base='http://127.0.0.1:'+str(native_port)
                native_cookies=CookieJar()
                native_client=build_opener(ProxyHandler({}),HTTPCookieProcessor(native_cookies))
                def native_http(path,body=None,expected=200,method=None):
                    headers={'Content-Type':'application/json'} if body is not None else {}
                    request=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
                    try:response=native_client.open(request,timeout=3)
                    except HTTPError as error:response=error
                    with response:
                        if response.status!=expected:raise RuntimeError('Installed native HTTP validation failed')
                        assert response.headers['Cache-Control']=='no-store'
                        return json.loads(response.read())
                try:
                    deadline=time.monotonic()+15
                    while True:
                        if process.poll() is not None:raise RuntimeError('Installed native service exited')
                        try:assert native_http('/api/health')['status']=='ok';break
                        except (URLError,TimeoutError):
                            if time.monotonic()>=deadline:raise RuntimeError('Installed native startup timed out')
                            time.sleep(.05)
                    native_http('/api/assets',expected=401)
                    assert native_http('/api/auth/login',{'username':'admin','password':'owned-installed-transfer-password'})['user']['role']=='operator'
                    assert native_http('/api/settings')['storage']=='postgres'
                    assert native_http('/api/overview')['stats']['covered_assets']==1
                    native_http('/api/users',expected=403)
                    assert native_http('/api/assignees')['total']==1
                    note=native_http('/api/notes',{'title':'Native HTTP note','content':'Owned server'})
                    native_http('/api/notes/'+note['id'],method='DELETE')
                    assert native_http('/api/graph?asset_id=owned-lab&task_id=native-engine')['edges']
                    report=native_http('/api/reports/export?format=json&task_id=native-engine')
                    assert report['coverage'][0]['status']=='completed' and report['evidence']
                    message=native_http('/api/tasks/native-engine/messages',{'content':'저장된 검증 요약'})
                    assert message['provenance']['citations']
                    assets=native_http('/api/records/assets')['items']
                    imported=next(item for item in assets if item['url']=='https://owned-import-changed.invalid/')
                    pending=native_http('/api/tasks',{'name':'Installed native HTTP pending','asset_ids':[imported['id']],'checks':['security_headers']})
                    assert pending['status']=='pending'
                    assert native_http('/api/runtime')['queue_watchdog']['errors']==0
                    archive=temporary/'native-online.zip'
                    backup=json.loads(run([installation/'bin'/'aegis-backup','--output',archive],'installed live PostgreSQL backup',env=native_env))
                    assert archive.stat().st_mode & 0o777==0o600 and backup['omitted_sessions']==2
                    backup_checkpoint=temporary/'backup-checkpoint.json'
                    backup_checkpoint.write_text(json.dumps(backup['audit']['checkpoint']));backup_checkpoint.chmod(0o600)
                    checked=json.loads(run([installation/'bin'/'aegis-restore','--source',archive,'--check-only','--checkpoint',backup_checkpoint],
                        'installed archive check without DB',env={**native_env,'AEGIS_POSTGRES_DSN':''}))
                    assert checked['manifest']==backup['manifest']
                    restored=json.loads(run([installation/'bin'/'aegis-restore','--source',archive,'--schema','owned_backup','--checkpoint',backup_checkpoint],
                        'installed fresh-schema native restore',env=native_env))
                    assert restored['audit']==backup['audit'] and restored['sessions_revoked'] and restored['existing_schema_preserved']
                    backup_cookie=next(cookie.value for cookie in native_cookies if cookie.name=='aegis_session')
                    native_http('/api/assets')
                    native_http('/api/auth/logout',method='POST')
                    native_http('/api/assets',expected=401)
                finally:
                    if process.poll() is None:process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5);raise RuntimeError('Installed native service shutdown timed out')
                assert process.returncode in (0,-15,143) and not (temporary/'unused-sqlite').exists()
            run([python,'-I','-c','''
import os,json,sys
from aegis.postgres_store import PostgresStore
from aegis.postgres_transfer import postgres_manifest
source=PostgresStore(os.environ['AEGIS_POSTGRES_DSN'],'owned_transfer')
copy=PostgresStore(os.environ['AEGIS_POSTGRES_DSN'],'owned_backup')
assert source.valid_session('owned-native-export-cookie') and not copy.valid_session('owned-native-export-cookie')
assert not copy.valid_session(sys.argv[1]) and copy.user(username='admin')==source.user(username='admin')
assert copy.get('tasks',sys.argv[2])['status']=='pending'
assert copy.audit_integrity()['checkpoint']==json.loads(sys.argv[3])
''',backup_cookie,pending['id'],json.dumps(backup['audit']['checkpoint'])],'installed restored native credentials and pending state')
            with socket_module.socket() as listener:
                listener.bind(('127.0.0.1',0));backup_port=listener.getsockname()[1]
            backup_env={**native_env,'AEGIS_POSTGRES_SCHEMA':'owned_backup','AEGIS_PORT':str(backup_port),'AEGIS_DATA_DIR':str(temporary/'unused-backup')}
            with (temporary/'backup-server.log').open('w') as log:
                process=subprocess.Popen([str(python),'-I','-m','aegis'],cwd=temporary,env=backup_env,stdout=log,stderr=subprocess.STDOUT)
                backup_base='http://127.0.0.1:'+str(backup_port)
                backup_client=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
                def backup_http(path,body=None,expected=200,headers=None):
                    request_headers=dict(headers or {})
                    if body is not None:request_headers['Content-Type']='application/json'
                    request=Request(backup_base+path,data=json.dumps(body).encode() if body is not None else None,headers=request_headers)
                    try:response=backup_client.open(request,timeout=3)
                    except HTTPError as error:response=error
                    with response:
                        if response.status!=expected:raise RuntimeError('Installed native backup HTTP validation failed')
                        return json.loads(response.read())
                try:
                    deadline=time.monotonic()+15
                    while True:
                        if process.poll() is not None:raise RuntimeError('Installed restored native service exited')
                        try:assert backup_http('/api/health')['status']=='ok';break
                        except (URLError,TimeoutError):
                            if time.monotonic()>=deadline:raise RuntimeError('Installed restored native startup timed out')
                            time.sleep(.05)
                    backup_http('/api/assets',expected=401,headers={'Cookie':'aegis_session='+backup_cookie})
                    backup_http('/api/auth/login',{'username':'admin','password':'owned-installed-transfer-password'})
                    assert backup_http('/api/settings')['storage']=='postgres'
                    assert backup_http('/api/tasks/'+pending['id'])['task']['status']=='pending'
                    assert backup_http('/api/reports/export?format=json&task_id=native-engine')['evidence']
                    assert backup_http('/api/graph?asset_id=owned-lab&task_id=native-engine')['edges']
                finally:
                    if process.poll() is None:process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5);raise RuntimeError('Installed restored native shutdown timed out')
                assert process.returncode in (0,-15,143) and not (temporary/'unused-backup').exists()
            final_native=json.loads(run([python,'-I','-c',"import json,os;from aegis.postgres_store import PostgresStore;from aegis.postgres_transfer import postgres_manifest;s=PostgresStore(os.environ['AEGIS_POSTGRES_DSN'],'owned_transfer');\nwith s.transaction() as db: manifest=postgres_manifest(db)\nprint(json.dumps({'manifest':manifest,'audit':s.audit_integrity()}))"],'installed native HTTP persisted snapshot'))
            native.update(final_native)
            reader_env={**environment,'AEGIS_STORAGE_BACKEND':'postgres','AEGIS_POSTGRES_SCHEMA':'owned_transfer',
                        'AEGIS_DATA_DIR':str(temporary/'unused-readers')}
            requests=[{'jsonrpc':'2.0','id':1,'method':'initialize'},
                      {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'get_task','arguments':{'id':'native-engine'}}},
                      {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'run_command','arguments':{'command':'must refuse'}}}]
            replies=[json.loads(line) for line in run([python,'-I','-m','aegis.mcp'],'installed native MCP stdio',env=reader_env,
                      input='\n'.join(json.dumps(item) for item in requests)+'\n').splitlines()]
            assert replies[0]['result']['protocolVersion']=='2025-03-26'
            detail=json.loads(replies[1]['result']['content'][0]['text'])
            assert detail['task']['status']=='completed' and detail['coverage'][0]['status']=='completed'
            assert replies[2]['result']['isError'] and not (temporary/'unused-readers').exists()
            checkpoint=temporary/'native-checkpoint.json'
            verified=json.loads(run([python,'-I','-m','aegis.cli.audit','--output',checkpoint],'installed native audit CLI',env=reader_env))
            assert verified==native['audit'] and checkpoint.stat().st_mode & 0o777==0o600
            assert json.loads(run([python,'-I','-m','aegis.cli.audit','--checkpoint',checkpoint],'installed native audit prefix',env=reader_env))==verified
            dump=temporary/'owned.dump'
            run([binaries['pg_dump'],'--format=custom','--schema','owned_transfer','--file',dump,'postgres'],'real pg_dump');dump.chmod(0o600)
            run([binaries['createdb'],'owned_restore'],'empty restore database')
            run([binaries['pg_restore'],'--exit-on-error','--dbname','owned_restore',dump],'real pg_restore')
            environment['AEGIS_POSTGRES_DSN']=f'host={socket} port=55439 dbname=owned_restore'
            output=temporary/'returned'/'aegis.db'
            reverse=json.loads(run([cli,'postgres-to-sqlite','--schema','owned_transfer','--output',output],'installed reverse transfer'))
            assert native['manifest']==reverse['manifest'] and native['audit']==reverse['audit'] and forward['sessions_revoked']==1
            assert reverse['omitted_session_count']==1 and reverse['source_sessions_preserved']
            run([python,'-I','-c',"import os;from aegis.postgres_store import PostgresStore;s=PostgresStore(os.environ['AEGIS_POSTGRES_DSN'],'owned_transfer');assert s.valid_session('owned-native-export-cookie')"],'source session survives return')
            run([python,'-I','-c','''
import sys
from aegis.store import Store
from aegis.auth import password_hash
s=Store(sys.argv[1]);u=s.user(username='admin')
assert u['password_hash']==password_hash('owned-installed-transfer-password',u['salt'])
assert not s.valid_session('owned-old-cookie')
assert not s.valid_session('owned-native-export-cookie')
assert s.get('notes','proof')['amount']=='0.000000000000001'
assert s.get('notes','native')['amount']=='0.000000000000001'
assert u['role']=='operator' and u['name']=='합성 PostgreSQL 관리자'
s.event(None,'반환 후 이벤트');assert s.audit_integrity()['valid']
''',output],'installed returned credentials, record and audit continuation')
            with socket_module.socket() as listener:
                listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
            server_env={**environment,'AEGIS_DATA_DIR':str(output.parent),'AEGIS_HOST':'127.0.0.1','AEGIS_PORT':str(port)}
            with (temporary/'returned-server.log').open('w') as log:
                process=subprocess.Popen([str(python),'-I','-m','aegis'],cwd=temporary,env=server_env,stdout=log,stderr=subprocess.STDOUT)
                base='http://127.0.0.1:'+str(port)
                authenticated=build_opener(ProxyHandler({}),HTTPCookieProcessor(CookieJar()))
                def http(path,body=None,expected=200,headers=None,opener=authenticated):
                    request_headers=dict(headers or {})
                    if body is not None:request_headers['Content-Type']='application/json'
                    request=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=request_headers)
                    try:response=opener.open(request,timeout=3)
                    except HTTPError as error:response=error
                    with response:
                        if response.status!=expected:raise RuntimeError('Installed returned service HTTP validation failed')
                        return json.loads(response.read())
                try:
                    deadline=time.monotonic()+15
                    while True:
                        if process.poll() is not None:raise RuntimeError('Installed returned service exited')
                        try:
                            assert http('/api/health')['status']=='ok';break
                        except (URLError,TimeoutError):
                            if time.monotonic()>=deadline:raise RuntimeError('Installed returned service startup timed out')
                            time.sleep(.05)
                    http('/api/assets',expected=401,headers={'Cookie':'aegis_session=owned-native-export-cookie'})
                    http('/api/auth/login',{'username':'admin','password':'owned-installed-transfer-password'})
                    assert http('/api/records/notes')['total']==2
                    graph=http('/api/graph?asset_id=owned-lab&task_id=native-engine')
                    assert any(edge['relation']=='evidence' for edge in graph['edges'])
                finally:
                    if process.poll() is None:process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5);raise RuntimeError('Installed returned service shutdown timed out')
                assert process.returncode in (0,-15,143)
            print(json.dumps({'valid':True,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
                'postgres_version':run([binaries['pg_ctl'],'--version'],'version').strip(),
                'installed_origin':origin['module'],'installed_native_origin':native['module'],'manifest':native['manifest'],'audit':native['audit'],
                'checks':['locked optional dependency','server fsync enabled','installed native initializer under a nonsuperuser role with database CREATE','fresh native HTTP first setup token, authentication, note and audit without SQLite','atomic offline transfer','installed native Store reads and writes','native security change session revocation','native attempt lifecycle and standalone recovery','native exact metadata usage summary','installed standalone native engine approved owned lab execution','native readonly provenance graph','native JSON CSV Markdown report streams','native bounded readonly audit review','native owned source read and atomic import retry/history','native duplicate runtime owner and active export refusal','actual owned backend termination and stale write refusal','real pg_dump/pg_restore',
                          'installed native PostgreSQL HTTP lifecycle, auth, queries, reports and pending plan','installed live native backup and no-DB archive check','installed atomic native fresh-schema restore and restored HTTP login, pending plan, reports and graph','installed native MCP stdio and audit checkpoint CLI','installed SQLite return','returned sessions omitted and source preserved','preserved password hashes and exact record','audit continuation','installed returned HTTP server login, records and graph'],
                'target_requests':native['owned_lab_requests'],'owned_lab_requests':native['owned_lab_requests'],
                'owned_source_requests':native['owned_source_requests'],'external_source_requests':0,
                'external_target_requests':0,'service_postgres_backend_enabled':True}))
        finally:
            run([binaries['pg_ctl'],'-D',data,'-w','-m','fast','stop'],'owned PostgreSQL stop')


if __name__=='__main__':main()
