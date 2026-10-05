import json
import ssl
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from aegis.remote_mcp import Client, Connection, RemoteMCPError
from aegis.runtime import TaskControl


@pytest.fixture
def peer(monkeypatch, tmp_path, request):
    state = {'calls': [], 'mode': 'json', 'revision': '1', 'token': 'fixture-secret',
             'session': 'fixture-session-secret', 'status': 200, 'pages': False}
    monkeypatch.setenv('FIXTURE_MCP_TOKEN', state['token'])

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_DELETE(self):
            state['calls'].append(('DELETE', dict(self.headers), None))
            self.send_response(405)
            self.send_header('Content-Length', '0')
            self.end_headers()

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state['calls'].append(('POST', dict(self.headers), request))
            method = request['method']
            if method == 'notifications/initialized':
                self.send_response(202)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            if method == 'initialize':
                result = {'protocolVersion': state.get('version', '2025-11-25'),
                          'capabilities': {'tools': {}},
                          'serverInfo': {'name': 'owned-fixture', 'version': '1'}}
            elif method == 'tools/list':
                schema = state.get('schema', {'type': 'object', 'properties': {'url': {'type': 'string'}},
                                              'required': ['url'], 'additionalProperties': False})
                result = {'tools': [{'name': 'inspect', 'description': state['revision'],
                                    'inputSchema': schema, 'annotations': {'readOnlyHint': True}}]}
                if state['pages']:
                    if request['params'].get('cursor'):
                        result['tools'][0]['name'] = 'second'
                    if state['pages'] == 'loop' or not request['params'].get('cursor'):
                        result['nextCursor'] = 'opaque'
            else:
                result = state.get('result', {'content': [{'type': 'text', 'text': 'fixture result'}]})
            value = {'jsonrpc': '2.0', 'id': request['id'], 'result': result}
            if state.get('wrong_id'):
                value['id'] = True
            if state.get('rpc_error'):
                value = {'jsonrpc': '2.0', 'id': request['id'],
                         'error': {'code': -32000, 'message': state['token'] + state['session']}}
            raw = json.dumps(value).encode()
            kind = 'application/json'
            if state['mode'] == 'sse':
                kind = 'text/event-stream'
                notification = {'jsonrpc': '2.0', 'method': 'notifications/tools/list_changed'}
                prefix = b': comment\r\nid: prime\r\ndata:\r\n\r\n'
                if state.get('list_changed'):
                    prefix += b'data: ' + json.dumps(notification).encode() + b'\r\n\r\n'
                raw = prefix + b'data: ' + raw + b'\r\n\r\n'
            elif state['mode'] == 'duplicate':
                raw = b'{"jsonrpc":"2.0","id":1,"id":2,"result":{}}'
            elif state['mode'] == 'oversize':
                raw = b' ' * (512 * 1024 + 1)
            elif state['mode'] == 'bad_type':
                kind = 'text/html'
            elif state['mode'] == 'slow':
                time.sleep(.25)
            status = state.get('call_status', state['status']) if method == 'tools/call' else state['status']
            if method == 'initialize':
                status = 200
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(raw)))
            if method == 'initialize':
                self.send_header('MCP-Session-Id', state['session'])
            if status == 302:
                self.send_header('Location', 'http://127.0.0.1:1/do-not-follow')
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    tls = getattr(request, 'param', None)
    state['tls'] = tls
    if tls:
        cert, key = tmp_path / 'peer.pem', tmp_path / 'peer.key'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '2',
                        '-subj', '/CN=owned-mcp-fixture', '-addext',
                        'subjectAltName=' + ('DNS:wrong.invalid' if tls == 'wrong_host' else 'IP:127.0.0.1'),
                        '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)
        if tls != 'untrusted':
            monkeypatch.setenv('SSL_CERT_FILE', str(cert))
        else:
            monkeypatch.delenv('SSL_CERT_FILE', raising=False)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    scheme = 'https' if tls else 'http'
    client = Client(Connection(id='fixture', url=f'{scheme}://127.0.0.1:{server.server_port}/mcp',
                               token_env='FIXTURE_MCP_TOKEN', allow_private=True, lab_http=True))
    yield state, client
    server.shutdown()
    server.server_close()
    thread.join()


