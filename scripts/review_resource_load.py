"""Owned loopback read/export load rehearsal; no target execution or real workspace.

Measurements are scenario evidence, not production memory/latency SLO certification.
Requires the development environment's httpx, Python 3.11+, and POSIX ps/pass_fds.
"""
import argparse
from collections import Counter, deque
from contextlib import ExitStack
import hashlib
from importlib.metadata import version
import json
import os
import platform
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aegis.maintenance import WorkspaceLease
from aegis.store import Store

SERVER = '''
import socket, sys, time
from pathlib import Path
from contextlib import asynccontextmanager
from aegis.app import create_app
from aegis.__main__ import AegisServer
app = create_app(sys.argv[1], allow_private=False)
app.state.store.put_many([('assets', {
 'id':f'load_{i}', 'name':f'Owned synthetic asset {i}',
 'url':f'https://owned-{i}.invalid/', 'authorized':True,
 'archived':False, 'revision':1, 'created_at':time.time(),
 'scope_prefix':'/', 'authorization_rules':[],
}) for i in range(int(sys.argv[3]))] + [('findings', {
 'id':f'finding_{i}', 'asset_id':f'load_{i}', 'asset_name':f'Owned synthetic asset {i}',
 'title':f'Owned synthetic finding {i}', 'severity':'info', 'status':'open',
 'check':'api_authorization', 'created_at':time.time(), 'task_ids':[], 'evidence_ids':[],
 'remediation':'Synthetic read-load fixture; no real target was checked.',
}) for i in range(int(sys.argv[3]))])
original = app.router.lifespan_context
@asynccontextmanager
async def lifespan(application):
 async with original(application): yield
 (Path(sys.argv[1])/'shutdown-complete').write_text('complete')
app.router.lifespan_context = lifespan
AegisServer(app, host='127.0.0.1', port=0, access_log=False,
 log_level='warning', timeout_graceful_shutdown=5).run(
 sockets=[socket.socket(fileno=int(sys.argv[2]))])
'''


def bounded_int(low, high):
    def parse(value):
        number = int(value)
        if not low <= number <= high:
            raise argparse.ArgumentTypeError(f'must be {low}..{high}')
        return number
    return parse


