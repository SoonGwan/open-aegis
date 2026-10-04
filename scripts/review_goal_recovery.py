"""Rehearse installed goal round/retest backup and fresh approvals on owned loopback HTTP."""
import argparse
from contextlib import contextmanager
from http.cookiejar import CookieJar
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener
import venv


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


class OwnedTarget(BaseHTTPRequestHandler):
    hardened = False
    requests = []

    def log_message(self, *_):
        pass

    def do_GET(self):
        self.requests.append(self.path)
        if self.hold:
            self.entered.set()
            if not self.release.wait(timeout=10):
                return
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        if self.hardened:
            self.send_header('X-Content-Type-Options', 'nosniff')
        body = b'{"owned_recovery_fixture":true}'
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # The owned crash scenario deliberately closes an in-flight socket.


@contextmanager
def service(python, folder, environment, label):
    cookies = CookieJar()
    opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(cookies))
    base = 'http://127.0.0.1:' + str(free_port())
    environment = {**environment, 'AEGIS_PORT': base.rsplit(':', 1)[1]}
    with (folder / (label + '.log')).open('w') as log:
        process = subprocess.Popen([str(python), '-I', '-m', 'aegis'], cwd=folder,
                                   env=environment, stdout=log, stderr=subprocess.STDOUT)
        killed = False
        def crash_owned():
            nonlocal killed
            if process.poll() is not None:
                raise RuntimeError(label + ': cannot crash an exited owned service')
            killed = True
            process.kill()
            assert process.wait(timeout=5) == -9
        def http(path, body=None, *, method=None, expected=200, headers=None):
            request_headers = dict(headers or {})
            if body is not None:
                request_headers['Content-Type'] = 'application/json'
            request = Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                              headers=request_headers, method=method)
            try:
                response = opener.open(request, timeout=5)
            except HTTPError as error:
                response = error
            with response:
                if response.status != expected:
                    raise RuntimeError(label + ' ' + path + ': unexpected HTTP ' + str(response.status))
                return json.loads(response.read())
        try:
            deadline = time.monotonic() + 15
            while True:
                if process.poll() is not None:
                    raise RuntimeError(label + ': installed service exited during startup')
                try:
                    assert http('/api/health')['status'] == 'ok'
                    break
                except (URLError, TimeoutError):
                    if time.monotonic() >= deadline:
                        raise RuntimeError(label + ': startup deadline exceeded')
                    time.sleep(.05)
            yield http, cookies, crash_owned
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
                raise RuntimeError(label + ': shutdown deadline exceeded')
            assert process.returncode in ((-9,) if killed else (0, -15, 143))


def finished(http, task_id):
    deadline = time.monotonic() + 15
    while True:
        result = http('/api/tasks/' + task_id)
        if result['task']['status'] in ('completed', 'failed', 'stopped', 'interrupted'):
            assert result['task']['status'] == 'completed', result['task']['status']
            assert {row['check'] for row in result['coverage']} == set(result['task']['checks'])
            assert all(row['status'] == 'completed' or
                       (row['check'] == 'api_authorization' and row['status'] == 'skipped')
                       for row in result['coverage'])
            return result
        if time.monotonic() >= deadline:
            raise RuntimeError('Owned approved task did not finish')
        time.sleep(.05)


