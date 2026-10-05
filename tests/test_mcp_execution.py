import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from aegis.__main__ import AegisServer
from aegis.mcp_execution_server import create_execution_app
from aegis.mcp_executor import ExecutionRejected, Runner
from aegis.mcp_execution_result import ExecutionResultError, validate_execution_response
from aegis.mcp_scope import RequestLimits, ScopeGrantError, issue_grant, sign_claim, verify_claim
from aegis.mcp_process import discover
from aegis.remote_mcp import Client, Connection
from aegis.runtime import ExecutionPolicy
from aegis.tool_contracts import contracts_for

KEY = b'owned-scope-signing-key-0123456789abcdef'
BEARER = 'owned-mcp-transport-bearer-0123456789abcdef'


@pytest.fixture
def target():
    state = {'requests': [], 'starts': [], 'redirect': None, 'delay': 0, 'echo': None, 'status': 200}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            state['requests'].append((self.path, self.headers.get('Authorization')))
            state['starts'].append(time.monotonic())
            time.sleep(state['delay'])
            raw = b'<html><a href="/approved/child">child</a><a href="/outside">outside</a></html>'
            status = 302 if state['redirect'] else state['status']
            self.send_response(status)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(raw)))
            if state['redirect']:
                self.send_header('Location', state['redirect'])
            if state['echo']:
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Credentials', state['echo'])
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}/approved', state
    server.shutdown(); server.server_close(); thread.join()


def approved_task(url, check='security_headers', **policy):
    return {'id': 'owned-approved-task', 'status': 'running', 'approved_at': time.time(),
            'checks': [check], 'tool_contracts': contracts_for([check]),
            'execution_policy': {**ExecutionPolicy().public(), **policy},
            'scope_snapshot': [{'id': 'owned-asset', 'name': 'Owned target', 'type': 'web',
                                'url': url, 'revision': 4, 'authorized': True, 'authorization_rules': []}]}


def grant(task, **kwargs):
    return issue_grant(task, 'owned-asset', task['checks'][0], 'owned-server', KEY,
                       allow_private=True, **kwargs)


@pytest.fixture
def service(tmp_path, monkeypatch):
    app = create_execution_app('owned-server', BEARER, KEY, tmp_path / 'server', allow_private=True,
                               credential_envs=('AEGIS_TEST_READER',))
    listener = socket.socket(); listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
    server = AegisServer(app, host='127.0.0.1', port=0, access_log=False, log_level='warning', timeout_graceful_shutdown=2)
    thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started:
        assert thread.is_alive() and time.monotonic() < deadline
        time.sleep(.01)
    monkeypatch.setenv('FIXTURE_SCOPE_BEARER', BEARER)
    sdk = Client(Connection(id='owned-server', url=f'http://127.0.0.1:{port}/mcp',
                            token_env='FIXTURE_SCOPE_BEARER', allow_private=True, lab_http=True))
    yield app.state.runner, sdk
    app.state.runner.stop.set(); server.should_exit = True
    thread.join(5); assert not thread.is_alive()


def call(sdk, token, check):
    args = {'grant': token}
    name = 'validate_' + check
    return sdk.call_tool(name, args, sdk.approve_call(name, args))


def test_actual_streamable_http_signed_scope_and_result(service, target):
    runner, sdk = service
    url, state = target
    sdk.initialize()
    tools = sdk.list_tools()
    assert len(tools) == 6
    assert tools[0]['_meta']['org.openaegis/scopedExecution']['server_id'] == 'owned-server'
    task = approved_task(url)
    token = grant(task)
    result = call(sdk, token, 'security_headers')
    assert result['isError'] is False
    output = result['structuredContent']
    assert validate_execution_response(token, KEY, 'owned-server', result, allow_private=True) == output
    assert output['grant_sha256'] == hashlib.sha256(token.encode()).hexdigest()
    assert output['asset_revision'] == 4 and output['scope_url'] == url and output['task_id'] == task['id']
    assert output['result'][0] and all(finding['check'] == 'security_headers' for finding in output['result'][0])
    assert state['requests'] == [('/approved', None)]
    assert output['traffic'][0]['url'] == url and 'headers' not in output['traffic'][0]
    assert token not in json.dumps(output) and BEARER not in json.dumps(output)
    # A fresh SDK review cannot revive execution authority already consumed server-side.
    assert call(sdk, token, 'security_headers')['isError'] is True
    assert len(state['requests']) == 1


