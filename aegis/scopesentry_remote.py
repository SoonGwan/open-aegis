"""Bounded, configured ScopeSentry read client; never calls target or write APIs."""
import hashlib
import http.client
import json
import os
import re
import threading
import time
from contextlib import nullcontext
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .network import normalize_url, resolve, PinnedHTTP, PinnedHTTPS
from .runtime import TaskControl, RequestGuard
from . import scopesentry as imports

PAGE_SIZE = 50
MAX_PAGES = 20


class Connection(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_.-]+$')
    url: str = Field(max_length=2000)
    token_env: str = Field(min_length=1, max_length=100, pattern=r'^[A-Za-z_][A-Za-z0-9_]*$')
    project: str = Field(default='', max_length=200)
    allow_private: bool = False
    lab_http: bool = False


class PageInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    connection_id: str = Field(min_length=1, max_length=64)
    previous_preview_id: str | None = Field(default=None, max_length=80)


class Sources:
    def __init__(self, store, shutdown, connections):
        self.store, self.shutdown = store, shutdown
        self.connections = {}
        self.gate = threading.Lock()
        self.timeout = 12
        if not isinstance(connections, list) or len(connections) > 10:
            raise ValueError('source admission')
        for item in connections:
            c = Connection(**item)
            c.project.encode('utf-8')
            if c.id in self.connections:
                raise ValueError('duplicate source')
            c.url = normalize_url(c.url)
            p = urlsplit(c.url)
            if p.query or any(ord(ch) < 32 or ord(ch) == 127 for ch in c.url):
                raise ValueError('source URL')
            if p.scheme != 'https' and not (c.lab_http and c.allow_private and p.hostname in ('127.0.0.1', '::1')):
                raise ValueError('TLS required')
            self.connections[c.id] = c
        if len(self.connections) > 10:
            raise ValueError('source admission')

    @classmethod
    def from_env(cls, store, shutdown):
        try:
            raw = os.environ.get('AEGIS_SCOPESENTRY_SOURCES', '[]')
            if len(raw.encode('utf-8')) > 32768:
                raise ValueError('source configuration size')
            value = json.loads(raw, object_pairs_hook=imports.unique_object, parse_constant=imports.invalid_constant)
            if not isinstance(value, list):
                raise ValueError('source list')
            return cls(store, shutdown, value)
        except (ValueError, TypeError, UnicodeError):
            raise RuntimeError('AEGIS_SCOPESENTRY_SOURCES 설정을 확인하세요. 연결은 최대 10개이며 HTTPS가 필요합니다.') from None

    def public(self):
        return [{'id': c.id, 'url': c.url, 'project': c.project,
                 'configured': bool(os.environ.get(c.token_env)), 'lab_http': c.lab_http}
                for c in self.connections.values()]

    def credentials(self, c):
        token = os.environ.get(c.token_env, '')
        if not token or len(token) > 4096 or any(not 33 <= ord(ch) <= 126 for ch in token):
            raise HTTPException(503, '원본 JWT 환경변수가 없거나 형식이 올바르지 않습니다. 관리자에게 확인하세요.')
        # No raw credential is stored. This opaque contract changes on credential rotation.
        fingerprint = imports.digest({**c.model_dump(), 'credential_sha256': hashlib.sha256(token.encode()).hexdigest()})
        return token, fingerprint

    def fetch(self, c, token, page, control):
        with self.store.execution_permit() if getattr(self.store,'backend',None)=='postgres' else nullcontext():
            return self._fetch(c,token,page,control)

    def _fetch(self, c, token, page, control):
        p = urlsplit(c.url)
        port = p.port or (443 if p.scheme == 'https' else 80)
        address = resolve(p.hostname, port, c.allow_private, control=control, timeout=control.timeout(4))[0]
        cls = PinnedHTTPS if p.scheme == 'https' else PinnedHTTP
        connection = cls(p.hostname, port, address, timeout=control.timeout(self.timeout))
        path = p.path.rstrip('/') + '/api/assets/asset'
        query = {'pageIndex': page, 'pageSize': PAGE_SIZE, 'index': 'asset',
                 'filter': {'type': ['http'], **({'project': [c.project]} if c.project else {})}}
        try:
            with RequestGuard(connection, control, self.timeout) as guard:
                connection.request('POST', path, body=json.dumps(query).encode(), headers={
                    'Content-Type': 'application/json', 'Accept': 'application/json', 'Accept-Encoding': 'identity',
                    'Authorization': 'Bearer ' + token, 'User-Agent': 'OpenAegis-ScopeSentry/0.1'})
                guard.sock = connection.sock
                response = connection.getresponse()
                if response.status in (401, 403):
                    raise HTTPException(502, '원본 ScopeSentry 인증 또는 조회 권한이 거절됐습니다. 현재 페이지를 다시 확인하세요.')
                if response.status != 200:
                    raise HTTPException(502, '원본 ScopeSentry 조회가 실패했습니다. 리다이렉트는 따르지 않습니다.')
                if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
                    raise HTTPException(502, '원본 응답의 압축 형식은 지원하지 않습니다.')
                if response.getheader('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                    raise HTTPException(502, '원본 응답이 JSON이 아닙니다.')
                body = response.read(imports.MAX_BYTES + 1)
                if len(body) > imports.MAX_BYTES:
                    raise HTTPException(502, '원본 페이지 응답이 1 MiB를 초과했습니다.')
            control.check()
            try:
                result = json.loads(body.decode('utf-8'), object_pairs_hook=imports.unique_object, parse_constant=imports.invalid_constant)
                if type(result.get('code')) is not int or result['code'] != 200:
                    raise ValueError('source code')
                rows = result['data']['list']
                if not isinstance(rows, list) or len(rows) > PAGE_SIZE or any(not isinstance(row, dict) for row in rows):
                    raise ValueError('source rows')
                # API model uses id; export model uses _id. Discard all other fields here.
                text = '\n'.join(json.dumps({'_id': row.get('id'), 'type': row.get('type'), 'url': row.get('url')}) for row in rows)
                parsed = imports.parse_export(text) if rows else []
                if any(row['external_id'] is None for row in parsed):
                    raise ValueError('source identity')
                return parsed, hashlib.sha256(body).hexdigest()
            except (ValueError, TypeError, KeyError, AttributeError, RecursionError, HTTPException):
                raise HTTPException(502, '원본 페이지의 응답 계약이 올바르지 않습니다. 내용을 저장하지 않았습니다.') from None
        finally:
            connection.close()

    def collect(self, data, actor_id):
        c = self.connections.get(data.connection_id)
        if c is None:
            raise HTTPException(404, '설정된 원본 연결이 없습니다.')
        if not self.gate.acquire(blocking=False):
            raise HTTPException(429, '다른 원본 조회가 진행 중입니다. 잠시 후 같은 페이지를 다시 요청하세요.', headers={'Retry-After': '5'})
        try:
            token, contract = self.credentials(c)
            previous = None
            seen = set()
            with self.store.lock:
                if data.previous_preview_id:
                    previous = self.store.get('import_previews', data.previous_preview_id)
                    if not previous or previous['actor_id'] != actor_id:
                        raise HTTPException(404, '이 사용자의 이전 원본 미리보기가 없습니다.')
                    remote = previous.get('remote')
                    if previous['expires_at'] <= imports.now():
                        raise HTTPException(410, '이전 페이지 검토가 만료됐습니다. 처음부터 다시 조회하세요.')
                    if not remote or remote['connection_id'] != c.id or remote['contract'] != contract:
                        raise HTTPException(409, '원본 연결 설정 또는 인증이 바뀌었습니다. 처음부터 다시 조회하세요.')
                    if not remote['has_more'] or remote['page'] >= MAX_PAGES:
                        raise HTTPException(409, '이 수집의 마지막 페이지 또는 20페이지 한도입니다. 별도 원본 필터로 다시 조회하세요.')
                    if remote.get('next_preview_id'):
                        cached = self.store.get('import_previews', remote['next_preview_id'])
                        if cached and cached['expires_at'] > imports.now():
                            return imports.public_preview(cached)
                    cursor = previous
                    for _ in range(MAX_PAGES):
                        seen.update(row['external_id'] for row in cursor['rows'] if row['external_id'])
                        parent = cursor['remote'].get('previous_preview_id')
                        if not parent:
                            break
                        cursor = self.store.get('import_previews', parent)
                        if not cursor or cursor['actor_id'] != actor_id:
                            raise HTTPException(409, '이전 페이지 연결을 찾을 수 없습니다. 처음부터 다시 조회하세요.')
            control = TaskControl(stop=self.shutdown, deadline=time.monotonic() + self.timeout)
            try:
                if previous:
                    old_rows, _ = self.fetch(c, token, previous['remote']['page'], control)
                    if imports.digest(old_rows) != previous['remote']['page_digest']:
                        raise HTTPException(409, '원본의 이전 페이지가 변경됐습니다. 순서가 바뀌어 누락될 수 있으므로 처음부터 다시 조회하세요.')
                page = previous['remote']['page'] + 1 if previous else 1
                rows, raw_hash = self.fetch(c, token, page, control)
                if any(row['external_id'] in seen for row in rows):
                    raise HTTPException(409, '이미 수집한 원본 ID가 다시 나타났습니다. 원본 순서를 확인하고 처음부터 다시 조회하세요.')
                control.check()
                remote = {'connection_id': c.id, 'contract': contract, 'page': page,
                          'page_digest': imports.digest(rows), 'previous_preview_id': data.previous_preview_id,
                          'has_more': len(rows) == PAGE_SIZE, 'next_preview_id': None}
                result = imports.store_preview(self.store, c.id, rows, raw_hash, actor_id, remote=remote)
                return result
            except HTTPException:
                raise
            except (ValueError, OSError, TimeoutError, InterruptedError, http.client.HTTPException):
                raise HTTPException(502, '원본 조회 연결·DNS·TLS·시간 제한을 확인하세요. 페이지를 저장하지 않았습니다.') from None
        finally:
            self.gate.release()
