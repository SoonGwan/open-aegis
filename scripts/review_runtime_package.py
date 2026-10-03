"""Smoke-test an installed wheel and separately built UI with synthetic local data."""
import argparse
from http.cookiejar import CookieJar
import hashlib
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel-dir', required=True, type=Path)
    parser.add_argument('--web-dir', required=True, type=Path)
    parser.add_argument('--runtime-lock', required=True, type=Path)
    args = parser.parse_args()
    wheels = list(args.wheel_dir.resolve(strict=True).glob('open_aegis-*.whl'))
    if len(wheels) != 1:
        raise SystemExit('The wheel directory must contain exactly one Open Aegis wheel.')
    wheel = wheels[0]
    web = args.web_dir.resolve(strict=True)
    if not (web / 'index.html').is_file():
        raise SystemExit('Build the frontend before package review.')
    lock = args.runtime_lock.resolve(strict=True)
    environment = {key: value for key, value in os.environ.items()
                   if key not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV')
                   and not key.startswith('AEGIS_')}
    with tempfile.TemporaryDirectory(prefix='aegis-runtime-review-') as temporary:
        root = Path(temporary)
        installation = root / 'installation'
        venv.EnvBuilder(with_pip=True).create(installation)
        python = installation / 'bin' / 'python'

        def run(command, label):
            result = subprocess.run([str(item) for item in command], cwd=root,
                                    env=environment, capture_output=True, text=True, timeout=180)
            if result.returncode:
                raise RuntimeError(f'{label} failed with exit {result.returncode}')
            return result.stdout

        run([python, '-m', 'pip', 'install', '-r', lock], 'locked runtime installation')
        run([python, '-m', 'pip', 'install', '--no-index', '--no-deps', wheel], 'wheel installation')
        run([python, '-m', 'pip', 'check'], 'dependency check')
        origin = json.loads(run([python, '-I', '-c',
            'import aegis,json,sys; from pathlib import Path; '
            'assert Path(aegis.__file__).is_relative_to(Path(sys.prefix)); '
            'print(json.dumps({"module":aegis.__file__}))'], 'installed package origin'))
        for command in ('backup', 'restore', 'verify-audit', 'replay-policy'):
            run([installation / 'bin' / ('aegis-' + command), '--help'], command + ' entry point')

        environment['AEGIS_WEB_DIR'] = str(web)
        source = root / 'workspace'
        # Hand the child a bound socket, avoiding a free-port lookup/startup race.
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
        server_code = '''
import socket, sys
from pathlib import Path
from contextlib import asynccontextmanager
from aegis.app import create_app
from aegis.__main__ import AegisServer
app = create_app(sys.argv[1], allow_private=False)
original_lifespan = app.router.lifespan_context
@asynccontextmanager
async def reviewed_lifespan(application):
    async with original_lifespan(application):
        yield
    (Path(sys.argv[1]) / 'shutdown-complete').write_text('complete')
app.router.lifespan_context = reviewed_lifespan
AegisServer(app, host='127.0.0.1', port=0, access_log=False, log_level='warning',
            timeout_graceful_shutdown=5).run(sockets=[socket.socket(fileno=int(sys.argv[2]))])
'''
        with (root / 'server.log').open('wb') as log:
            process = subprocess.Popen([str(python), '-I', '-c', server_code,
                                        str(source), str(listener.fileno())], cwd=root,
                                       env=environment, pass_fds=(listener.fileno(),),
                                       stdout=log, stderr=log)
            listener.close()
            base = f'http://127.0.0.1:{port}'
            anonymous = build_opener(ProxyHandler({}))
            authenticated = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))

            def request(path, body=None, expected=200, opener=authenticated):
                data = None if body is None else json.dumps(body).encode()
                req = Request(base + path, data=data,
                              headers={} if body is None else {'Content-Type': 'application/json'})
                try:
                    response = opener.open(req, timeout=3)
                except HTTPError as exc:
                    response = exc
                with response:
                    if response.code != expected:
                        raise RuntimeError(f'HTTP {path} returned {response.code}, expected {expected}')
                    payload = response.read()
                    return json.loads(payload) if 'application/json' in response.headers.get('Content-Type', '') else payload.decode()

            try:
                deadline = time.monotonic() + 30
                while True:
                    if process.poll() is not None:
                        raise RuntimeError('Installed server exited before startup.')
                    try:
                        assert request('/api/health', opener=anonymous)['status'] == 'ok'
                        break
                    except (URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise RuntimeError('Installed server startup timed out.')
                        time.sleep(.05)
                request('/api/assets', expected=401, opener=anonymous)
                request('/api/auth/setup', {'password': 'runtime-package-fixture-password-only'})
                html = request('/')
                bundles = re.findall(r'(?:src|href)="(/assets/[^"\s]+)"', html)
                assert bundles and any(path.endswith('.js') for path in bundles)
                for path in bundles:
                    assert request(path)
                asset = request('/api/assets', {'name': 'Synthetic installed runtime',
                    'url': 'https://runtime-package-fixture.invalid/', 'authorized': True})
                task = request('/api/tasks', {'name': 'Synthetic pending plan', 'asset_ids': [asset['id']]})
                assert task['status'] == 'pending' and task['approved_at'] is None
                assets = request('/api/assets')
                assert len(assets) == 1 and assets[0]['id'] == asset['id']
                runtime = request('/api/runtime')
                assert runtime['requests']['requests'] == 0
                assert runtime['authentication']['parallel'] == 4
                assert request('/api/audit/verify', {})['status'] == 'verified'
                request('/api/auth/logout', {})
                request('/api/assets', expected=401)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                    raise RuntimeError('Installed server did not shut down cleanly.')
            # Uvicorn may re-raise SIGTERM after completing lifespan shutdown.
            assert process.returncode in (0, -signal.SIGTERM), 'Installed server shutdown failed.'
            assert (source / 'shutdown-complete').read_text() == 'complete', 'Lifespan shutdown did not complete.'
        run([python, '-I', '-c',
             'from aegis.maintenance import WorkspaceLease; import sys; '
             'lease=WorkspaceLease(sys.argv[1]); lease.close()', source], 'workspace lease release')
        run([python, Path(__file__).resolve().with_name('review_installed_commands.py'),
             '--wheel', wheel], 'installed maintenance rehearsal')
        print(json.dumps({'valid': True, 'wheel': wheel.name,
            'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
            'installed_origin': origin['module'], 'target_requests': 0,
            'checks': ['locked runtime dependencies', 'pip check', 'four CLI entry points',
                       'installed server outside checkout', 'separate frontend assets',
                       'authentication and logout', 'asset and pending plan persistence',
                       'login limit metrics', 'read-only audit review', 'clean shutdown and lease release',
                       'installed backup/restore/audit rehearsal']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