def process_sample(pid):
    result = subprocess.run(['ps', '-o', 'rss=,time=', '-p', str(pid)],
                            capture_output=True, text=True, timeout=3, check=True)
    rss, cpu = result.stdout.split()
    seconds = 0.0
    for component in cpu.split(':'):
        seconds = seconds * 60 + float(component)
    fd_path = Path(f'/proc/{pid}/fd')
    return {'rss_kib': int(rss), 'cpu_seconds': seconds,
            'open_fds': len(list(fd_path.iterdir())) if fd_path.is_dir() else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=bounded_int(1, 3600), default=60)
    parser.add_argument('--clients', type=bounded_int(1, 32), default=4)
    parser.add_argument('--sse-clients', type=bounded_int(0, 32), default=0)
    revocations = parser.add_mutually_exclusive_group()
    revocations.add_argument('--revoke-stream-session', action='store_const',
                             const='logout', dest='stream_revocation', help='legacy alias for logout')
    revocations.add_argument('--stream-revocation', choices=('logout', 'password', 'role', 'disable'))
    parser.add_argument('--assets', type=bounded_int(25, 20000), default=1000)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    revoke_requested = args.stream_revocation is not None
    if revoke_requested and (not args.sse_clients or args.duration < 2):
        parser.error('stream revocation requires sse-clients > 0 and duration >= 2')
    if args.stream_revocation in ('password', 'role', 'disable') and args.sse_clients < 2:
        parser.error('account revocation requires at least two SSE clients for independent sessions')
    fingerprint = hashlib.sha256()
    for path in sorted((ROOT/'aegis').rglob('*.py')):
        fingerprint.update(str(path.relative_to(ROOT)).encode())
        fingerprint.update(path.read_bytes())
    environment = {key:value for key,value in os.environ.items()
                   if not key.startswith('AEGIS_') and key not in ('PYTHONPATH','PYTHONHOME')}
    lock = threading.Lock()
    counts = Counter()
    errors = []
    latency = deque(maxlen=2000)
    samples = deque(maxlen=1000)
    with tempfile.TemporaryDirectory(prefix='aegis-load-review-') as temporary, ExitStack() as stack:
        directory = Path(temporary)
        workspace = directory/'workspace'
        listener = stack.enter_context(socket.socket())
        listener.bind(('127.0.0.1', 0))
        base = f'http://127.0.0.1:{listener.getsockname()[1]}'
        log = stack.enter_context((directory/'server.log').open('wb'))
        process = subprocess.Popen([sys.executable, '-c', SERVER, str(workspace),
                                    str(listener.fileno()), str(args.assets)], cwd=ROOT,
                                   env=environment, pass_fds=(listener.fileno(),), stdout=log, stderr=log)
        listener.close()
        stopped = threading.Event()
        workers = []
        stream_workers = []
        shutdown_sent = threading.Event()
        revocation_sent = threading.Event()
        revocation = {'requested':revoke_requested, 'action':args.stream_revocation, 'performed':False}
        streams = {'opened':0, 'active':0, 'natural_reconnections':0,
                   'shutdown_eof':0, 'revoked_eof':0, 'data_messages':0, 'heartbeats':0, 'errors':0}
        try:
            with httpx.Client(base_url=base, trust_env=False, timeout=10) as authenticated:
                startup = time.monotonic()+20
                while True:
                    if process.poll() is not None:
                        raise RuntimeError('Owned server exited during startup')
                    try:
                        ready = authenticated.get('/api/health')
                        ready.raise_for_status()
                        break
                    except httpx.TransportError:
                        if time.monotonic() >= startup:
                            raise RuntimeError('Owned server startup deadline exceeded')
                        time.sleep(.05)
                setup = authenticated.post('/api/auth/setup', json={'password':'owned-load-fixture-password-only'})
                setup.raise_for_status()
                assert authenticated.get('/api/auth/status').json()['authenticated']
                cookie = dict(authenticated.cookies)
                stream_cookies = [cookie]
                stream_controls = []
                stream_username = 'admin'
                stream_password = 'owned-load-fixture-password-only'
                if revoke_requested:
                    login_count = 1
                    if args.stream_revocation != 'logout':
                        stream_username = 'owned-stream-operator'
                        created = authenticated.post('/api/users', json={
                            'username':stream_username, 'name':'Owned synthetic operator',
                            'role':'operator', 'password':stream_password})
                        created.raise_for_status()
                        stream_user = created.json()
                        login_count = 2
                    stream_cookies = []
                    for _ in range(login_count):
                        control = stack.enter_context(httpx.Client(base_url=base, trust_env=False, timeout=10))
                        control.post('/api/auth/login', json={
                            'username':stream_username,'password':stream_password}).raise_for_status()
                        stream_controls.append(control)
                        stream_cookies.append(dict(control.cookies))
                    assert len({item['aegis_session'] for item in stream_cookies}) == login_count
                    revocation['sessions_tested'] = login_count
                first = authenticated.get('/api/records/assets', params={'limit':25}).json()
                assert first['total'] == args.assets and len(first['items']) == 25
                ready_streams = [threading.Event() for _ in range(args.sse_clients)]

                def stream_worker(index):
                    cursor = 0
                    try:
                        with httpx.Client(base_url=base, cookies=stream_cookies[index % len(stream_cookies)], trust_env=False,
                                          timeout=httpx.Timeout(10, read=None)) as client:
                            while not shutdown_sent.is_set():
                                with client.stream('GET', '/api/events/stream', params={'after':cursor}) as response:
                                    response.raise_for_status()
                                    assert response.headers['Content-Type'].startswith('text/event-stream')
                                    with lock:
                                        streams['opened'] += 1
                                        streams['active'] += 1
                                    try:
                                        for line in response.iter_lines():
                                            if line.startswith('id:'):
                                                cursor = max(cursor, int(line[3:].strip()))
                                            elif line.startswith('data:'):
                                                assert isinstance(json.loads(line[5:]), dict)
                                                with lock:
                                                    streams['data_messages'] += 1
                                            elif line.startswith(':'):
                                                with lock:
                                                    streams['heartbeats'] += 1
                                            ready_streams[index].set()
                                    finally:
                                        with lock:
                                            streams['active'] -= 1
                                if shutdown_sent.is_set():
                                    with lock:
                                        streams['shutdown_eof'] += 1
                                    return
                                if revocation_sent.is_set():
                                    with lock:
                                        streams['revoked_eof'] += 1
                                    return
                                with lock:
                                    streams['natural_reconnections'] += 1
                    except Exception as error:
                        with lock:
                            streams['errors'] += 1
                            if len(errors) < 10:
                                errors.append(f'event stream: {type(error).__name__}')

                for index in range(args.sse_clients):
                    thread = threading.Thread(target=stream_worker, args=(index,), name=f'owned-sse-{index}')
                    stream_workers.append(thread)
                    thread.start()
                for ready in ready_streams:
                    if not ready.wait(10):
                        raise RuntimeError('Owned event stream did not deliver a first frame')

                def wait_for_streams(expected):
                    stream_deadline = time.monotonic()+5
                    while True:
                        with lock:
                            active_streams = streams['active']
                            stream_errors = streams['errors']
                        if stream_errors:
                            raise RuntimeError('Owned event stream failed during load')
                        if active_streams == expected:
                            return active_streams
                        if time.monotonic() >= stream_deadline:
                            raise RuntimeError('Owned event streams did not reach the expected active count')
                        time.sleep(.02)

                started = time.monotonic()
                deadline = started+args.duration
                # Revoke before the normal ~30s stream lifetime can end the first
                # connection by itself, which would weaken the revocation evidence.
                revoke_at = started+min(args.duration/2, 10)
                baseline = process_sample(process.pid)
                peak = baseline['rss_kib']
                paths = ['/api/records/assets?limit=25', '/api/overview', '/api/runtime',
                         '/api/reports/export?format=json']

                def worker(index):
                    iteration = index
                    with httpx.Client(base_url=base, cookies=cookie, trust_env=False, timeout=10) as client:
                        while time.monotonic() < deadline and not stopped.is_set():
                            path = paths[iteration % len(paths)]
                            before = time.monotonic()
                            try:
                                response = client.get(path)
                                if response.status_code == 429 and path.startswith('/api/reports/'):
                                    assert float(response.headers['Retry-After']) > 0
                                else:
                                    response.raise_for_status()
                                    data = response.json()
                                    if '/records/assets' in path:
                                        assert len(data['items']) == 25 and data['total'] == args.assets
                                    elif path == '/api/overview':
                                        assert len(data['assets']) <= 100 and data['stats']['assets'] == args.assets
                                    elif path == '/api/runtime':
                                        assert data['requests']['requests'] == 0
                                    else:
                                        assert len(data['findings']) == args.assets
                                        assert not data['tasks'] and not data['traffic']
                                with lock:
                                    counts[f'{path} HTTP {response.status_code}'] += 1
                                    latency.append((time.monotonic()-before)*1000)
                            except Exception as error:
                                with lock:
                                    counts['failures'] += 1
                                    if len(errors) < 10:
                                        errors.append(f'{path}: {type(error).__name__}')
                            iteration += 1
                            stopped.wait(.03)

                for index in range(args.clients):
                    thread = threading.Thread(target=worker, args=(index,), name=f'owned-load-{index}')
                    workers.append(thread)
                    thread.start()
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError('Owned server exited during load')
                    if revoke_requested and not revocation['performed'] and time.monotonic() >= revoke_at:
                        revocation['open_before_revocation'] = wait_for_streams(args.sse_clients)
                        revoke_started = time.monotonic()
                        revocation_sent.set()
                        if args.stream_revocation == 'logout':
                            changed = stream_controls[0].post('/api/auth/logout')
                        elif args.stream_revocation == 'password':
                            changed = stream_controls[0].post('/api/auth/password', json={
                                'current_password':stream_password,
                                'new_password':'owned-load-new-password-only'})
                        else:
                            changes = {'expected_updated_at':stream_user['updated_at']}
                            changes.update({'role':'viewer'} if args.stream_revocation == 'role' else {'disabled':True})
                            changed = authenticated.patch(f"/api/users/{stream_user['id']}", json=changes)
                        changed.raise_for_status()
                        for thread in stream_workers:
                            thread.join(5)
                            if thread.is_alive():
                                raise RuntimeError('Owned event stream remained open after revocation')
                        assert streams['revoked_eof'] == args.sse_clients and streams['errors'] == 0
                        revocation['closed_seconds'] = round(time.monotonic()-revoke_started,3)
                        reconnect_statuses = []
                        for old_cookie in stream_cookies:
                            with httpx.Client(base_url=base, cookies=old_cookie, trust_env=False, timeout=10) as revoked_probe:
                                with revoked_probe.stream('GET', '/api/events/stream') as denied:
                                    assert denied.status_code == 401
                                    reconnect_statuses.append(denied.status_code)
                                assert not revoked_probe.get('/api/auth/status').json()['authenticated']
                        revocation['reconnect_statuses'] = reconnect_statuses
                        assert authenticated.get('/api/auth/status').json()['authenticated']
                        if args.stream_revocation != 'logout':
                            with httpx.Client(base_url=base, trust_env=False, timeout=10) as fresh:
                                login = fresh.post('/api/auth/login', json={
                                    'username':stream_username,'password':stream_password})
                                revocation['original_password_login_status'] = login.status_code
                                if args.stream_revocation in ('password', 'disable'):
                                    assert login.status_code == 401
                                else:
                                    login.raise_for_status()
                                    identity = fresh.get('/api/auth/status').json()
                                    assert identity['authenticated'] and identity['user']['role'] == 'viewer'
                                    assert fresh.post('/api/assets', json={
                                        'name':'Must not be created', 'url':'https://denied-owned.invalid/',
                                        'authorized':True}).status_code == 403
                                    revocation['fresh_role'] = 'viewer'
                                    revocation['fresh_write_status'] = 403
                                if args.stream_revocation == 'password':
                                    fresh.post('/api/auth/login', json={
                                        'username':stream_username,'password':'owned-load-new-password-only'}).raise_for_status()
                                    identity = fresh.get('/api/auth/status').json()
                                    assert identity['authenticated'] and identity['user']['role'] == 'operator'
                                    revocation['new_password_authenticated'] = True
                                if args.stream_revocation == 'disable':
                                    users = authenticated.get('/api/users')
                                    users.raise_for_status()
                                    assert any(user['id'] == stream_user['id'] and user['disabled'] for user in users.json())
                                    revocation['disabled_account_verified'] = True
                        revocation.update(performed=True, unaffected_session_authenticated=True)
                        with lock:
                            completed_at_revocation = sum(counts.values())
                    sample = {'elapsed_seconds':round(time.monotonic()-started, 3), **process_sample(process.pid)}
                    samples.append(sample)
                    peak = max(peak, sample['rss_kib'])
                    pause = min(2, max(0, deadline-time.monotonic()))
                    if revoke_requested and not revocation['performed']:
                        pause = min(pause, max(0, revoke_at-time.monotonic()))
                    stopped.wait(pause)
                stopped.set()
                for thread in workers:
                    thread.join(15)
                    if thread.is_alive():
                        raise RuntimeError('Owned workload did not drain')
                final = process_sample(process.pid)
                peak = max(peak, final['rss_kib'])
                runtime = authenticated.get('/api/runtime').json()
                assert runtime['requests']['requests'] == 0
                assert runtime['exports']['active'] == 0
                assert not runtime['tasks']
                elapsed = time.monotonic()-started
                # A natural 30-second stream rollover can briefly reconnect.
                open_at_shutdown = wait_for_streams(0 if revoke_requested else args.sse_clients)
                if revoke_requested:
                    assert revocation['performed']
                    revocation['responses_after_revocation'] = sum(counts.values())-completed_at_revocation
                    assert revocation['responses_after_revocation'] > 0
            shutdown_started = time.monotonic()
            shutdown_sent.set()
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=10)
            # Uvicorn can re-raise the requested SIGTERM after finishing lifespan.
            assert process.returncode in (0, -signal.SIGTERM)
            assert (workspace/'shutdown-complete').read_text() == 'complete'
            for thread in stream_workers:
                thread.join(5)
                if thread.is_alive():
                    raise RuntimeError('Owned event stream did not close after shutdown')
            assert streams['shutdown_eof'] == (0 if revoke_requested else args.sse_clients)
            assert streams['errors'] == 0
            shutdown_elapsed = time.monotonic()-shutdown_started
            with WorkspaceLease(workspace):
                store = Store(workspace/'aegis.db')
                assert store.count('assets') == args.assets
                assert store.count('findings') == args.assets
                assert store.count('tasks') == 0 and store.count('traffic') == 0
            ordered = sorted(latency)
            result = {
                'valid': counts['failures'] == 0 and sum(counts.values()) > 0,
                'scenario':'owned read/export load; no target execution',
                'source_sha256':fingerprint.hexdigest(),
                'platform':sys.platform, 'duration_requested_seconds':args.duration,
                'elapsed_seconds':round(elapsed,3), 'clients':args.clients, 'assets':args.assets,
                'synthetic_findings':args.assets,
                'event_streams':{'clients':args.sse_clients, 'open_before_shutdown':open_at_shutdown,
                    **streams},
                'shutdown_seconds':round(shutdown_elapsed,3),
                'stream_session_revocation':revocation,
                'target_requests':0, 'fixture_record_counts_preserved':True,
                'record_counts':{'assets':args.assets,'findings':args.assets,'tasks':0,'traffic':0},
                'environment':{'python':platform.python_version(),'machine':platform.machine(),
                    'sqlite':sqlite3.sqlite_version,'packages':{name:version(name) for name in
                    ('fastapi','starlette','uvicorn','anyio','httpx')}},
                'clean_shutdown':True, 'lease_released':True,
                'server_exit_code':process.returncode,
                'requests':dict(counts), 'error_types':errors,
                'rss_kib':{'baseline':baseline['rss_kib'],'sampled_peak':peak,'final':final['rss_kib']},
                'cpu_seconds_during_load':round(final['cpu_seconds']-baseline['cpu_seconds'],3),
                'latency_last_2000_ms':{'samples':len(ordered),
                    'p50':round(ordered[int((len(ordered)-1)*.5)],3) if ordered else None,
                    'p95':round(ordered[int((len(ordered)-1)*.95)],3) if ordered else None},
                'samples_last_1000':list(samples),
                'runtime':runtime,
                'limits':'No memory/latency SLO enforced; sampled RSS can miss peaks; parent memory excluded; not a long-duration production soak.',
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
            print(json.dumps({key:value for key,value in result.items() if key not in ('samples_last_1000','runtime')}, ensure_ascii=False), flush=True)
            if not result['valid']:
                raise SystemExit(1)
        finally:
            stopped.set()
            shutdown_sent.set()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            for thread in workers:
                thread.join(15)
            for thread in stream_workers:
                thread.join(5)


if __name__ == '__main__':
    main()
