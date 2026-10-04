"""Rehearse two installed artifacts, failed startup and recovery on owned local data."""
import argparse
from contextlib import contextmanager, ExitStack
import hashlib
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import re
import signal
import shutil
import socket
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPCookieProcessor, ProxyHandler
import venv


SERVER = '''
import socket, sys
from pathlib import Path
from contextlib import asynccontextmanager
from aegis.app import create_app
from aegis.__main__ import AegisServer
workspace, fd, marker, fail = sys.argv[1:]
app = create_app(workspace, allow_private=False)
original = app.router.lifespan_context
@asynccontextmanager
async def lifespan(application):
    async with original(application):
        if fail == 'yes':
            app.state.store.put('notes', {
                'id':'startup-fault-write', 'title':'Synthetic failed startup'})
            Path(marker + '.injected').write_text('after original startup, before readiness')
            raise RuntimeError('Owned rehearsal startup fault')
        try:
            yield
        finally:
            Path(marker + '.exiting').write_text('lifespan exiting')
    Path(marker).write_text('original lifespan exited')
app.router.lifespan_context = lifespan
AegisServer(app, host='127.0.0.1', port=0, access_log=False,
    log_level='warning', timeout_graceful_shutdown=5).run(
    sockets=[socket.socket(fileno=int(fd))])
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('old-wheel', 'new-wheel', 'web-dir', 'runtime-lock'):
        parser.add_argument('--' + flag, required=True, type=Path)
    for flag in ('old-revision', 'new-revision'):
        parser.add_argument('--' + flag, required=True)
    parser.add_argument('--backend',choices=['sqlite','postgres'],default='sqlite')
    parser.add_argument('--old-web-dir',type=Path)
    parser.add_argument('--postgres-lock',type=Path)
    args = parser.parse_args()
    old_wheel = args.old_wheel.resolve(strict=True)
    new_wheel = args.new_wheel.resolve(strict=True)
    web = args.web_dir.resolve(strict=True)
    lock = args.runtime_lock.resolve(strict=True)
    old_web=(args.old_web_dir or web).resolve(strict=True)
    postgres_lock=args.postgres_lock.resolve(strict=True) if args.postgres_lock else None
    binaries={name:shutil.which(name) for name in ('initdb','pg_ctl')}
    if args.backend=='postgres' and (not postgres_lock or not all(binaries.values())):
        parser.error('PostgreSQL transition requires --postgres-lock and owned server binaries.')
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    if sha(old_wheel) == sha(new_wheel):
        parser.error('Provide two different wheel artifacts.')
    if not all((folder/'index.html').is_file() for folder in (web,old_web)):
        parser.error('Build the frontend first.')
    for revision in (args.old_revision, args.new_revision):
        if not re.fullmatch(r'[0-9a-f]{40}', revision):
            parser.error('Revisions must be full lowercase Git SHAs.')
    environment = {key: value for key, value in os.environ.items()
                   if key not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV')
                   and not key.startswith('AEGIS_')}
    with tempfile.TemporaryDirectory(prefix='aegis-transition-',dir='/tmp') as temporary, ExitStack() as cleanup:
        root = Path(temporary)

        def run(command, label, *, extra_env=None,input=None):
            result = subprocess.run([str(item) for item in command], cwd=root,
                                    env={**environment,**(extra_env or {})},input=input,capture_output=True, text=True, timeout=180)
            if result.returncode:
                raise RuntimeError(f'{label} failed with exit {result.returncode}')
            return result.stdout

        installs = {}
        origins = {}
        for name, wheel in (('old', old_wheel), ('new', new_wheel)):
            installation = root / name
            venv.EnvBuilder(with_pip=True).create(installation)
            python = installation / 'bin' / 'python'
            run([python, '-m', 'pip', 'install', '-r', lock], name + ' dependencies')
            if args.backend=='postgres':run([python,'-m','pip','install','-r',postgres_lock],name+' PostgreSQL dependencies')
            run([python, '-m', 'pip', 'install', '--no-index', '--no-deps', wheel], name + ' wheel')
            run([python, '-m', 'pip', 'check'], name + ' dependency check')
            origins[name] = json.loads(run([python, '-I', '-c',
                'import aegis,json,sys; from pathlib import Path; '
                'assert Path(aegis.__file__).is_relative_to(Path(sys.prefix)); '
                'print(json.dumps({"module":aegis.__file__,"version":aegis.__version__}))'], name + ' installed origin'))
            installs[name] = installation
        private = root / 'private.pem'
        public = root / 'public.pem'
        run(['openssl', 'genpkey', '-algorithm', 'ED25519', '-out', private], 'ephemeral key')
        private.chmod(0o600)
        run(['openssl', 'pkey', '-in', private, '-pubout', '-out', public], 'public key')
        release = installs['new'] / 'bin' / 'aegis-release'
        manifests = {}
        for name, wheel, revision in (('old', old_wheel, args.old_revision),
                                      ('new', new_wheel, args.new_revision)):
            bundle = root / (name + '-release')
            create=installs[name]/'bin'/'aegis-release'
            extra=['--postgres-lock',postgres_lock] if args.backend=='postgres' else []
            run([create, 'create', '--wheel', wheel, '--web', old_web if name=='old' else web, '--lock', lock,
                 '--output', bundle, '--private-key', private, '--revision', revision,*extra], name + ' signing')
            manifests[name] = json.loads(run([release, 'verify', '--bundle', bundle,
                                             '--public-key', public], name + ' verification'))
            assert sha(bundle / manifests[name]['wheel']) == sha(wheel)
        # Signing identity is deliberately rehearsal-only; no retained secret key.
        private.unlink()
        workspace = root / 'workspace'
        if args.backend=='postgres':
            cluster=root/'cluster';pg_socket=root/'socket';pg_socket.mkdir(mode=0o700)
            run([binaries['initdb'],'-D',cluster,'--auth=trust','--no-locale','--encoding=UTF8'],'owned initdb')
            run([binaries['pg_ctl'],'-D',cluster,'-l',root/'postgres.log','-o',f"-c listen_addresses='' -k {pg_socket} -p 55439",'-w','start'],'owned PostgreSQL start')
            cleanup.callback(run,[binaries['pg_ctl'],'-D',cluster,'-w','-m','fast','stop'],'owned PostgreSQL stop')
            environment.update(AEGIS_STORAGE_BACKEND='postgres',AEGIS_POSTGRES_DSN=f'host={pg_socket} port=55439 dbname=postgres',AEGIS_POSTGRES_SCHEMA='owned_transition')
            run([installs['old']/'bin'/'aegis-init-postgres'],'old installed native initialization')
        jar = CookieJar()
        authenticated = build_opener(ProxyHandler({}), HTTPCookieProcessor(jar))
        anonymous = build_opener(ProxyHandler({}))
        stages = {}

        @contextmanager
        def server(name, stage, fail=False, budget=None):
            listener = socket.socket()
            listener.bind(('127.0.0.1', 0))
            base = f'http://127.0.0.1:{listener.getsockname()[1]}'
            marker = root / (stage + '.shutdown')
            budget=budget if budget is not None else 12 if name=='new' else 24
            env = dict(environment, AEGIS_WEB_DIR=str(root / (name + '-release') / 'web'),AEGIS_REQUEST_BUDGET=str(budget),AEGIS_DATA_DIR=str(workspace))
            with (root / (stage + '.log')).open('wb') as log:
                process = subprocess.Popen([str(installs[name] / 'bin' / 'python'), '-I', '-c',
                    SERVER, str(workspace), str(listener.fileno()), str(marker),
                    'yes' if fail else 'no'], cwd=root, env=env,
                    pass_fds=(listener.fileno(),), stdout=log, stderr=log)
                listener.close()

                def request(path, body=None, expected=200, opener=authenticated):
                    data = None if body is None else json.dumps(body).encode()
                    req = Request(base + path, data=data,
                                  headers={} if body is None else {'Content-Type':'application/json'})
                    try:
                        response = opener.open(req, timeout=3)
                    except HTTPError as exc:
                        response = exc
                    with response:
                        assert response.code == expected, f'{stage}: {path} HTTP {response.code}'
                        payload = response.read()
                        return json.loads(payload) if 'application/json' in response.headers.get(
                            'Content-Type', '') else payload.decode()

                try:
                    if fail:
                        process.wait(timeout=30)
                        assert process.returncode != 0, 'Injected startup must fail.'
                        assert Path(str(marker) + '.injected').is_file()
                        try:
                            anonymous.open(base + '/api/health', timeout=1)
                        except URLError:
                            pass
                        else:
                            raise AssertionError('Failed process is still serving HTTP.')
                    else:
                        deadline = time.monotonic() + 30
                        while True:
                            assert process.poll() is None, 'Server exited before readiness.'
                            try:
                                assert request('/api/health', opener=anonymous)['status'] == 'ok'
                                break
                            except (URLError, TimeoutError):
                                if time.monotonic() >= deadline:
                                    raise RuntimeError('Server startup timed out.')
                                time.sleep(.05)
                        initialized=json.loads(run([installs[name]/'bin'/'python','-I','-m','aegis.mcp'],stage+' MCP installed version',extra_env=env,
                            input=json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize'})+'\n'))
                        assert initialized['result']['serverInfo']['version']==origins[name]['version']
                    yield request
                finally:
                    if process.poll() is None:
                        process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                        raise RuntimeError('Server did not stop cleanly.')
                if not fail:
                    assert process.returncode in (0, -signal.SIGTERM)
                    assert marker.is_file(), 'Original lifespan cleanup did not complete.'
                if args.backend=='sqlite':run([installs[name] / 'bin' / 'python', '-I', '-c',
                     'from aegis.maintenance import WorkspaceLease; import sys; '
                     'lease=WorkspaceLease(sys.argv[1]); lease.close()', workspace], stage + ' lease release')
                else:
                    run([installs[name]/'bin'/'python','-I','-c',"import os;from aegis.postgres_store import PostgresStore;s=PostgresStore(os.environ['AEGIS_POSTGRES_DSN'],os.environ['AEGIS_POSTGRES_SCHEMA']);\nwith s.acquire_runtime():pass"],stage+' native owner release')
                    assert not workspace.exists(),'Native transition created a SQLite workspace'
                stages[stage] = {'artifact':name, 'exit_code':process.returncode,
                                 'injected_startup_failure':fail, 'lease_released':True}

        credentials = {'username':'admin', 'password':'owned-transition-fixture-password-only'}
        with server('old', 'initial') as request:
            request('/api/auth/setup', credentials)
            initial_cookie=next(cookie.value for cookie in jar if cookie.name=='aegis_session')
            asset = request('/api/assets', {'name':'Owned transition fixture',
                'url':'https://transition-fixture.invalid/', 'authorized':True})
            task = request('/api/tasks', {'name':'Pending, no execution', 'asset_ids':[asset['id']]})
            assert task['status'] == 'pending'
            note = request('/api/notes', {'title':'Before update', 'content':'Retain this record'})
            assert request('/api/runtime')['requests']['requests'] == 0
            assert request('/api/settings')['version']==origins['old']['version']
        preflight = root / 'preflight'
        source_flags=['--backend','sqlite','--database',workspace/'aegis.db'] if args.backend=='sqlite' else ['--backend','postgres','--schema','owned_transition']
        receipt = json.loads(run([release, 'prepare', '--bundle', root / 'new-release',
            '--public-key', public,*source_flags, '--output', preflight], 'preflight'))
        assert receipt['installed'] is False
        if args.backend=='sqlite':assert receipt['backup_metadata']['records']['tasks']==1
        else:assert receipt['backup_metadata']['manifest']['records']['rows']>=3
        with server('new', 'candidate') as request:
            assert request('/api/assets')[0]['id'] == asset['id']
            assert request('/api/settings')['version']==origins['new']['version']
            assert request('/api/runtime')['policy']['request_budget']==12
            request('/api/tasks/'+task['id']+'/approve',{},expected=409)
            assert request('/api/tasks/'+task['id'])['task']['status']=='pending'
            changed = request('/api/notes', {'title':'Candidate write', 'content':'Lost on rollback'})
            candidate_task=request('/api/tasks',{'name':'Candidate pending, no execution','asset_ids':[asset['id']]})
            assert candidate_task['status']=='pending'
            html = request('/')
            assert html==(root/'new-release'/'web'/'index.html').read_text()
            bundles = re.findall(r'(?:src|href)="(/assets/[^"\s]+)"', html)
            assert bundles and any(path.endswith('.js') for path in bundles)
            for path in bundles:
                assert request(path)==(root/'new-release'/'web'/path.lstrip('/')).read_text()
            assert request('/api/audit/verify', {})['status'] == 'verified'
        with server('new','policy-restart',budget=6) as request:
            refusal=request('/api/tasks/'+candidate_task['id']+'/approve',{},expected=409)
            assert '서버 실행 정책이 변경' in refusal['detail']
            assert request('/api/runtime')['policy']['request_budget']==6
            assert request('/api/tasks/'+candidate_task['id'])['task']['status']=='pending'
            assert request('/api/runtime')['requests']['requests']==0
        with server('new', 'failed-startup', fail=True):
            pass
        if args.backend=='sqlite':inspect = json.loads(run([installs['new'] / 'bin' / 'python', '-I', '-c',
            'from aegis.store import Store; import json,sys; '
            's=Store(sys.argv[1]); print(json.dumps({"fault_write":'
            's.get("notes","startup-fault-write") is not None}))', workspace / 'aegis.db'], 'fault persistence'))
        else:inspect=json.loads(run([installs['new']/'bin'/'python','-I','-c',"import os,json;from aegis.postgres_store import PostgresStore;s=PostgresStore(os.environ['AEGIS_POSTGRES_DSN'],os.environ['AEGIS_POSTGRES_SCHEMA']);print(json.dumps({'fault_write':s.get('notes','startup-fault-write') is not None}))"],'native fault persistence'))
        assert inspect['fault_write'], 'Failure must occur after an actual DB write.'
        if args.backend=='sqlite':restored = json.loads(run([installs['old'] / 'bin' / 'aegis-restore', '--source',
            preflight / 'before-update.db', '--destination', workspace / 'aegis.db'], 'old runtime restore'))
        else:
            restored=json.loads(run([installs['old']/'bin'/'aegis-restore','--backend','postgres','--source',preflight/'before-update.zip','--schema','owned_recovered'],'old installed native restore'))
            environment['AEGIS_POSTGRES_SCHEMA']='owned_recovered'
        assert restored['sessions_revoked']
        if args.backend=='sqlite':assert Path(restored['rollback']).is_file()
        # Re-check retained signed payloads before selecting the old process/UI.
        run([release, 'verify', '--bundle', root / 'old-release', '--public-key', public], 'retained old release')
        with server('old', 'recovered') as request:
            request('/api/assets', expected=401)
            request('/api/auth/login', credentials)
            assert request('/api/settings')['version']==origins['old']['version']
            assert request('/api/runtime')['policy']['request_budget']==24
            assert request('/api/assets')[0]['id'] == asset['id']
            assert request('/api/tasks')[0]['id'] == task['id']
            assert {item['id'] for item in request('/api/tasks')}=={task['id']}
            notes = request('/api/notes')
            assert {item['id'] for item in notes} == {note['id']}
            assert changed['id'] not in {item['id'] for item in notes}
            assert 'startup-fault-write' not in {item['id'] for item in notes}
            if args.backend=='postgres':
                run([installs['old']/'bin'/'python','-I','-c',"import os,sys;from aegis.postgres_store import PostgresStore;s=PostgresStore(os.environ['AEGIS_POSTGRES_DSN'],'owned_transition');assert s.valid_session(sys.argv[1]) and s.get('notes',sys.argv[2]) and s.get('notes','startup-fault-write')",initial_cookie,changed['id']],
                    'preserved original native schema and source cookie after copy restore')
            assert request('/') == (root / 'old-release' / 'web' / 'index.html').read_text()
            for path in re.findall(r'(?:src|href)="(/assets/[^"\s]+)"',request('/')):
                assert request(path)==(root/'old-release'/'web'/path.lstrip('/')).read_text()
            assert request('/api/audit/verify', {})['status'] == 'verified'
            assert request('/api/runtime')['requests']['requests'] == 0
        print(json.dumps({'valid':True, 'target_requests':0, 'rehearsal_only':True,
            'artifacts':{name:{'sha256':sha(wheel), 'version':manifests[name]['version'],
                'revision':manifests[name]['revision'], 'installed_origin':origins[name]['module']}
                for name, wheel in (('old', old_wheel), ('new', new_wheel))},
            'same_version':manifests['old']['version'] == manifests['new']['version'],'backend':args.backend,
            'shared_ui_input':old_web==web, 'shared_runtime_lock':True,'changed_execution_budget':True,
            'stages':stages, 'private_key_removed':not private.exists(),
            'checks':['two independent installed environments outside checkout',
                'ephemeral-key signed old/new payload verification', 'old service creates owned records',
                'actual HTTP and MCP artifact versions','changed UI payload and execution budget, old plan approval refusal',
                'offline preflight backup', 'new service reads old records and writes a note',
                'startup fault after actual DB write and lease acquisition',
                'failed process exits and releases lease', 'old installed restore revokes sessions',
                'old process and retained UI restart', 'old cookie rejected and password login succeeds',
                'preflight records retained and both later writes removed',
                'audit verification, zero target requests, clean shutdown and lease release']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
