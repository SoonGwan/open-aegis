"""Bounded Streamable HTTP client foundation; not an application tool registry.

Grants bind a reviewed tool definition and exact arguments to one client session.
They do not establish application roles or constrain a remote server's effects.
"""
import hashlib
import http.client
import json
import math
import os
import secrets
import threading
import time
from contextlib import contextmanager
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .network import PinnedHTTP, PinnedHTTPS, normalize_url, resolve
from .runtime import RequestGuard, TaskControl

VERSIONS = ('2025-11-25', '2025-06-18', '2025-03-26')
MAX_BYTES = 512 * 1024
MAX_ARGUMENT_BYTES = 64 * 1024


class RemoteMCPError(ValueError):
    """Only fixed codes escape the transport, never peer error text or credentials."""


class Connection(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    id: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_.-]+$')
    url: str = Field(max_length=2000)
    token_env: str | None = Field(default=None, min_length=1, max_length=100,
                                 pattern=r'^[A-Za-z_][A-Za-z0-9_]*$')
    allow_private: bool = False
    lab_http: bool = False

    @field_validator('url')
    @classmethod
    def endpoint(cls, value):
        if any(ord(c) <= 32 or ord(c) == 127 for c in value) or '?' in value or '#' in value:
            raise ValueError('endpoint')
        return normalize_url(value)


def _check_json(value):
    stack = [(value, 0)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if depth > 16 or count > 4096:
            raise RemoteMCPError('json_budget')
        if isinstance(item, dict):
            if any(type(key) is not str for key in item):
                raise RemoteMCPError('json_shape')
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
        elif type(item) not in (str, int, float, bool, type(None)):
            raise RemoteMCPError('json_shape')
        elif type(item) is float and not math.isfinite(item):
            raise RemoteMCPError('json_shape')


def _encode(value, limit=MAX_BYTES):
    _check_json(value)
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                         allow_nan=False).encode('utf-8')
    except (ValueError, UnicodeError, RecursionError):
        raise RemoteMCPError('json_shape') from None
    if len(raw) > limit:
        raise RemoteMCPError('byte_budget')
    return raw


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RemoteMCPError('duplicate_key')
        result[key] = value
    return result


def _decode(raw):
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        _check_json(value)
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise RemoteMCPError('invalid_json') from None


def _digest(value):
    return hashlib.sha256(_encode(value)).hexdigest()


def _sse_messages(response):
    """Bound the entire POST stream, including comments and empty priming events."""
    total, line, data, skip_lf, first_line = 0, bytearray(), [], False, True
    while chunk := response.read1(4096):
        total += len(chunk)
        if total > MAX_BYTES:
            raise RemoteMCPError('byte_budget')
        for byte in chunk:
            if skip_lf and byte == 10:
                skip_lf = False
                continue
            skip_lf = False
            if byte not in (10, 13):
                line.append(byte)
                continue
            skip_lf = byte == 13
            raw = bytes(line)
            line.clear()
            if first_line:
                raw = raw.removeprefix(b'\xef\xbb\xbf')
                first_line = False
            if not raw:
                if data:
                    payload = b'\n'.join(data)
                    data.clear()
                    if payload:
                        yield _decode(payload)
            elif raw == b'data' or raw.startswith(b'data:'):
                field = raw[5:] if raw.startswith(b'data:') else b''
                data.append(field[1:] if field.startswith(b' ') else field)
    raise RemoteMCPError('stream_ended')


