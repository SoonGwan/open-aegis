"""Rehearse installed transfer CLI using an owned disposable PostgreSQL cluster."""
import argparse
import hashlib
import json
import os
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
        def run(command,label,env=None):
            result=subprocess.run([str(item) for item in command],cwd=temporary,env=env or environment,capture_output=True,text=True,timeout=180)
            if result.returncode:raise RuntimeError(label+' failed')
            return result.stdout
        run([python,'-m','pip','install','-r',root/'requirements.lock','-r',root/'requirements-postgres.lock'],'locked installation')
        run([python,'-m','pip','install','--no-deps',wheel],'wheel installation');run([python,'-m','pip','check'],'pip check')
        run([cli,'--help'],'transfer entry point')
        run([binaries['initdb'],'-D',data,'--auth=trust','--no-locale','--encoding=UTF8'],'initdb')
        run([binaries['pg_ctl'],'-D',data,'-l',temporary/'server.log','-o',f"-c listen_addresses='' -k {socket} -p 55439",'-w','start'],'owned PostgreSQL start')
        environment.update(AEGIS_POSTGRES_DSN=f'host={socket} port=55439 dbname=postgres',PGHOST=str(socket),PGPORT='55439')
        try:
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
owned_requests=[]
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        owned_requests.append(self.path)
        self.send_response(200);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'OK')
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
with s.transaction() as db:manifest=postgres_manifest(db)
print(json.dumps({'module':sys.modules[s.__class__.__module__].__file__,'manifest':manifest,'audit':s.audit_integrity(),'usage':usage,'owned_lab_requests':len(owned_requests)}))
''',forward_proof],'installed native PostgreSQL store'))
            dump=temporary/'owned.dump'
            run([binaries['pg_dump'],'--format=custom','--schema','owned_transfer','--file',dump,'postgres'],'real pg_dump');dump.chmod(0o600)
            run([binaries['createdb'],'owned_restore'],'empty restore database')
            run([binaries['pg_restore'],'--exit-on-error','--dbname','owned_restore',dump],'real pg_restore')
            environment['AEGIS_POSTGRES_DSN']=f'host={socket} port=55439 dbname=owned_restore'
            output=temporary/'returned'/'aegis.db'
            reverse=json.loads(run([cli,'postgres-to-sqlite','--schema','owned_transfer','--output',output],'installed reverse transfer'))
            assert native['manifest']==reverse['manifest'] and native['audit']==reverse['audit'] and forward['sessions_revoked']==1
            run([python,'-I','-c','''
import sys
from aegis.store import Store
from aegis.auth import password_hash
s=Store(sys.argv[1]);u=s.user(username='admin')
assert u['password_hash']==password_hash('owned-installed-transfer-password',u['salt'])
assert not s.valid_session('owned-old-cookie')
assert s.get('notes','proof')['amount']=='0.000000000000001'
assert s.get('notes','native')['amount']=='0.000000000000001'
assert u['role']=='operator' and u['name']=='합성 PostgreSQL 관리자'
s.event(None,'반환 후 이벤트');assert s.audit_integrity()['valid']
''',output],'installed returned credentials, record and audit continuation')
            print(json.dumps({'valid':True,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
                'postgres_version':run([binaries['pg_ctl'],'--version'],'version').strip(),
                'installed_origin':origin['module'],'installed_native_origin':native['module'],'manifest':native['manifest'],'audit':native['audit'],
                'checks':['locked optional dependency','server fsync enabled','installed six-command package','atomic offline transfer','installed native Store reads and writes','native security change session revocation','native attempt lifecycle and standalone recovery','native exact metadata usage summary','installed standalone native engine approved owned lab execution','native duplicate runtime owner and active export refusal','actual owned backend termination and stale write refusal','real pg_dump/pg_restore',
                          'installed SQLite return','revoked old sessions','preserved password hashes and exact record','audit continuation'],
                'target_requests':native['owned_lab_requests'],'owned_lab_requests':native['owned_lab_requests'],
                'external_target_requests':0,'service_postgres_backend_enabled':False}))
        finally:
            run([binaries['pg_ctl'],'-D',data,'-w','-m','fast','stop'],'owned PostgreSQL stop')


if __name__=='__main__':main()