def execute_restored(python, folder, environment, http_target, pending, origin_key, crash):
    """Approve one pending plan; optionally crash its owned service during its GET."""
    label = "restored-" + origin_key.replace("_", "-")
    with service(python, folder, environment, label) as (http, _, crash_owned):
        http('/api/auth/login', {'password': 'owned-goal-recovery-password'})
        before = len(http_target.requests)
        if crash:
            http_target.entered.clear()
            http_target.release.clear()
            http_target.hold = True
        http('/api/tasks/' + pending['id'] + '/approve', method='POST')
        if crash:
            assert http_target.entered.wait(timeout=5), 'Owned target did not receive the approved request'
            assert http('/api/tasks/' + pending['id'])['task']['status'] == 'running'
            crash_owned()
            http_target.hold = False
            http_target.release.set()
        else:
            result = finished(http, pending['id'])
            assert result['task'][origin_key] == pending[origin_key]
        assert len(http_target.requests) == before + 1
    if not crash:
        return pending
    with service(python, folder, environment, label + '-crash-recovered') as (http, _, _):
        http('/api/auth/login', {'password': 'owned-goal-recovery-password'})
        interrupted = http('/api/tasks/' + pending['id'])
        assert interrupted['task']['status'] == 'interrupted'
        assert interrupted['task'][origin_key] == pending[origin_key]
        assert all(row['status'] == 'interrupted' for row in interrupted['coverage'])
        assert len(http_target.requests) == before + 1
        task_count = http('/api/records/tasks')['total']
        retry_path = '/api/tasks/' + pending['id'] + '/retry'
        retry = http(retry_path, method='POST')
        assert retry['status'] == 'pending' and retry['approved_at'] is None
        assert retry[origin_key] == pending[origin_key]
        assert retry.get('planning_round', 0) == pending.get('planning_round', 0)
        assert http(retry_path, method='POST')['id'] == retry['id']
        assert http('/api/records/tasks')['total'] == task_count + 1
        assert all(row['status'] == 'not_started' for row in http('/api/tasks/' + retry['id'])['coverage'])
        assert len(http_target.requests) == before + 1
        http('/api/tasks/' + retry['id'] + '/approve', method='POST')
        result = finished(http, retry['id'])
        assert result['task'][origin_key] == pending[origin_key]
        assert len(http_target.requests) == before + 2
        return retry


