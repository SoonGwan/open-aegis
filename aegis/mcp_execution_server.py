"""Authenticated Streamable HTTP server for signed, reviewed scoped GET checks.

Separate service, not the workspace API and not a general-purpose plugin loader.
"""
import asyncio
from contextlib import asynccontextmanager
import hmac
import os
from pathlib import Path
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from . import __version__
from .checks import CATALOG
from .http_limits import BodyLimitMiddleware
from .mcp_executor import ExecutionRejected, Runner
from .mcp_scope import FORMAT, MAX_TOKEN_CHARS, RequestLimits
from .remote_mcp import VERSIONS, _decode, _encode
from .tool_contracts import PACKAGE_SHA256

MAX_RPC_BYTES = 65536


def tools_for(runner):
    profile = {'format': FORMAT, 'server_id': runner.server_id, 'package_sha256': PACKAGE_SHA256,
               'ceiling': runner.ceiling.model_dump(), 'allow_private': runner.allow_private,
               'credential_envs': sorted(runner.credential_envs), 'method': 'GET', 'single_use': True}
    return [{'name': 'validate_' + item['id'], 'description': item['description'],
             'inputSchema': {'type': 'object', 'properties': {'grant': {'type': 'string', 'minLength': 1,
                              'maxLength': MAX_TOKEN_CHARS}}, 'required': ['grant'], 'additionalProperties': False},
             'outputSchema': {'type': 'object', 'properties': {
                 'format': {'const': FORMAT}, 'grant_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'},
                 'task_id': {'type': 'string'}, 'asset_id': {'type': 'string'}, 'asset_revision': {'type': 'integer'},
                 'check_id': {'const': item['id']}, 'scope_url': {'type': 'string'},
                 'allow_private': {'type': 'boolean'},
                 'package_sha256': {'const': PACKAGE_SHA256}, 'effective_limits': {'type': 'object'},
                 'result': {'type': 'array', 'minItems': 3, 'maxItems': 3}, 'traffic': {'type': 'array', 'maxItems': 240}},
                 'required': ['format', 'grant_sha256', 'task_id', 'asset_id', 'asset_revision', 'check_id',
                              'scope_url', 'package_sha256', 'allow_private', 'effective_limits', 'result', 'traffic'],
                 'additionalProperties': False},
             'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'idempotentHint': False,
                             'openWorldHint': True},
             '_meta': {'org.openaegis/scopedExecution': {**profile, 'check_id': item['id']}}} for item in CATALOG]