def test_supervised_discovery_preserves_execution_profile_without_target_calls(service, target):
    _, sdk = service
    _, state = target
    catalog = discover(sdk.connection)
    assert len(catalog['tools']) == 6
    for tool in catalog['tools']:
        profile = tool['_meta']['org.openaegis/scopedExecution']
        assert profile['server_id'] == 'owned-server'
        assert profile['single_use'] is True and profile['method'] == 'GET'
    assert not state['requests']


@pytest.mark.parametrize('fault', ['signature', 'server', 'package', 'expiry', 'tool'])
def test_invalid_authority_rejected_before_target_request(tmp_path, target, fault):
    url, state = target
    runner = Runner('owned-server', KEY, tmp_path / 'consumed.db', allow_private=True)
    token = grant(approved_task(url))
    claim = verify_claim(token, KEY, 'owned-server')
    name = 'validate_security_headers'
    if fault == 'signature':
        token = token[:-1] + ('0' if token[-1] != '0' else '1')
    elif fault == 'server':
        token = sign_claim(claim.model_copy(update={'server_id': 'different-server'}), KEY)
    elif fault == 'package':
        token = sign_claim(claim.model_copy(update={'package_sha256': '0' * 64}), KEY)
    elif fault == 'expiry':
        token = sign_claim(claim.model_copy(update={'issued_at': int(time.time()) - 10,
                                                  'expires_at': int(time.time()) - 1}), KEY)
    else:
        name = 'validate_cookie_policy'
    with pytest.raises(ExecutionRejected):
        runner.execute(name, {'grant': token})
    assert not state['requests']


def test_duplicate_signed_issuance_has_same_nonce_and_survives_restart(tmp_path, target):
    url, state = target
    task = approved_task(url)
    first, second = grant(task), grant(task, ttl=120)
    assert verify_claim(first, KEY, 'owned-server').nonce == verify_claim(second, KEY, 'owned-server').nonce
    path = tmp_path / 'consumed.db'
    Runner('owned-server', KEY, path, allow_private=True).execute('validate_security_headers', {'grant': first})
    with pytest.raises(ExecutionRejected, match='scope_grant_consumed'):
        Runner('owned-server', KEY, path, allow_private=True).execute('validate_security_headers', {'grant': second})
    assert len(state['requests']) == 1


def test_cross_process_ledger_instances_allow_only_one_attempt(tmp_path, target):
    url, state = target
    token = grant(approved_task(url))
    code = '''
import json, sys
sys.path.insert(0, sys.argv[1])
from aegis.mcp_executor import Runner, ExecutionRejected
value = json.load(sys.stdin)
try:
    Runner('owned-server', value['key'].encode(), sys.argv[2], allow_private=True).execute(
        'validate_security_headers', {'grant': value['grant']})
    print('executed')
except ExecutionRejected:
    print('rejected')
'''
    environment = {k: v for k, v in os.environ.items() if not k.startswith('AEGIS_')}
    processes = []
    try:
        for _ in range(2):
            process = subprocess.Popen([sys.executable, '-I', '-c', code,
                                        str(Path(__file__).resolve().parents[1]), str(tmp_path / 'consumed.db')],
                                       cwd=tmp_path, env=environment, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            processes.append(process)
            process.stdin.write(json.dumps({'key': KEY.decode(), 'grant': token}))
            process.stdin.close()
            process.stdin = None
        results = [process.communicate(timeout=15) for process in processes]
        assert all(process.returncode == 0 for process in processes), results
        assert sorted(out.strip() for out, _ in results) == ['executed', 'rejected']
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=3)
    assert len(state['requests']) == 1


def test_redirect_cannot_cross_signed_path_scope(tmp_path, target):
    url, state = target
    state['redirect'] = '/outside'
    runner = Runner('owned-server', KEY, tmp_path / 'consumed.db', allow_private=True)
    token = grant(approved_task(url))
    with pytest.raises(ExecutionRejected):
        runner.execute('validate_security_headers', {'grant': token})
    assert state['requests'] == [('/approved', None)]
    with pytest.raises(ExecutionRejected, match='scope_grant_consumed'):
        runner.execute('validate_security_headers', {'grant': token})


def test_private_target_requires_both_signed_and_server_permission(tmp_path, target):
    url, state = target
    task = approved_task(url)
    token = issue_grant(task, 'owned-asset', 'security_headers', 'owned-server', KEY, allow_private=False)
    with pytest.raises(ExecutionRejected):
        Runner('owned-server', KEY, tmp_path / 'a.db', allow_private=True).execute('validate_security_headers', {'grant': token})
    token = grant(task)
    with pytest.raises(ExecutionRejected):
        Runner('owned-server', KEY, tmp_path / 'b.db', allow_private=False).execute('validate_security_headers', {'grant': token})
    assert not state['requests']


