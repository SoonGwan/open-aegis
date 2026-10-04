"""Rehearse two installed artifacts, failed startup and recovery on owned local data."""
import argparse
from contextlib import contextmanager
import hashlib
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import re
import signal
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
from aegis.store import Store
workspace, fd, marker, fail = sys.argv[1:]
app = create_app(workspace, allow_private=False)
original = app.router.lifespan_context
@asynccontextmanager
async def lifespan(application):
    async with original(application):
        if fail == 'yes':
            Store(Path(workspace) / 'aegis.db').put('notes', {
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
    args = parser.parse_args()
    old_wheel = args.old_wheel.resolve(strict=True)
    new_wheel = args.new_wheel.resolve(strict=True)
    web = args.web_dir.resolve(strict=True)
    lock = args.runtime_lock.resolve(strict=True)
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    if sha(old_wheel) == sha(new_wheel):
        parser.error('Provide two different wheel artifacts.')
    if not (web / 'index.html').is_file():
        parser.error('Build the frontend first.')
    for revision in (args.old_revision, args.new_revision):
        if not re.fullmatch(r'[0-9a-f]{40}', revision):
            parser.error('Revisions must be full lowercase Git SHAs.')
    environment = {key: value for key, value in os.environ.items()
                   if key not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV')
                   and not key.startswith('AEGIS_')}
    with tempfile.TemporaryDirectory(prefix='aegis-transition-') as temporary:
        root = Path(temporary)

        def run(command, label):
            result = subprocess.run([str(item) for item in command], cwd=root,
                                    env=environment, capture_output=True, text=True, timeout=180)
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
            run([python, '-m', 'pip', 'install', '--no-index', '--no-deps', wheel], name + ' wheel')
            run([python, '-m', 'pip', 'check'], name + ' dependency check')
            origins[name] = json.loads(run([python, '-I', '-c',
                'import aegis,json,sys; from pathlib import Path; '
                'assert Path(aegis.__file__).is_relative_to(Path(sys.prefix)); '
                'print(json.dumps({"module":aegis.__file__}))'], name + ' installed origin'))
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
            run([release, 'create', '--wheel', wheel, '--web', web, '--lock', lock,
                 '--output', bundle, '--private-key', private, '--revision', revision], name + ' signing')
            manifests[name] = json.loads(run([release, 'verify', '--bundle', bundle,
                                             '--public-key', public], name + ' verification'))
            assert sha(bundle / manifests[name]['wheel']) == sha(wheel)
        # Signing identity is deliberately rehearsal-only; no retained secret key.
        private.unlink()
        workspace = root / 'workspace'
        jar = CookieJar()
        authenticated = build_opener(ProxyHandler({}), HTTPCookieProcessor(jar))
        anonymous = build_opener(ProxyHandler({}))
        stages = {}

        @contextmanager
        def server(name, stage, fail=False):
            listener = socket.socket()
            listener.bind(('127.0.0.1', 0))
            base = f'http://127.0.0.1:{listener.getsockname()[1]}'
            marker = root / (stage + '.shutdown')
            env = dict(environment, AEGIS_WEB_DIR=str(root / (name + '-release') / 'web'))
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
                run([installs[name] / 'bin' / 'python', '-I', '-c',
                     'from aegis.maintenance import WorkspaceLease; import sys; '
                     'lease=WorkspaceLease(sys.argv[1]); lease.close()', workspace], stage + ' lease release')
                stages[stage] = {'artifact':name, 'exit_code':process.returncode,
                                 'injected_startup_failure':fail, 'lease_released':True}

        credentials = {'username':'admin', 'password':'owned-transition-fixture-password-only'}
        with server('old', 'initial') as request:
            request('/api/auth/setup', credentials)
            asset = request('/api/assets', {'name':'Owned transition fixture',
                'url':'https://transition-fixture.invalid/', 'authorized':True})
            task = request('/api/tasks', {'name':'Pending, no execution', 'asset_ids':[asset['id']]})
            assert task['status'] == 'pending'
            note = request('/api/notes', {'title':'Before update', 'content':'Retain this record'})
            assert request('/api/runtime')['requests']['requests'] == 0
        preflight = root / 'preflight'
        receipt = json.loads(run([release, 'prepare', '--bundle', root / 'new-release',
            '--public-key', public, '--database', workspace / 'aegis.db', '--output', preflight], 'preflight'))
        assert receipt['installed'] is False
        assert receipt['backup_metadata']['records']['tasks'] == 1
        with server('new', 'candidate') as request:
            assert request('/api/assets')[0]['id'] == asset['id']
            changed = request('/api/notes', {'title':'Candidate write', 'content':'Lost on rollback'})
            html = request('/')
            bundles = re.findall(r'(?:src|href)="(/assets/[^"\s]+)"', html)
            assert bundles and any(path.endswith('.js') for path in bundles)
            for path in bundles:
                assert request(path)
            assert request('/api/audit/verify', {})['status'] == 'verified'
        with server('new', 'failed-startup', fail=True):
            pass
        inspect = json.loads(run([installs['new'] / 'bin' / 'python', '-I', '-c',
            'from aegis.store import Store; import json,sys; '
            's=Store(sys.argv[1]); print(json.dumps({"fault_write":'
            's.get("notes","startup-fault-write") is not None}))', workspace / 'aegis.db'], 'fault persistence'))
        assert inspect['fault_write'], 'Failure must occur after an actual DB write.'
        restored = json.loads(run([installs['old'] / 'bin' / 'aegis-restore', '--source',
            preflight / 'before-update.db', '--destination', workspace / 'aegis.db'], 'old runtime restore'))
        assert restored['sessions_revoked'] and Path(restored['rollback']).is_file()
        # Re-check retained signed payloads before selecting the old process/UI.
        run([release, 'verify', '--bundle', root / 'old-release', '--public-key', public], 'retained old release')
        with server('old', 'recovered') as request:
            request('/api/assets', expected=401)
            request('/api/auth/login', credentials)
            assert request('/api/assets')[0]['id'] == asset['id']
            assert request('/api/tasks')[0]['id'] == task['id']
            notes = request('/api/notes')
            assert {item['id'] for item in notes} == {note['id']}
            assert changed['id'] not in {item['id'] for item in notes}
            assert 'startup-fault-write' not in {item['id'] for item in notes}
            assert request('/') == (root / 'old-release' / 'web' / 'index.html').read_text()
            for path in bundles:
                assert request(path)
            assert request('/api/audit/verify', {})['status'] == 'verified'
            assert request('/api/runtime')['requests']['requests'] == 0
        print(json.dumps({'valid':True, 'target_requests':0, 'rehearsal_only':True,
            'artifacts':{name:{'sha256':sha(wheel), 'version':manifests[name]['version'],
                'revision':manifests[name]['revision'], 'installed_origin':origins[name]['module']}
                for name, wheel in (('old', old_wheel), ('new', new_wheel))},
            'same_version':manifests['old']['version'] == manifests['new']['version'],
            'shared_ui_input':True, 'shared_runtime_lock':True,
            'stages':stages, 'private_key_removed':not private.exists(),
            'checks':['two independent installed environments outside checkout',
                'ephemeral-key signed old/new payload verification', 'old service creates owned records',
                'offline preflight backup', 'new service reads old records and writes a note',
                'startup fault after actual DB write and lease acquisition',
                'failed process exits and releases lease', 'old installed restore revokes sessions',
                'old process and retained UI restart', 'old cookie rejected and password login succeeds',
                'preflight records retained and both later writes removed',
                'audit verification, zero target requests, clean shutdown and lease release']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
