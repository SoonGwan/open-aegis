import concurrent.futures
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pytest

from aegis.mcp_executor import ExecutionRejected, Runner
from aegis.mcp_process import cancel
from aegis.remote_mcp import RemoteMCPError
from tests.test_mcp_execution import KEY, approved_task, call, grant, service, target


def test_http_signed_cancel_is_idempotent_and_prevents_late_execution(service, target):
    runner, sdk = service
    token = grant(approved_task(target[0]))
    sdk.initialize()
    first = sdk.cancel_scoped(token)
    assert first == sdk.cancel_scoped(token)
    sdk.list_tools()
    assert call(sdk, token, 'security_headers')['isError'] is True
    assert not target[1]['requests']
    restarted = Runner('owned-server', KEY, runner.ledger.path, allow_private=True)
    with pytest.raises(ExecutionRejected):
        restarted.execute('validate_security_headers', {'grant': token})
    assert not target[1]['requests']


@pytest.mark.parametrize('change', ['signature', 'server', 'expired'])
def test_invalid_cancellation_cannot_modify_ledger(service, target, change):
    runner, sdk = service
    task = approved_task(target[0])
    token = grant(task)
    if change == 'signature':
        token = token[:-1] + ('0' if token[-1] != '0' else '1')
    elif change == 'server':
        from aegis.mcp_scope import issue_grant
        token = issue_grant(task, 'owned-asset', 'security_headers', 'other-server', KEY, allow_private=True)
    else:
        token = grant(task, timestamp=int(time.time()) - 2, ttl=1)
    sdk.initialize()
    with pytest.raises(RemoteMCPError):
        sdk.cancel_scoped(token)
    with runner.ledger.connect() as db:
        assert db.execute('SELECT count(*) FROM consumed').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM cancelled').fetchone()[0] == 0
    assert not target[1]['requests']


def test_separate_runner_observes_durable_cancel_and_interrupts_socket(tmp_path, target):
    token = grant(approved_task(target[0], request_timeout=8))
    target[1]['delay'] = 3
    runner = Runner('owned-server', KEY, tmp_path / 'nonce.db', allow_private=True)
    canceller = Runner('owned-server', KEY, runner.ledger.path, allow_private=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(runner.execute, 'validate_security_headers', {'grant': token})
        deadline = time.monotonic() + 3
        while not target[1]['requests'] and time.monotonic() < deadline:
            time.sleep(.01)
        assert target[1]['requests']
        start = time.monotonic()
        canceller.cancel(token)
        with pytest.raises(ExecutionRejected):
            future.result(timeout=1)
        assert time.monotonic() - start < 1
    assert not runner.stop.is_set() and not runner.gate.locked()
    # Cancellation is per grant; a different approval can still run.
    target[1]['delay'] = 0
    other = approved_task(target[0]); other['id'] = 'another-owned-approval'
    assert runner.execute('validate_security_headers', {'grant': grant(other)})['task_id'] == other['id']
    assert len(target[1]['requests']) == 2


def test_supervised_cancel_client_and_legacy_ledger_compatibility(service, target, tmp_path):
    runner, sdk = service
    token = grant(approved_task(target[0]))
    assert cancel(sdk.connection, token)['cancelled'] is True
    sdk.initialize()
    sdk.list_tools()
    assert call(sdk, token, 'security_headers')['isError'] is True
    assert not target[1]['requests']
    path = tmp_path / 'legacy.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE consumed(nonce TEXT PRIMARY KEY, retain_until INTEGER NOT NULL)')
        db.execute('INSERT INTO consumed VALUES (?,?)', ('a' * 32, time.time() + 600))
    upgraded = Runner('owned-server', KEY, path, allow_private=True)
    upgraded.cancel(token)
    with sqlite3.connect(path) as db:
        assert len(db.execute('PRAGMA table_info(consumed)').fetchall()) == 2
        assert db.execute('SELECT count(*) FROM consumed').fetchone()[0] == 2
        # The prior binary's two-column write remains compatible.
        db.execute('INSERT INTO consumed VALUES (?,?)', ('b' * 32, time.time() + 600))


def test_actual_separate_process_execution_observes_cancel(tmp_path, target):
    token = grant(approved_task(target[0], request_timeout=8))
    target[1]['delay'] = 3
    path = tmp_path / 'cross-process.db'
    runner = Runner('owned-server', KEY, path, allow_private=True)
    code = '''
import json,sys
sys.path.insert(0,sys.argv[1])
from aegis.mcp_executor import Runner,ExecutionRejected
value=json.load(sys.stdin)
try:
 Runner('owned-server',value['key'].encode(),sys.argv[2],allow_private=True).execute('validate_security_headers',{'grant':value['grant']})
except ExecutionRejected:
 print('execution-rejected')
else:
 raise SystemExit(2)
'''
    environment = {k:v for k,v in os.environ.items() if k == 'PATH'}
    child = subprocess.Popen([sys.executable, '-I', '-c', code,
        str(Path(__file__).resolve().parents[1]), str(path)], cwd=tmp_path, env=environment,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        child.stdin.write(json.dumps({'key': KEY.decode(), 'grant': token})); child.stdin.close(); child.stdin = None
        deadline = time.monotonic() + 4
        while not target[1]['requests'] and time.monotonic() < deadline:
            assert child.poll() is None
            time.sleep(.01)
        assert target[1]['requests']
        runner.cancel(token)
        output, _ = child.communicate(timeout=1)
        assert child.returncode == 0 and output.strip() == 'execution-rejected'
        assert len(target[1]['requests']) == 1
    finally:
        if child.poll() is None:child.kill()
        child.wait(timeout=2)


def test_cancellation_capacity_still_allows_revoking_existing_job(tmp_path, target):
    from aegis.mcp_scope import verify_claim
    token = grant(approved_task(target[0]))
    runner = Runner('owned-server', KEY, tmp_path / 'capacity.db', allow_private=True)
    runner.ledger.consume(verify_claim(token, KEY, 'owned-server'))
    with runner.ledger.connect() as db:
        db.executemany('INSERT INTO consumed VALUES (?,?)',
            [(f'{i:032x}', time.time() + 600) for i in range(9999)])
    assert runner.cancel(token)['cancelled'] is True
    other = approved_task(target[0]); other['id'] = 'other-capacity-task'
    with pytest.raises(ExecutionRejected, match='nonce_capacity'):
        runner.cancel(grant(other))
    assert not target[1]['requests']


def test_trusted_rpc_timeout_covers_reviewed_long_running_check(service, target):
    from aegis.mcp_scope import RequestLimits
    from aegis.remote_mcp import Client
    runner, original = service
    runner.ceiling = RequestLimits(request_timeout=20)
    sdk = Client(original.connection, operation_timeout=20)
    target[1]['delay'] = 13
    sdk.initialize(); sdk.list_tools()
    token = grant(approved_task(target[0], request_timeout=20))
    try:
        result = call(sdk, token, 'security_headers')
        assert result['isError'] is False
        assert len(target[1]['requests']) == 1
    finally:
        sdk.close()