def test_observed_links_are_scoped_and_do_not_create_requests(tmp_path, target):
    url, state = target
    runner = Runner('owned-server', KEY, tmp_path / 'consumed.db', allow_private=True)
    output = runner.execute('validate_endpoint_inventory', {'grant': grant(approved_task(url, 'endpoint_inventory'))})
    assert output['result'][1] == [url + '/child']
    assert state['requests'] == [('/approved', None)]


@pytest.mark.parametrize('status', [401, 404, 429, 500])
def test_non_success_base_response_cannot_complete_validation(tmp_path, target, status):
    url, state = target
    state['status'] = status
    token = grant(approved_task(url))
    runner = Runner('owned-server', KEY, tmp_path / 'consumed.db', allow_private=True)
    with pytest.raises(ExecutionRejected, match='target_unconfirmed'):
        runner.execute('validate_security_headers', {'grant': token})
    assert state['requests'] and all(path == '/approved' for path, _ in state['requests'])
    with pytest.raises(ExecutionRejected, match='scope_grant_consumed'):
        runner.execute('validate_security_headers', {'grant': token})


def test_test_credentials_require_execution_server_allowlist(tmp_path, target, monkeypatch):
    url, state = target
    monkeypatch.setenv('AEGIS_TEST_READER', 'Bearer owned-test-secret')
    task = approved_task(url, 'api_authorization')
    task['scope_snapshot'][0]['authorization_rules'] = [
        {'path': '/approved/reader', 'role': 'reader', 'expected_allowed': True,
         'credential_env': 'AEGIS_TEST_READER'}]
    token = grant(task)
    runner = Runner('owned-server', KEY, tmp_path / 'consumed.db', allow_private=True)
    with pytest.raises(ExecutionRejected, match='credential_permission'):
        runner.execute('validate_api_authorization', {'grant': token})
    assert not state['requests']
    permitted = Runner('owned-server', KEY, tmp_path / 'consumed.db', allow_private=True,
                       credential_envs=('AEGIS_TEST_READER',))
    output = permitted.execute('validate_api_authorization', {'grant': token})
    assert state['requests'] == [('/approved', None), ('/approved/reader', 'Bearer owned-test-secret')]
    assert 'owned-test-secret' not in json.dumps(output)


def test_known_secret_reflection_is_not_returned(tmp_path, target):
    url, state = target
    state['echo'] = BEARER
    runner = Runner('owned-server', KEY, tmp_path / 'consumed.db', allow_private=True, protected_values=(BEARER,))
    with pytest.raises(ExecutionRejected, match='secret_reflection'):
        runner.execute('validate_cors_policy', {'grant': grant(approved_task(url, 'cors_policy'))})


def test_deadline_interrupts_target_request_and_consumes_grant(tmp_path, target):
    url, state = target
    state['delay'] = .5
    runner = Runner('owned-server', KEY, tmp_path / 'consumed.db', allow_private=True,
                    ceiling=RequestLimits(task_timeout=.2))
    token = grant(approved_task(url))
    start = time.monotonic()
    with pytest.raises(ExecutionRejected):
        runner.execute('validate_security_headers', {'grant': token})
    assert time.monotonic() - start < .45
    with pytest.raises(ExecutionRejected, match='scope_grant_consumed'):
        runner.execute('validate_security_headers', {'grant': token})
    assert len(state['requests']) == 1


def test_transport_bearer_origin_and_body_contract(service):
    _, sdk = service
    body = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list', 'params': {}}
    with httpx.Client(trust_env=False) as client:
        assert client.post(sdk.connection.url, json=body).status_code == 401
        headers = {'Authorization': 'Bearer ' + BEARER, 'MCP-Protocol-Version': '2025-11-25'}
        assert client.post(sdk.connection.url, json=body, headers={**headers, 'Origin': 'https://evil.invalid', 'Host': 'evil.invalid'}).status_code == 403
        assert client.post(sdk.connection.url, content=b' ' * 65537, headers={**headers, 'Content-Type': 'application/json'}).status_code == 400
        bad = {**body, 'id': True}
        assert client.post(sdk.connection.url, json=bad, headers=headers).json()['error']['code'] == -32600


@pytest.mark.parametrize('status', ['pending', 'completed', 'failed', 'stopped'])
def test_signer_refuses_unapproved_or_finished_task(target, status):
    task = approved_task(target[0]); task['status'] = status
    with pytest.raises(ScopeGrantError):
        grant(task)