def create_execution_app(server_id, bearer, scope_key, data_dir, *, allow_private=False, credential_envs=(), ceiling=None, allowed_origins=()):
    if (not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', server_id) or not isinstance(bearer, str)
            or not 32 <= len(bearer) <= 4096 or any(not 33 <= ord(c) <= 126 for c in bearer)
            or any(not re.fullmatch(r'AEGIS_TEST_[A-Z0-9_]+', name) for name in credential_envs)
            or len(set(credential_envs)) > 20):
        raise ValueError('execution_server_configuration')
    if scope_key == bearer.encode() or any(not origin.startswith(('http://', 'https://')) for origin in allowed_origins):
        raise ValueError('execution_server_configuration')
    runner = Runner(server_id, scope_key, Path(data_dir) / 'consumed.db', allow_private=allow_private,
                    credential_envs=credential_envs, ceiling=ceiling, protected_values=(bearer,))

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            runner.stop.set()

    app = FastAPI(title='Open Aegis scoped MCP execution', docs_url=None, redoc_url=None,
                  openapi_url=None, lifespan=lifespan)
    app.state.runner = runner
    app.state.shutdown_requested = runner.stop
    app.add_middleware(BodyLimitMiddleware)

    @app.middleware('http')
    async def boundary(request, call_next):
        if runner.stop.is_set():
            return JSONResponse({'detail': 'execution_server_stopping'}, status_code=503)
        authorization = request.headers.get('authorization', '').encode('utf-8')
        if not hmac.compare_digest(authorization, ('Bearer ' + bearer).encode()):
            return JSONResponse({'detail': 'authentication_required'}, status_code=401)
        origin = request.headers.get('origin')
        if origin and origin not in allowed_origins:
            return JSONResponse({'detail': 'origin_rejected'}, status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    def rpc_error(identifier, code):
        return JSONResponse({'jsonrpc': '2.0', 'id': identifier, 'error': {'code': code, 'message': 'request_rejected'}})

    @app.post('/mcp')
    async def mcp(request: Request):
        identifier = None
        try:
            raw = await request.body()
            if len(raw) > MAX_RPC_BYTES or request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
                return JSONResponse({'detail': 'rpc_body'}, status_code=400)
            value = _decode(raw)
            if not isinstance(value, dict) or not set(value) <= {'jsonrpc', 'id', 'method', 'params'} or value.get('jsonrpc') != '2.0':
                return rpc_error(None, -32600)
            identifier = value.get('id')
            if 'id' in value and (type(identifier) not in (int, str) or type(identifier) is str and not 1 <= len(identifier) <= 80):
                return rpc_error(None, -32600)
            method, params = value.get('method'), value.get('params', {})
            if not isinstance(method, str) or not isinstance(params, dict):
                return rpc_error(identifier, -32600)
            if method != 'initialize' and request.headers.get('MCP-Protocol-Version') not in VERSIONS:
                return JSONResponse({'detail': 'protocol_version'}, status_code=400)
            if method == 'notifications/initialized' and 'id' not in value:
                return Response(status_code=202)
            if 'id' not in value:
                return JSONResponse({'detail': 'notification_rejected'}, status_code=400)
            if method == 'initialize':
                if not isinstance(params.get('protocolVersion'), str) or not isinstance(params.get('capabilities'), dict) or not isinstance(params.get('clientInfo'), dict):
                    return rpc_error(identifier, -32602)
                result = {'protocolVersion': params['protocolVersion'] if params['protocolVersion'] in VERSIONS else VERSIONS[0],
                          'capabilities': {'tools': {}}, 'serverInfo': {'name': 'OpenAegis-ScopedGET', 'version': __version__}}
            elif method == 'tools/list' and not params:
                result = {'tools': tools_for(runner)}
            elif method == 'tools/call' and set(params) == {'name', 'arguments'} and isinstance(params['name'], str):
                try:
                    output = await asyncio.to_thread(runner.execute, params['name'], params['arguments'])
                    result = {'content': [{'type': 'text', 'text': 'Approved scoped GET validation completed.'}],
                              'structuredContent': output, 'isError': False}
                except ExecutionRejected:
                    result = {'content': [{'type': 'text', 'text': 'Validation could not be confirmed. Grant replay is not allowed.'}],
                              'isError': True}
            else:
                return rpc_error(identifier, -32601)
            return Response(_encode({'jsonrpc': '2.0', 'id': identifier, 'result': result}), media_type='application/json')
        except Exception:
            return rpc_error(identifier, -32600)

    return app


def main():
    from .__main__ import AegisServer
    try:
        key = os.environ.get('AEGIS_MCP_SCOPE_KEY', '').encode()
        raw_limits = os.environ.get('AEGIS_MCP_EXEC_LIMITS', '{}').encode()
        if len(raw_limits) > 32768:
            raise ValueError()
        limits = _decode(raw_limits)
        if not isinstance(limits, dict):
            raise ValueError()
        app = create_execution_app(os.environ.get('AEGIS_MCP_SERVER_ID', ''),
                                   os.environ.get('AEGIS_MCP_BEARER_TOKEN', ''), key,
                                   os.environ.get('AEGIS_MCP_EXEC_DATA_DIR', 'data/mcp-execution'),
                                   ceiling=RequestLimits(**limits),
                                   allow_private=os.environ.get('AEGIS_MCP_EXEC_LAB') == '1',
                                   credential_envs=tuple(filter(None, os.environ.get('AEGIS_MCP_TEST_ENVS', '').split(','))),
                                   allowed_origins=tuple(filter(None, os.environ.get('AEGIS_MCP_ALLOWED_ORIGINS', '').split(','))))
        AegisServer(app, host=os.environ.get('AEGIS_MCP_EXEC_HOST', '127.0.0.1'),
                    port=int(os.environ.get('AEGIS_MCP_EXEC_PORT', '8791')), access_log=False,
                    timeout_graceful_shutdown=5).run()
    except (ValueError, RuntimeError):
        raise SystemExit('MCP 실행 서버 설정을 확인하세요.') from None


if __name__ == '__main__':
    main()
