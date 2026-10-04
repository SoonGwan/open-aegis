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
        for command in ('backup', 'restore', 'verify-audit', 'replay-policy', 'release', 'transfer-storage'):
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
                request('/openapi.json', expected=404, opener=anonymous)
                request('/docs', expected=404, opener=anonymous)
                request('/api/openapi.json', expected=401, opener=anonymous)
                request('/api/auth/setup', {'password': 'runtime-package-fixture-password-only'})
                assert '/api/assets' in request('/api/openapi.json')['paths']
                html = request('/')
                bundles = re.findall(r'(?:src|href)="(/assets/[^"\s]+)"', html)
                assert bundles and any(path.endswith('.js') for path in bundles)
                for path in bundles:
                    assert request(path)
                asset = request('/api/assets', {'name': 'Synthetic installed runtime',
                    'url': 'https://runtime-package-fixture.invalid/', 'authorized': True})
                task = request('/api/tasks', {'name': 'Synthetic pending plan', 'asset_ids': [asset['id']]})
                assert task['status'] == 'pending' and task['approved_at'] is None
                message_path = '/api/tasks/' + task['id'] + '/messages'
                question = {'content':'검증 요약', 'request_id':'installed-citation-0001'}
                reply = request(message_path, question)
                assert reply['provenance']['mode'] == 'recorded_rules'
                assert reply['provenance']['finding_total'] == 0
                citation = reply['provenance']['citations'][0]
                assert citation['kind'] == 'task' and citation['id'] == task['id']
                assert citation['snapshot']['status'] == 'pending'
                assert request(message_path, question) == reply
                messages = request(message_path + '/page')
                assert messages['total'] == 2
                assert next(m for m in messages['items'] if m['role'] == 'assistant') == reply
                assets = request('/api/assets')
                assert len(assets) == 1 and assets[0]['id'] == asset['id']
                assert request('/api/integrations/scopesentry/connections') == []
                request('/api/integrations/scopesentry/remote/preview', {'connection_id': 'unconfigured'}, expected=404)
                imported = request('/api/integrations/scopesentry/preview', {
                    'source_key': 'installed-runtime-fixture',
                    'export': json.dumps({'_id': '000000000000000000000001', 'type': 'http',
                                          'url': asset['url'], 'body': 'discarded-installed-fixture'})})
                assert imported['rows'][0]['action'] == 'link'
                selection = {'selected': ['000000000000000000000001'], 'authorized': True}
                applied = request('/api/integrations/scopesentry/' + imported['id'] + '/apply', selection)
                assert applied['created'] == 0 and applied['linked'] == 1
                assert request('/api/integrations/scopesentry/' + imported['id'] + '/apply', selection) == applied
                sources = request('/api/assets/' + asset['id'] + '/sources')
                assert sources['total'] == 1 and sources['items'][0]['external_id'] == selection['selected'][0]
                assert 'discarded-installed-fixture' not in json.dumps(sources)
                runtime = request('/api/runtime')
                usage = request('/api/llm/usage')
                assert usage['calls'] == 0 and usage['reported_tokens']['total_tokens'] is None
                assert request('/api/llm/usage?days=7')['days'] == 7
                assert request('/api/llm/usage?days=30')['days'] == 30
                combined = request('/api/llm/usage?source=all')
                assert combined['source_counts'] == {'planner':0, 'conversation':0}
                assert combined['source'] == 'all' and combined['calls'] == 0
                assert combined['costs']['totals'] == []
                assert all(value == 0 for value in combined['costs']['states'].values())
                attempts = request('/api/llm/usage?source=all&ledger=attempts')
                assert attempts['ledger'] == 'attempts' and attempts['calls'] == 0
                assert attempts['time_basis'] == 'started_at'
                assert all(value == 0 for value in attempts['attempt_states'].values())
                assert request('/api/llm/calls')['total'] == 0
                request('/api/llm/calls?state=unknown', expected=422)
                assert request('/api/llm/usage?source=conversation&days=7')['days'] == 7
                request('/api/llm/usage?source=unconfigured', expected=422)
                request('/api/llm/usage?days=365', expected=422)
                assert runtime['requests']['requests'] == 0
                assert runtime['authentication']['parallel'] == 4
                assert request('/api/audit/verify', {})['status'] == 'verified'
                request('/api/auth/logout', {})
                request('/api/assets', expected=401)
                request('/api/llm/usage', expected=401)
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
        # Ephemeral rehearsal key: never an official publisher trust root.
        release_key=root/'rehearsal-private.pem'; release_public=root/'rehearsal-public.pem'
        run(['openssl','genpkey','-algorithm','ED25519','-out',release_key], 'rehearsal signing key')
        release_key.chmod(0o600)
        run(['openssl','pkey','-in',release_key,'-pubout','-out',release_public], 'rehearsal public key')
        release_cli=installation/'bin'/'aegis-release'
        bundle=root/'signed-release'
        run([release_cli,'create','--wheel',wheel,'--web',web,'--lock',lock,
             '--output',bundle,'--private-key',release_key,'--revision','0'*40], 'installed release creation')
        verified=json.loads(run([release_cli,'verify','--bundle',bundle,'--public-key',release_public],
                                'installed signature and payload verification'))
        assert verified['package']=='open-aegis' and verified['sqlite_write']==2
        html_path=bundle/'web'/'index.html'; original_html=html_path.read_bytes()
        html_path.write_bytes(original_html+b'changed')
        refused=subprocess.run([str(release_cli),'verify','--bundle',str(bundle),
                                '--public-key',str(release_public)],cwd=root,env=environment,
                               capture_output=True,text=True,timeout=30)
        assert refused.returncode==2 and 'Traceback' not in refused.stderr
        html_path.write_bytes(original_html)
        preflight=root/'before-update'
        receipt=json.loads(run([release_cli,'prepare','--bundle',bundle,'--public-key',release_public,
                               '--database',source/'aegis.db','--output',preflight],
                              'installed offline update preflight'))
        assert receipt['installed'] is False and receipt['backup_metadata']['records']['tasks']==1
        run([python,'-I','-c',
             'from aegis.store import Store; import sys; '
             'Store(sys.argv[1]).put("notes",{"id":"failed-update","title":"synthetic"})',
             source/'aegis.db'], 'synthetic post-preflight update')
        restored=json.loads(run([installation/'bin'/'aegis-restore','--source',preflight/'before-update.db',
                                 '--destination',source/'aegis.db'], 'installed preflight rollback'))
        assert restored['sessions_revoked'] and restored['rollback']
        run([python,'-I','-c',
             'from aegis.store import Store; import sys; '
             'assert Store(sys.argv[1]).get("notes","failed-update") is None',
             source/'aegis.db'], 'rollback state verification')
        run([python,'-I','-c', '''
from aegis.store import Store
from aegis import call_ledger
from aegis.store_util import now
from aegis.llm import token_usage
from aegis.costs import estimate
import sys
s=Store(sys.argv[1]); task_id=s.page('tasks')['items'][0]['id']
price={'status':'unconfigured','quote':None}; at=now()
first=call_ledger.start(s,'planner',task_id,'owned-recovery-model','https://provider-fixture.invalid/v1',at,price)
second=call_ledger.start(s,'planner',task_id,'owned-recovery-model','https://provider-fixture.invalid/v1',at,price)
tokens=token_usage({'prompt_tokens':3,'completion_tokens':2,'total_tokens':5})
call_ledger.observe(s,second,{'call_id':second,'model':'owned-recovery-model','started_at':at,
    'observed_at':now(),'outcome':'accepted','tokens':tokens,'cost':estimate(tokens,price,at)})
assert Store(sys.argv[1]).get('llm_calls',first)['state']=='started'
''',source/'aegis.db'], 'installed synthetic unresolved call fixture')
        run([python,'-I','-c', '''
import asyncio,sys
from aegis.app import create_app
from aegis.usage import usage_summary
app=create_app(sys.argv[1],allow_private=False)
async def review():
    async with app.router.lifespan_context(app):
        result=usage_summary(app.state.store,source='all',ledger='attempts')
        assert result['calls']==2 and result['attempt_states']['interrupted']==2
        assert result['reported_tokens']['total_tokens']=='5' and result['usage_states']['missing']==1
        assert app.state.store.audit_integrity()['valid']
asyncio.run(review())
''',source], 'installed exclusive startup call recovery')
        print(json.dumps({'valid': True, 'wheel': wheel.name,
            'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
            'installed_origin': origin['module'], 'target_requests': 0,
            'checks': ['locked runtime dependencies', 'pip check', 'six CLI entry points',
                       'installed server outside checkout', 'separate frontend assets',
                       'authentication and logout', 'administrator schema and disabled public docs',
                       'asset and pending plan persistence', 'ScopeSentry review/apply/retry/provenance',
                       'recorded conversation citations, retry and persisted exchange',
                       'authenticated usage periods and validation',
                       'ScopeSentry installed remote configuration and unconfigured-source refusal',
                       'login limit metrics', 'read-only audit review', 'clean shutdown and lease release',
                       'installed backup/restore/audit rehearsal',
                       'attempt aggregate/page validation and installed startup recovery',
                       'ephemeral-key signed release, tamper refusal, preflight and data rollback']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