def requests(state, method):
    return [request for _, _, request in state['calls'] if request and request['method'] == method]


@pytest.mark.parametrize('mode', ['json', 'sse'])
def test_initialize_list_review_call_and_close(peer, mode):
    state, client = peer
    state['mode'] = mode
    assert client.initialize()['protocolVersion'] == '2025-11-25'
    tools = client.list_tools()
    assert tools[0]['name'] == 'inspect'
    args = {'url': 'https://owned.invalid/'}
    grant = client.approve_call('inspect', args)
    assert client.call_tool('inspect', args, grant)['content'][0]['text'] == 'fixture result'
    with pytest.raises(RemoteMCPError, match='approval_required'):
        client.call_tool('inspect', args, grant)
    assert len(requests(state, 'tools/call')) == 1
    initialize_headers = state['calls'][0][1]
    assert 'MCP-Session-Id' not in initialize_headers
    for _, headers, request in state['calls'][1:]:
        assert headers['MCP-Session-Id'] == state['session']
        assert headers['MCP-Protocol-Version'] == '2025-11-25'
        assert headers['Authorization'] == 'Bearer fixture-secret'
        assert headers['Accept'] == 'application/json, text/event-stream'
    client.close()
    assert state['calls'][-1][0] == 'DELETE'
    with pytest.raises(RemoteMCPError, match='not_initialized'):
        client.list_tools()


def test_exact_arguments_and_metadata_reapproval(peer):
    state, client = peer
    client.initialize()
    client.list_tools()
    args = {'url': 'https://owned.invalid/'}
    grant = client.approve_call('inspect', args)
    before = len(state['calls'])
    with pytest.raises(RemoteMCPError, match='approval_required'):
        client.call_tool('inspect', {'url': 'https://other.invalid/'}, grant)
    assert len(state['calls']) == before
    state['revision'] = '2'
    with pytest.raises(RemoteMCPError, match='approval_changed'):
        client.call_tool('inspect', args, grant)
    assert not requests(state, 'tools/call')
    grant = client.approve_call('inspect', args)
    client.call_tool('inspect', args, grant)
    assert len(requests(state, 'tools/call')) == 1


def test_readonly_hint_does_not_authorize_call(peer):
    state, client = peer
    client.initialize()
    client.list_tools()
    with pytest.raises(RemoteMCPError, match='approval_required'):
        client.call_tool('inspect', {'url': 'https://owned.invalid/'}, None)
    assert not requests(state, 'tools/call')


def test_rotation_prevents_wire_call(peer, monkeypatch):
    state, client = peer
    client.initialize()
    client.list_tools()
    args = {'url': 'https://owned.invalid/'}
    grant = client.approve_call('inspect', args)
    before = len(state['calls'])
    monkeypatch.setenv('FIXTURE_MCP_TOKEN', 'rotated')
    with pytest.raises(RemoteMCPError, match='credential_changed'):
        client.call_tool('inspect', args, grant)
    assert len(state['calls']) == before
    assert not client._grants


@pytest.mark.parametrize('status', [302, 401, 403, 404, 500])
def test_transport_failure_revokes_and_never_replays(peer, status):
    state, client = peer
    client.initialize()
    client.list_tools()
    args = {'url': 'https://owned.invalid/'}
    grant = client.approve_call('inspect', args)
    state['status'] = status
    with pytest.raises(RemoteMCPError):
        client.call_tool('inspect', args, grant)
    assert not requests(state, 'tools/call')
    assert not client._grants
    assert len(requests(state, 'tools/list')) == 2


@pytest.mark.parametrize('mode', ['duplicate', 'oversize', 'bad_type'])
def test_reject_invalid_response(peer, mode):
    state, client = peer
    state['mode'] = mode
    with pytest.raises(RemoteMCPError):
        client.initialize()
    assert client._version is None