def test_signed_rate_and_request_budget_are_enforced(tmp_path, target):
    url, state = target
    task = approved_task(url, 'api_authorization', target_rps=5.0)
    task['scope_snapshot'][0]['authorization_rules'] = [
        {'path': '/approved/reader', 'role': 'reader', 'expected_allowed': True}]
    runner = Runner('owned-server', KEY, tmp_path / 'consumed.db', allow_private=True,
                    ceiling=RequestLimits(target_rps=20.0))
    output = runner.execute('validate_api_authorization', {'grant': grant(task)})
    assert output['effective_limits']['target_rps'] == 5.0
    assert len(state['starts']) == 2 and state['starts'][1] - state['starts'][0] >= .17
    task['id'] = 'different-approved-task'
    task['execution_policy']['request_budget'] = 1
    with pytest.raises(ExecutionRejected):
        runner.execute('validate_api_authorization', {'grant': grant(task)})
    assert len(state['requests']) == 3  # Only the new base GET; its rule GET was denied.


@pytest.mark.parametrize('fault', ['revision', 'identity', 'traffic_scope', 'method', 'headers', 'result_check', 'is_error', 'limits', 'failed_body_hash'])
def test_receiver_rejects_whole_mismatched_result(tmp_path, target, fault):
    url, _ = target
    task = approved_task(url)
    if fault == 'revision':
        task['scope_snapshot'][0]['revision'] = 1
    token = grant(task)
    output = Runner('owned-server', KEY, tmp_path / 'consumed.db', allow_private=True).execute(
        'validate_security_headers', {'grant': token})
    response = {'isError': False, 'content': [], 'structuredContent': output}
    assert validate_execution_response(token, KEY, 'owned-server', response, allow_private=True) == output
    if fault == 'revision':
        output['asset_revision'] = True
    elif fault == 'identity':
        output['task_id'] = 'different-task'
    elif fault == 'traffic_scope':
        output['traffic'][0]['url'] = url.replace('/approved', '/outside')
    elif fault == 'method':
        output['traffic'][0]['method'] = 'POST'
    elif fault == 'headers':
        output['traffic'][0]['headers'] = {'Authorization': 'do-not-store'}
    elif fault == 'result_check':
        output['result'][0][0]['check'] = 'cookie_policy'
    elif fault == 'is_error':
        response['isError'] = True
    elif fault == 'failed_body_hash':
        output['traffic'][0]['status'] = 0
        output['traffic'][0]['body_sha256'] = {'untrusted': 'nested-data'}
    else:
        output['effective_limits']['request_budget'] += 1
    with pytest.raises(ExecutionResultError, match='remote_result_unconfirmed'):
        validate_execution_response(token, KEY, 'owned-server', response, allow_private=True)


def test_server_keys_cannot_be_forwarded_as_target_test_credentials(tmp_path, target, monkeypatch):
    url, state = target
    task = approved_task(url, 'api_authorization')
    task['scope_snapshot'][0]['authorization_rules'] = [
        {'path': '/approved/reader', 'role': 'reader', 'expected_allowed': True, 'credential_env': 'AEGIS_TEST_READER'}]
    monkeypatch.setenv('AEGIS_TEST_READER', 'Bearer ' + BEARER)
    runner = Runner('owned-server', KEY, tmp_path / 'consumed.db', allow_private=True,
                    credential_envs=('AEGIS_TEST_READER',), protected_values=(BEARER,))
    with pytest.raises(ExecutionRejected, match='credential_configuration'):
        runner.execute('validate_api_authorization', {'grant': grant(task)})
    assert not state['requests']


def test_rotating_scope_key_does_not_reexecute_same_approval(tmp_path, target):
    url, state = target
    task = approved_task(url)
    path = tmp_path / 'consumed.db'
    Runner('owned-server', KEY, path, allow_private=True).execute('validate_security_headers', {'grant': grant(task)})
    rotated = b'owned-rotated-signing-key-0123456789abcdef'
    token = issue_grant(task, 'owned-asset', 'security_headers', 'owned-server', rotated, allow_private=True)
    with pytest.raises(ExecutionRejected, match='scope_grant_consumed'):
        Runner('owned-server', rotated, path, allow_private=True).execute('validate_security_headers', {'grant': token})
    assert len(state['requests']) == 1


@pytest.mark.parametrize('budget', [True, False, 0, -1, 2.5, '1', 25])
def test_scope_factory_cannot_increase_or_coerce_approved_request_budget(target, budget):
    with pytest.raises(ScopeGrantError):
        grant(approved_task(target[0], request_budget=24), request_budget=budget)
    assert not target[1]['requests']


def test_scope_factory_can_only_reduce_shared_asset_budget(target):
    token = grant(approved_task(target[0], request_budget=24), request_budget=1)
    assert verify_claim(token, KEY, 'owned-server').limits.request_budget == 1
    assert not target[1]['requests']