def rehearse(backend, root, python, binaries, environment, run, dsn=None, crash=False):
    folder = root / backend
    folder.mkdir()
    source = folder / 'source'
    restored = folder / 'restored'
    source_environment = {**environment, 'AEGIS_STORAGE_BACKEND': backend,
                          'AEGIS_DATA_DIR': str(source)}
    restored_environment = {**source_environment, 'AEGIS_DATA_DIR': str(restored)}
    if backend == 'postgres':
        source_environment.update(AEGIS_POSTGRES_DSN=dsn, AEGIS_POSTGRES_SCHEMA='goal_source')
        restored_environment.update(AEGIS_POSTGRES_DSN=dsn, AEGIS_POSTGRES_SCHEMA='goal_restored')
        run([binaries / 'aegis-init-postgres'], source_environment)
    class Handler(OwnedTarget):
        requests = []
        hardened = False
        hold = False
        entered = threading.Event()
        release = threading.Event()
    target = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=target.serve_forever, daemon=True)
    thread.start()
    try:
        with service(python, folder, source_environment, 'source') as (http, cookies, crash_owned):
            assert http('/api/auth/setup', {'password': 'owned-goal-recovery-password',
                                          'setup_token': 'owned-goal-recovery-token'})['user']['role'] == 'admin'
            asset = http('/api/assets', {'name': 'Owned recovery target', 'authorized': True,
                                        'url': 'http://127.0.0.1:' + str(target.server_port) + '/'})
            original = http('/api/tasks', {'name': 'Owned source goal', 'asset_ids': [asset['id']],
                                          'checks': ['security_headers']})
            draft_path = '/api/tasks/' + original['id'] + '/goal-plans'
            draft_input = {'request_id': 'a' * 32, 'mode': 'rules', 'goal': 'Owned response header review'}
            draft = http(draft_path, draft_input)
            goal = http(draft_path + '/' + draft['id'] + '/accept', {'fingerprint': draft['fingerprint']})
            assert goal['goal_plan']['execution'] == 'objective_pairs'
            assert Handler.requests == []
            http('/api/tasks/' + goal['id'] + '/approve', method='POST')
            executed = finished(http, goal['id'])
            assert Handler.requests == ['/']
            source_coverage = {row['check']: row['status'] for row in executed['coverage']}
            assert len(source_coverage) == 6 and source_coverage['api_authorization'] == 'skipped'
            assert source_coverage['security_headers'] == 'completed'
            finding = next(row for row in executed['findings'] if row['code'] == 'missing-nosniff')
            proof_path = '/api/tasks/' + goal['id'] + '/goal-objectives/g1/findings'
            proof = http(proof_path)
            assert proof['goal_verified'] is False and finding['id'] in {row['id'] for row in proof['items']}
            todo_path = '/api/tasks/' + goal['id'] + '/todos'
            http(todo_path, {'request_id': 'b' * 32, 'title': 'Recheck approved header scope',
                             'check_ids': ['security_headers']})
            round_path = '/api/tasks/' + goal['id'] + '/next-plan'
            proposal = http(round_path)
            assert proposal['available'] and proposal['basis']['missing_checks'] == []
            round_input = {'fingerprint': proposal['fingerprint']}
            first_round = http(round_path, round_input)
            following = http('/api/tasks/' + first_round['id'] + '/replan', method='POST')
            assert following['planning_round'] == 1 and following['goal_plan'] == goal['goal_plan']
            assert http(round_path, round_input)['id'] == following['id']
            retest_path = proof_path + '/' + finding['id'] + '/retest'
            retest_input = {'request_id': 'c' * 32}
            first_retest = http(retest_path, retest_input)
            retest = http('/api/tasks/' + first_retest['id'] + '/replan', method='POST')
            assert retest['goal_retest'] == first_retest['goal_retest']
            assert http(retest_path, retest_input)['id'] == first_retest['id']
            for pending in (following, retest):
                assert pending['status'] == 'pending' and pending['approved_at'] is None
                assert all(row['status'] == 'not_started' for row in http('/api/tasks/' + pending['id'])['coverage'])
            assert Handler.requests == ['/']
            old_cookie = next(cookie.value for cookie in cookies if cookie.name == 'aegis_session')
            source_task_count = http('/api/records/tasks')['total']
            if crash:
                crash_owned()
        if crash:
            with service(python, folder, source_environment, 'source-crash-recovered') as (http, _, _):
                http('/api/auth/login', {'password': 'owned-goal-recovery-password'})
                assert http(round_path, round_input)['id'] == following['id']
                assert http(retest_path, retest_input)['id'] == first_retest['id']
                for pending, key in ((following, 'goal_plan'), (retest, 'goal_retest')):
                    current = http('/api/tasks/' + pending['id'])
                    assert current['task'][key] == pending[key]
                    assert current['task']['status'] == 'pending' and current['task']['approved_at'] is None
                    assert all(row['status'] == 'not_started' for row in current['coverage'])
                assert http('/api/records/tasks')['total'] == source_task_count
                assert Handler.requests == ['/']
        # Stop the source cleanly, then copy its consistent data using installed CLIs.
        archive = folder / ('backup.zip' if backend == 'postgres' else 'backup.db')
        checkpoint = folder / 'checkpoint.json'
        audit = run([binaries / 'aegis-verify-audit', '--output', checkpoint], source_environment)
        backup = run([binaries / 'aegis-backup', '--output', archive], source_environment)
        assert archive.stat().st_mode & 0o777 == 0o600
        if backend == 'postgres':
            assert backup['audit']['checkpoint'] == audit['checkpoint']
            checked = run([binaries / 'aegis-restore', '--source', archive, '--check-only',
                           '--checkpoint', checkpoint], {**source_environment, 'AEGIS_POSTGRES_DSN': ''})
            assert checked['manifest'] == backup['manifest']
            restored_result = run([binaries / 'aegis-restore', '--source', archive,
                                   '--checkpoint', checkpoint], restored_environment)
        else:
            checked = run([binaries / 'aegis-restore', '--source', archive, '--check-only'], source_environment)
            assert checked['records'] == backup['records']
            restored_result = run([binaries / 'aegis-restore', '--source', archive], restored_environment)
        assert restored_result['sessions_revoked']
        restored_audit = run([binaries / 'aegis-verify-audit', '--checkpoint', checkpoint], restored_environment)
        assert restored_audit['checkpoint'] == audit['checkpoint']
        assert Handler.requests == ['/']
        with service(python, folder, restored_environment, 'restored') as (http, _, crash_owned):
            http('/api/assets', expected=401, headers={'Cookie': 'aegis_session=' + old_cookie})
            http('/api/auth/login', {'password': 'owned-goal-recovery-password'})
            assert http('/api/settings')['storage'] == backend
            assert http(draft_path, draft_input)['id'] == draft['id']
            assert http(draft_path + '/' + draft['id'] + '/accept', {'fingerprint': draft['fingerprint']})['id'] == goal['id']
            assert http(round_path, round_input)['id'] == following['id']
            assert http('/api/tasks/' + first_round['id'] + '/replan', method='POST')['id'] == following['id']
            assert http(retest_path, retest_input)['id'] == first_retest['id']
            assert http('/api/tasks/' + first_retest['id'] + '/replan', method='POST')['id'] == retest['id']
            for pending, key in ((following, 'goal_plan'), (retest, 'goal_retest')):
                current = http('/api/tasks/' + pending['id'])
                assert current['task'][key] == pending[key]
                assert current['task']['status'] == 'pending' and current['task']['approved_at'] is None
                assert all(row['status'] == 'not_started' for row in current['coverage'])
            restored_proof = http(proof_path)
            assert restored_proof['goal_verified'] is False
            assert restored_proof['items'] == proof['items']
            assert Handler.requests == ['/']
        # Recovery must not approve execution. Each new approval is explicit here.
        Handler.hardened = True
        retest = execute_restored(python, folder, restored_environment, Handler, retest, 'goal_retest', crash)
        following = execute_restored(python, folder, restored_environment, Handler, following, 'goal_plan', crash)
        # Reopen the restored service again: completed results and request identities persist.
        with service(python, folder, restored_environment, 'reopened') as (http, _, _):
            http('/api/auth/login', {'password': 'owned-goal-recovery-password'})
            assert http(round_path, round_input)['id'] == following['id']
            assert http(retest_path, retest_input)['id'] == first_retest['id']
            assert http('/api/tasks/' + following['id'])['task']['status'] == 'completed'
            retest_results = http('/api/findings/' + finding['id'])['retests']
            resolved = next(row for row in retest_results if row['task_id'] == retest['id'])
            assert resolved['conclusion'] == 'resolved' and resolved['goal_retest'] == retest['goal_retest']
            latest = next(row for row in http(proof_path)['items'] if row['id'] == finding['id'])
            assert latest['latest_retest']['task_id'] == retest['id'] and latest['latest_retest']['conclusion'] == 'resolved'
            assert http('/api/tasks/' + following['id'] + '/goal-progress')['goal_verified'] is False
            assert http('/api/tasks/' + goal['id'] + '/goal-progress')['goal_verified'] is False
            assert Handler.requests == ['/'] * (5 if crash else 3)
        unchanged_source_audit = run([binaries / 'aegis-verify-audit', '--checkpoint', checkpoint], source_environment)
        final_audit = run([binaries / 'aegis-verify-audit', '--checkpoint', checkpoint], restored_environment)
        assert unchanged_source_audit['checkpoint'] == audit['checkpoint']
        assert final_audit['valid'] and final_audit['events'] > audit['events']
        if backend == 'postgres':
            assert not (source / 'aegis.db').exists() and not (restored / 'aegis.db').exists()
        return {'backend': backend, 'valid': True, 'owned_target_requests': len(Handler.requests),
                'process_crash_rehearsed': crash, 'owned_service_sigkills': 3 if crash else 0,
                'preapproval_restore_requests': 0, 'external_target_requests': 0,
                'goal_round': following['id'], 'goal_retest': retest['id'], 'audit_events_before_backup': audit['events'],
                'source_coverage': source_coverage,
                'audit_events_after_recovery': final_audit['events'],
                'checks': ['actual source HTTP proof', 'goal round and retest replacement',
                           'installed backup/archive check/restore/audit checkpoint', 'old session refused',
                           'restored pending state without target requests', 'same request identities after restore',
                           'new explicit approvals and resolved origin', 'completed results survive another service restart',
                           'source audit unchanged and restored audit extends its checkpoint'] +
                          (['pending SIGKILL recovery preserves plans and request identities',
                            'in-flight retest and round SIGKILL recover as interrupted with no automatic requests',
                            'one pending retry per interrupted task before fresh approval'] if crash else [])}
    finally:
        Handler.release.set()
        target.shutdown()
        target.server_close()
        thread.join(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', required=True, type=Path)
    parser.add_argument('--backend', choices=('sqlite', 'postgres', 'both'), default='both')
    parser.add_argument('--crash', action='store_true', help='SIGKILL owned pending and in-flight servers; verify interrupted recovery and newly approved retry')
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    repository = Path(__file__).resolve().parents[1]
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('AEGIS_', 'PYTHON', 'PG')) and key != 'VIRTUAL_ENV'}
    environment.update(AEGIS_HOST='127.0.0.1', AEGIS_LAB_MODE='1', AEGIS_SETUP_TOKEN='owned-goal-recovery-token',
                       AEGIS_REQUEST_RETRIES='0', AEGIS_TARGET_RPS='20')
    native = args.backend in ('postgres', 'both')
    postgres_binaries = {name: shutil.which(name) for name in ('initdb', 'pg_ctl', 'pg_dump', 'pg_restore')}
    if native and not all(postgres_binaries.values()):
        parser.error('PostgreSQL binaries are required for the requested native rehearsal')
    with tempfile.TemporaryDirectory(prefix='aegis-goal-recovery-', dir='/tmp') as temporary:
        root = Path(temporary)
        installation = root / 'installation'
        venv.EnvBuilder(with_pip=True).create(installation)
        binaries = installation / 'bin'
        python = binaries / 'python'
        def run(command, env):
            result = subprocess.run([str(item) for item in command], cwd=root, env=env,
                                    capture_output=True, text=True, timeout=180)
            if result.returncode:
                raise RuntimeError('Installed command failed: ' + Path(str(command[0])).name)
            return json.loads(result.stdout) if result.stdout.strip().startswith('{') else result.stdout
        locks = [repository / 'requirements.lock']
        if native:
            locks.append(repository / 'requirements-postgres.lock')
        run([python, '-m', 'pip', 'install', *[item for lock in locks for item in ('-r', lock)]], environment)
        run([python, '-m', 'pip', 'install', '--no-index', '--no-deps', wheel], environment)
        run([python, '-m', 'pip', 'check'], environment)
        origin = run([python, '-I', '-c', 'import aegis,json,sys;from pathlib import Path;'
                      'assert Path(aegis.__file__).is_relative_to(Path(sys.prefix));'
                      'print(json.dumps({"module":aegis.__file__}))'], environment)
        results = []
        if args.backend in ('sqlite', 'both'):
            results.append(rehearse('sqlite', root, python, binaries, environment, run, crash=args.crash))
        if native:
            cluster, socket_folder = root / 'cluster', root / 'socket'
            socket_folder.mkdir(mode=0o700)
            run([postgres_binaries['initdb'], '-D', cluster, '--auth=trust', '--no-locale', '--encoding=UTF8'], environment)
            port = free_port()
            run([postgres_binaries['pg_ctl'], '-D', cluster, '-l', root / 'postgres.log', '-o',
                 "-c listen_addresses='' -k " + str(socket_folder) + ' -p ' + str(port), '-w', 'start'], environment)
            try:
                dsn = 'host=' + str(socket_folder) + ' port=' + str(port) + ' dbname=postgres'
                results.append(rehearse('postgres', root, python, binaries, environment, run, dsn, crash=args.crash))
            finally:
                run([postgres_binaries['pg_ctl'], '-D', cluster, '-w', '-m', 'fast', 'stop'], environment)
        print(json.dumps({'valid': True, 'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
                          'installed_origin': origin['module'], 'results': results}, ensure_ascii=False))


if __name__ == '__main__':
    main()