def test_rpc_error_text_is_not_exposed(peer):
    state, client = peer
    state['rpc_error'] = True
    with pytest.raises(RemoteMCPError) as exc:
        client.initialize()
    assert str(exc.value) == 'rpc_error'
    assert state['token'] not in str(exc.value)
    assert state['session'] not in str(exc.value)


def test_pagination_and_cursor_loop(peer):
    state, client = peer
    client.initialize()
    state['pages'] = True
    assert [tool['name'] for tool in client.list_tools()] == ['inspect', 'second']
    state['pages'] = 'loop'
    with pytest.raises(RemoteMCPError, match='cursor_contract'):
        client.list_tools()
    assert client._version is None


@pytest.mark.parametrize('schema', [
    {'type': 'object', '$ref': 'https://127.0.0.1:1/schema'},
    {'type': 'object', '$id': 'https://127.0.0.1:1/schema'},
    {'type': 'object', 'properties': {'x': {'$dynamicRef': 'file:///tmp/no'}}},
])
def test_schema_cannot_fetch_external_resources(peer, schema):
    state, client = peer
    client.initialize()
    state['schema'] = schema
    with pytest.raises(RemoteMCPError):
        client.list_tools()
    assert len(state['calls']) == 3


def test_argument_schema_and_input_budget(peer):
    _, client = peer
    client.initialize()
    client.list_tools()
    with pytest.raises(RemoteMCPError, match='arguments_contract'):
        client.approve_call('inspect', {'url': 42})
    with pytest.raises(RemoteMCPError, match='byte_budget'):
        client.approve_call('inspect', {'url': 'x' * 65536})


def test_list_changed_notification_revokes_review(peer):
    state, client = peer
    client.initialize()
    client.list_tools()
    args = {'url': 'https://owned.invalid/'}
    grant = client.approve_call('inspect', args)
    state.update(mode='sse', list_changed=True)
    with pytest.raises(RemoteMCPError, match='approval_changed'):
        client.call_tool('inspect', args, grant)
    assert not requests(state, 'tools/call')


def test_whole_operation_deadline(peer):
    state, client = peer
    client.initialize()
    state['mode'] = 'slow'
    control = TaskControl(deadline=time.monotonic() + .08)
    start = time.monotonic()
    with pytest.raises(RemoteMCPError, match='transport_failed'):
        client.list_tools(control)
    assert time.monotonic() - start < .5
    assert not client._grants


@pytest.mark.parametrize('url', ['https://example.invalid/mcp?x=1', 'https://example.invalid/mcp#x',
                               'https://user:pass@example.invalid/mcp', 'https://example.invalid/\n'])
def test_endpoint_admission(url):
    with pytest.raises(ValueError):
        Connection(id='test', url=url)


def test_http_requires_explicit_loopback_lab():
    with pytest.raises(RemoteMCPError, match='tls_required'):
        Client(Connection(id='test', url='http://127.0.0.1/mcp'))
    with pytest.raises(RemoteMCPError, match='tls_required'):
        Client(Connection(id='test', url='http://example.invalid/mcp', allow_private=True, lab_http=True))


def test_private_dns_blocked_before_request(peer):
    state, client = peer
    client = Client(Connection(id='fixture', url=client.connection.url.replace('http:', 'https:')))
    with pytest.raises(RemoteMCPError, match='transport_failed'):
        client.initialize()
    assert not state['calls']


@pytest.mark.parametrize('peer', ['trusted', 'untrusted', 'wrong_host'], indirect=True)
def test_tls_trust_and_host_before_credential_delivery(peer):
    state, client = peer
    if state['tls'] != 'trusted':
        with pytest.raises(RemoteMCPError, match='transport_failed'):
            client.initialize()
        assert not state['calls']
        return
    client.initialize()
    assert len(state['calls']) == 2
    client.list_tools()
    args = {'url': 'https://owned.invalid/'}
    client.call_tool('inspect', args, client.approve_call('inspect', args))
    assert len(requests(state, 'tools/call')) == 1