class Client:
    def __init__(self, connection: Connection, *, operation_timeout=12):
        if type(operation_timeout) not in (int, float) or not .1 <= operation_timeout <= 300:
            raise RemoteMCPError('operation_timeout')
        self.operation_timeout = operation_timeout
        p = urlsplit(connection.url)
        if p.scheme != 'https' and not (connection.lab_http and connection.allow_private
                                       and p.hostname in ('127.0.0.1', '::1')):
            raise RemoteMCPError('tls_required')
        self.connection = connection
        self._lock = threading.Lock()
        self._session = None
        self._version = None
        self._credential = None
        self._server = None
        self._next_id = 0
        self._grants = {}
        self._tools = {}

    def _control(self, control):
        return TaskControl(stop=control.stop if control else None,
                           deadline=min(time.monotonic() + self.operation_timeout, control.deadline)
                           if control and control.deadline is not None else time.monotonic() + self.operation_timeout)

    @contextmanager
    def _operation(self, control):
        control = self._control(control)
        try:
            while True:
                control.check()
                if self._lock.acquire(blocking=False):
                    break
                control.wait(.02)
        except (TimeoutError, InterruptedError):
            raise RemoteMCPError('admission_timeout') from None
        try:
            yield control
        finally:
            self._lock.release()

    def _credentials(self):
        token = os.environ.get(self.connection.token_env, '') if self.connection.token_env else ''
        if self.connection.token_env and (not token or len(token) > 4096
                                         or any(not 33 <= ord(c) <= 126 for c in token)):
            raise RemoteMCPError('credential_unavailable')
        return token, hashlib.sha256(token.encode()).hexdigest()

    def _invalidate(self):
        self._session = self._version = self._credential = self._server = None
        self._grants.clear()
        self._tools.clear()

    def _exchange(self, message, control, *, method='POST', initializing=False):
        body = _encode(message) if message is not None else None
        p = urlsplit(self.connection.url)
        port = p.port or (443 if p.scheme == 'https' else 80)
        connection = None
        try:
            token, fingerprint = self._credentials()
            if not initializing and self._credential != fingerprint:
                raise RemoteMCPError('credential_changed')
            address = resolve(p.hostname, port, self.connection.allow_private,
                              control=control, timeout=control.timeout(4))[0]
            cls = PinnedHTTPS if p.scheme == 'https' else PinnedHTTP
            connection = cls(p.hostname, port, address, timeout=control.timeout(self.operation_timeout))
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
                       'Accept-Encoding': 'identity', 'User-Agent': 'OpenAegis-MCP/0.2'}
            if token:
                headers['Authorization'] = 'Bearer ' + token
            if not initializing:
                headers['MCP-Protocol-Version'] = self._version
                if self._session:
                    headers['MCP-Session-Id'] = self._session
            with RequestGuard(connection, control, self.operation_timeout) as guard:
                connection.request(method, p.path, body=body, headers=headers)
                guard.sock = connection.sock
                response = connection.getresponse()
                if method == 'DELETE' and response.status in (200, 202, 204, 404, 405):
                    return None
                if response.status == 404 and not initializing:
                    raise RemoteMCPError('session_lost')
                if response.status in (401, 403):
                    raise RemoteMCPError('authentication_rejected')
                notification = message is not None and 'id' not in message
                if response.status != (202 if notification else 200):
                    raise RemoteMCPError('http_status')
                if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
                    raise RemoteMCPError('content_encoding')
                sessions = response.headers.get_all('MCP-Session-Id', [])
                if len(sessions) > 1:
                    raise RemoteMCPError('session_header')
                if sessions:
                    session = sessions[0]
                    if not session or len(session) > 256 or any(not 33 <= ord(c) <= 126 for c in session):
                        raise RemoteMCPError('session_header')
                    if not initializing and session != self._session:
                        raise RemoteMCPError('session_changed')
                    if initializing:
                        self._session = session
                if notification:
                    if response.read(1):
                        raise RemoteMCPError('notification_body')
                    return None
                kind = response.getheader('Content-Type', '').split(';')[0].strip().lower()
                if kind == 'application/json':
                    raw = response.read(MAX_BYTES + 1)
                    if len(raw) > MAX_BYTES:
                        raise RemoteMCPError('byte_budget')
                    return self._reply(_decode(raw), message['id'])
                if kind == 'text/event-stream':
                    for value in _sse_messages(response):
                        if not isinstance(value, dict) or value.get('jsonrpc') != '2.0':
                            raise RemoteMCPError('rpc_shape')
                        if 'id' not in value and isinstance(value.get('method'), str):
                            if ('result' in value or 'error' in value
                                    or ('params' in value and not isinstance(value['params'], dict))):
                                raise RemoteMCPError('rpc_shape')
                            if value['method'] == 'notifications/tools/list_changed':
                                self._grants.clear()
                            continue
                        return self._reply(value, message['id'])
                raise RemoteMCPError('content_type')
        except RemoteMCPError:
            self._invalidate()
            raise
        except (OSError, ValueError, TimeoutError, InterruptedError, http.client.HTTPException):
            self._invalidate()
            raise RemoteMCPError('transport_failed') from None
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _reply(value, request_id):
        if (not isinstance(value, dict) or value.get('jsonrpc') != '2.0'
                or type(value.get('id')) is not int or value['id'] != request_id
                or ('result' in value) == ('error' in value) or 'method' in value):
            raise RemoteMCPError('rpc_shape')
        if 'error' in value:
            raise RemoteMCPError('rpc_error')
        if not isinstance(value['result'], dict):
            raise RemoteMCPError('result_shape')
        return value['result']

    def _rpc(self, method, params, control, initializing=False):
        self._next_id += 1
        return self._exchange({'jsonrpc': '2.0', 'id': self._next_id, 'method': method,
                               'params': params}, control, initializing=initializing)

    def initialize(self, control=None):
        with self._operation(control) as control:
            self._invalidate()
            try:
                _, fingerprint = self._credentials()
                result = self._rpc('initialize', {'protocolVersion': VERSIONS[0], 'capabilities': {},
                                   'clientInfo': {'name': 'OpenAegis', 'version': '0.2.0a1'}}, control, True)
                if (result.get('protocolVersion') not in VERSIONS
                        or not isinstance(result.get('capabilities'), dict)
                        or not isinstance(result['capabilities'].get('tools'), dict)
                        or not isinstance(result.get('serverInfo'), dict)
                        or not all(isinstance(result['serverInfo'].get(k), str)
                                   and result['serverInfo'][k] for k in ('name', 'version'))):
                    raise RemoteMCPError('initialize_contract')
                self._version, self._credential = result['protocolVersion'], fingerprint
                self._server = result['serverInfo']
                self._exchange({'jsonrpc': '2.0', 'method': 'notifications/initialized'}, control)
                return _decode(_encode(result))
            except RemoteMCPError:
                self._invalidate()
                raise

    def _list(self, control):
        if not self._version:
            raise RemoteMCPError('not_initialized')
        tools, seen, cursor = {}, set(), None
        for _ in range(10):
            result = self._rpc('tools/list', {'cursor': cursor} if cursor else {}, control)
            rows = result.get('tools')
            if not isinstance(rows, list):
                raise RemoteMCPError('tools_contract')
            for row in rows:
                if (not isinstance(row, dict) or not isinstance(row.get('name'), str)
                        or not 1 <= len(row['name']) <= 128 or row['name'] in tools
                        or not isinstance(row.get('inputSchema'), dict)
                        or row['inputSchema'].get('type') != 'object'):
                    raise RemoteMCPError('tools_contract')
                schema = row['inputSchema']
                stack = [(schema, 0, ())]
                expanded = 0
                while stack:
                    item, depth, ancestors = stack.pop()
                    expanded += 1
                    if expanded > 4096 or depth > 16 or id(item) in ancestors:
                        raise RemoteMCPError('schema_expansion_budget')
                    if isinstance(item, dict):
                        if '$dynamicRef' in item:
                            raise RemoteMCPError('dynamic_schema_reference')
                        if '$ref' in item:
                            ref = item['$ref']
                            if not isinstance(ref, str) or not ref.startswith('#'):
                                raise RemoteMCPError('external_schema_reference')
                            if (ref != '#' and not ref.startswith('#/')) or '%' in ref:
                                raise RemoteMCPError('schema_reference')
                            target = schema
                            try:
                                for part in ref[2:].split('/') if ref != '#' else []:
                                    if '~' in part.replace('~0', '').replace('~1', ''):
                                        raise ValueError()
                                    key = part.replace('~1', '/').replace('~0', '~')
                                    target = target[int(key)] if isinstance(target, list) else target[key]
                            except (KeyError, IndexError, TypeError, ValueError):
                                raise RemoteMCPError('schema_reference') from None
                            if not isinstance(target, (dict, bool)):
                                raise RemoteMCPError('schema_reference')
                            stack.append((target, depth + 1, ancestors + (id(item),)))
                        if '$id' in item:
                            raise RemoteMCPError('schema_identifier')
                        stack.extend((child, depth + 1, ancestors + (id(item),))
                                     for child in item.values() if isinstance(child, (dict, list)))
                    elif isinstance(item, list):
                        stack.extend((child, depth + 1, ancestors + (id(item),))
                                     for child in item if isinstance(child, (dict, list)))
                if schema.get('$schema', 'https://json-schema.org/draft/2020-12/schema') != 'https://json-schema.org/draft/2020-12/schema':
                    raise RemoteMCPError('schema_dialect')
                try:
                    Draft202012Validator.check_schema(schema)
                except Exception:
                    raise RemoteMCPError('schema_contract') from None
                tools[row['name']] = row
                if len(tools) > 100:
                    raise RemoteMCPError('tools_budget')
            _encode(list(tools.values()))
            cursor = result.get('nextCursor')
            if cursor is None:
                self._tools = tools
                return tools
            if not isinstance(cursor, str) or not 1 <= len(cursor) <= 2048 or cursor in seen:
                raise RemoteMCPError('cursor_contract')
            seen.add(cursor)
        raise RemoteMCPError('page_budget')

    def list_tools(self, control=None):
        with self._operation(control) as control:
            try:
                return _decode(_encode(list(self._list(control).values())))
            except RemoteMCPError:
                self._invalidate()
                raise

    def _binding(self, name, arguments):
        if not isinstance(name, str) or type(arguments) is not dict or name not in self._tools:
            raise RemoteMCPError('approval_input')
        _encode(arguments, MAX_ARGUMENT_BYTES)
        try:
            Draft202012Validator(self._tools[name]['inputSchema']).validate(arguments)
        except Exception:
            raise RemoteMCPError('arguments_contract') from None
        return _digest({'connection': self.connection.model_dump(), 'credential': self._credential,
                        'session': self._session, 'version': self._version, 'server': self._server,
                        'tool': self._tools[name], 'catalog_sha256': _digest(self._tools), 'arguments': arguments})

    def approve_call(self, name, arguments, control=None):
        """Trusted caller attests it reviewed the latest listed definition and input.

        Application registration, actor authorization and audit are not supplied here.
        """
        with self._operation(control):
            arguments = _decode(_encode(arguments, MAX_ARGUMENT_BYTES))
            binding = self._binding(name, arguments)
            if len(self._grants) >= 16:
                raise RemoteMCPError('grant_budget')
            grant = secrets.token_urlsafe(32)
            self._grants[grant] = binding
            return grant

    def call_tool(self, name, arguments, grant, control=None):
        with self._operation(control) as control:
            arguments = _decode(_encode(arguments, MAX_ARGUMENT_BYTES))
            expected = self._grants.get(grant) if isinstance(grant, str) else None
            if expected is None or expected != self._binding(name, arguments):
                raise RemoteMCPError('approval_required')
            try:
                self._list(control)
            except RemoteMCPError:
                self._invalidate()
                raise
            if self._grants.pop(grant, None) != expected or expected != self._binding(name, arguments):
                raise RemoteMCPError('approval_changed')
            result = self._rpc('tools/call', {'name': name, 'arguments': arguments}, control)
            if (not isinstance(result.get('content'), list)
                    or any(not isinstance(c, dict) or not isinstance(c.get('type'), str)
                           for c in result['content'])
                    or ('isError' in result and type(result['isError']) is not bool)
                    or ('structuredContent' in result and not isinstance(result['structuredContent'], dict))):
                raise RemoteMCPError('tool_result_contract')
            return result

    def cancel_scoped(self, token, control=None):
        """Fixed server extension: revoke existing signed authority, never execute."""
        with self._operation(control) as control:
            if not self._version:
                raise RemoteMCPError('not_initialized')
            if not isinstance(token, str) or not 1 <= len(token) <= 44000:
                raise RemoteMCPError('cancellation_authority')
            result = self._rpc('aegis/cancel', {'grant': token}, control)
            expected = {'format': 'aegis-mcp-cancellation-v1',
                        'grant_sha256': hashlib.sha256(token.encode()).hexdigest(), 'cancelled': True}
            if _encode(result) != _encode(expected):
                raise RemoteMCPError('cancellation_unconfirmed')
            return result

    def close(self, control=None):
        with self._operation(control) as control:
            try:
                if self._version and self._session:
                    self._exchange(None, control, method='DELETE')
            finally:
                self._invalidate()