@pytest.mark.parametrize('version', ['2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05'])
def test_version_negotiation(peer, version):
    state, client = peer
    state['version'] = version
    if version == '2024-11-05':
        with pytest.raises(RemoteMCPError, match='initialize_contract'):
            client.initialize()
        assert len(state['calls']) == 1
    else:
        client.initialize()
        client.list_tools()
        assert state['calls'][-1][1]['MCP-Protocol-Version'] == version


def test_call_error_consumes_grant_without_retry(peer):
    state, client = peer
    client.initialize()
    client.list_tools()
    args = {'url': 'https://owned.invalid/'}
    grant = client.approve_call('inspect', args)
    state['call_status'] = 500
    with pytest.raises(RemoteMCPError, match='http_status'):
        client.call_tool('inspect', args, grant)
    with pytest.raises(RemoteMCPError, match='approval_required'):
        client.call_tool('inspect', args, grant)
    assert len(requests(state, 'tools/call')) == 1


@pytest.mark.parametrize('result', [{'content': 'bad'}, {'content': [], 'isError': 'false'},
                                  {'content': [], 'structuredContent': []}])
def test_invalid_tool_result_is_not_success(peer, result):
    state, client = peer
    client.initialize()
    client.list_tools()
    args = {'url': 'https://owned.invalid/'}
    grant = client.approve_call('inspect', args)
    state['result'] = result
    with pytest.raises(RemoteMCPError, match='tool_result_contract'):
        client.call_tool('inspect', args, grant)
    assert grant not in client._grants


def test_server_declared_tool_error_is_preserved(peer):
    state, client = peer
    client.initialize()
    client.list_tools()
    args = {'url': 'https://owned.invalid/'}
    state['result'] = {'content': [{'type': 'text', 'text': 'failed'}], 'isError': True}
    assert client.call_tool('inspect', args, client.approve_call('inspect', args))['isError'] is True


def test_concurrent_admission_respects_deadline(peer):
    state, client = peer
    client._lock.acquire()
    try:
        with pytest.raises(RemoteMCPError, match='admission_timeout'):
            client.initialize(TaskControl(deadline=time.monotonic() + .05))
        assert not state['calls']
    finally:
        client._lock.release()


def test_caller_mutation_during_refresh_cannot_change_approved_payload(peer, monkeypatch):
    state, client = peer
    client.initialize()
    client.list_tools()
    args = {'url': 'https://owned.invalid/'}
    grant = client.approve_call('inspect', args)
    original = client._rpc

    def mutate(method, params, control, initializing=False):
        if method == 'tools/list':
            args['url'] = 'https://changed.invalid/'
        return original(method, params, control, initializing)

    monkeypatch.setattr(client, '_rpc', mutate)
    client.call_tool('inspect', args, grant)
    assert requests(state, 'tools/call')[0]['params']['arguments']['url'] == 'https://owned.invalid/'


def test_local_schema_reference_validates_without_fetch(peer):
    state, client = peer
    state['schema'] = {'type': 'object', '$defs': {'url': {'type': 'string'}},
                       'properties': {'url': {'$ref': '#/$defs/url'}}, 'required': ['url']}
    client.initialize()
    client.list_tools()
    with pytest.raises(RemoteMCPError, match='arguments_contract'):
        client.approve_call('inspect', {'url': 42})
    args = {'url': 'https://owned.invalid/'}
    client.call_tool('inspect', args, client.approve_call('inspect', args))


def test_recursive_schema_is_rejected_before_validation(peer):
    state, client = peer
    state['schema'] = {'type': 'object', '$ref': '#'}
    client.initialize()
    with pytest.raises(RemoteMCPError, match='schema_expansion_budget'):
        client.list_tools()
    assert not requests(state, 'tools/call')


def test_sse_bom_cr_and_multiline_json():
    import io
    from aegis.remote_mcp import _sse_messages

    response = io.BytesIO(b'\xef\xbb\xbf: comment\rdata: {"jsonrpc": "2.0",\rdata: "id": 1, "result": {}}\r\r')
    assert next(_sse_messages(response)) == {'jsonrpc': '2.0', 'id': 1, 'result': {}}
