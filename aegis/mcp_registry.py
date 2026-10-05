"""Administrator-reviewed remote metadata registration, separate from execution."""
from contextlib import nullcontext
import hashlib
import json
import os
import threading

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .mcp_process import DiscoveryError, discover
from .remote_mcp import Client, Connection, RemoteMCPError, _decode, _digest, _encode
from .store_util import identifier, now

TTL = 900


class PreviewInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    connection_id: str = Field(min_length=1, max_length=64)


class RegisterInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    selected: list[str] = Field(min_length=1, max_length=100)
    reviewed: bool


class DisableInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    revision: int = Field(ge=1, le=10_000_000)


class Registry:
    def __init__(self, store, stop, connections):
        self.store, self.stop = store, stop
        self.connections = {}
        self.gate = threading.Lock()
        self.executor = None
        if not isinstance(connections, list) or len(connections) > 10:
            raise ValueError('connection_budget')
        for item in connections:
            connection = Connection(**item)
            Client(connection)  # Admission only; constructor does not make requests.
            if connection.id in self.connections:
                raise ValueError('duplicate_connection')
            self.connections[connection.id] = connection

    @classmethod
    def from_env(cls, store, stop):
        try:
            raw = os.environ.get('AEGIS_MCP_CONNECTIONS', '[]').encode('utf-8')
            if len(raw) > 32768:
                raise ValueError()
            return cls(store, stop, _decode(raw))
        except (ValueError, TypeError, UnicodeError):
            raise RuntimeError('AEGIS_MCP_CONNECTIONS 설정을 확인하세요. 최대 10개의 고정 HTTPS 연결을 사용하세요.') from None

    def public_connections(self):
        return [{'id': c.id, 'url': c.url, 'configured': not c.token_env or bool(os.environ.get(c.token_env)),
                 'lab_http': c.lab_http, 'execution_available': False} for c in self.connections.values()]

    def _connection(self, connection_id):
        connection = self.connections.get(connection_id)
        if connection is None:
            raise HTTPException(404, '설정된 MCP 연결이 없습니다.')
        return connection

    @staticmethod
    def _contract(connection):
        try:
            _, fingerprint = Client(connection)._credentials()
            return _digest({'connection': connection.model_dump(), 'credential': fingerprint})
        except RemoteMCPError:
            raise HTTPException(503, 'MCP 인증 환경변수를 확인하세요.') from None

    def _discover(self, connection):
        try:
            with self.store.execution_permit() if getattr(self.store, 'backend', None) == 'postgres' else nullcontext():
                return discover(connection, self.stop)
        except DiscoveryError:
            raise HTTPException(502, 'MCP 목록 조회의 연결·TLS·응답 계약·프로세스 제한을 확인하세요.') from None

    def _acquire(self):
        if not self.gate.acquire(blocking=False):
            raise HTTPException(429, '다른 MCP 검토가 진행 중입니다.', headers={'Retry-After': '2'})

    def _placeholder(self):
        return '%s' if getattr(self.store, 'backend', None) == 'postgres' else '?'

    def _expire(self, db, timestamp):
        expr = "(data::jsonb->>'expires_at')::numeric" if self._placeholder() == '%s' else "json_extract(data,'$.expires_at')"
        db.execute(f"DELETE FROM records WHERE kind='mcp_previews' AND {expr}<={self._placeholder()}", (timestamp,))

    @staticmethod
    def public_preview(record):
        return {key: record[key] for key in ('id', 'connection_id', 'actor_id', 'created_at', 'expires_at',
                                             'catalog', 'fingerprint', 'registered_at')} | {'execution_available': False}

    @staticmethod
    def _tool_id(connection_id, name):
        return hashlib.sha256(_encode([connection_id, name])).hexdigest()[:32]

    def preview(self, data, actor_id):
        connection = self._connection(data.connection_id)
        self._acquire()
        try:
            contract = self._contract(connection)
            catalog = self._discover(connection)
            if self._contract(connection) != contract:
                raise HTTPException(409, '조회 중 MCP 설정 또는 인증이 변경됐습니다. 다시 검토하세요.')
            timestamp = now()
            record = {'id': identifier(), 'connection_id': connection.id, 'actor_id': actor_id,
                      'created_at': timestamp, 'expires_at': timestamp + TTL, 'catalog': catalog,
                      'fingerprint': _digest(catalog), 'connection_contract': contract, 'registered_at': None}
            with self.store.write_transaction() as db:
                self._expire(db, timestamp)
                count = db.execute("SELECT count(*) AS count FROM records WHERE kind='mcp_previews'").fetchone()['count']
                if count >= 20:
                    raise HTTPException(429, '열린 MCP 검토가 20개입니다. 만료 후 다시 시도하세요.')
                record['registry_basis'] = {}
                for tool in catalog['tools']:
                    tool_id = self._tool_id(connection.id, tool['name'])
                    previous = self.store.get('mcp_tools', tool_id, connection=db)
                    record['registry_basis'][tool_id] = previous['revision'] if previous else None
                self.store.put_many([('mcp_previews', record)], connection=db)
                self.store.event(None, 'MCP 도구 목록 검토 생성', detail={'actor_id': actor_id,
                                 'connection_id': connection.id, 'preview_id': record['id'],
                                 'catalog_sha256': record['fingerprint'], 'tool_count': len(catalog['tools'])}, connection=db)
            return self.public_preview(record)
        finally:
            self.gate.release()

    def _review(self, preview_id, actor_id, selected, *, connection=None):
        record = self.store.get('mcp_previews', preview_id, connection=connection)
        if record is None:
            raise HTTPException(404, 'MCP 검토 기록이 없습니다.')
        if record['actor_id'] != actor_id:
            raise HTTPException(403, '이 검토를 만든 관리자만 등록할 수 있습니다.')
        if record['registered_at'] is not None:
            if record['selected'] != selected:
                raise HTTPException(409, '이미 반영한 검토의 선택은 바꿀 수 없습니다.')
            return record, True
        if record['expires_at'] <= now():
            raise HTTPException(410, 'MCP 검토가 만료됐습니다.')
        if not set(selected) <= {tool['name'] for tool in record['catalog']['tools']}:
            raise HTTPException(422, '검토 목록의 도구만 선택하세요.')
        return record, False

    def register(self, preview_id, data, actor_id):
        if data.reviewed is not True or len(set(data.selected)) != len(data.selected):
            raise HTTPException(422, '중복 없는 선택과 도구 정의 검토 확인이 필요합니다.')
        selected = sorted(data.selected)
        self._acquire()
        try:
            record, replay = self._review(preview_id, actor_id, selected)
            if replay:
                return record['result']
            connection = self._connection(record['connection_id'])
            if self._contract(connection) != record['connection_contract']:
                raise HTTPException(409, 'MCP 연결 또는 인증이 바뀌었습니다. 다시 검토하세요.')
            fresh = self._discover(connection)
            if _digest(fresh) != record['fingerprint']:
                raise HTTPException(409, 'MCP 도구 목록이 바뀌었습니다. 다시 검토하세요.')
            with self.store.write_transaction() as db:
                current, replay = self._review(preview_id, actor_id, selected, connection=db)
                if replay:
                    return current['result']
                if current != record or self._contract(connection) != record['connection_contract']:
                    raise HTTPException(409, '검토 또는 인증 상태가 바뀌었습니다. 다시 검토하세요.')
                timestamp, records, items = now(), [], []
                p = self._placeholder()
                expr = "data::jsonb->>'connection_id'" if p == '%s' else "json_extract(data,'$.connection_id')"
                count = db.execute(f"SELECT count(*) AS count FROM records WHERE kind='mcp_tools' AND {expr}={p}",
                                   (connection.id,)).fetchone()['count']
                for tool in record['catalog']['tools']:
                    if tool['name'] not in selected:
                        continue
                    tool_id = self._tool_id(connection.id, tool['name'])
                    previous = self.store.get('mcp_tools', tool_id, connection=db)
                    if (previous['revision'] if previous else None) != record['registry_basis'][tool_id]:
                        raise HTTPException(409, '검토 이후 도구 등록 또는 비활성화 상태가 바뀌었습니다. 다시 검토하세요.')
                    if previous is None:
                        count += 1
                        if count > 100:
                            raise HTTPException(409, '연결별 등록 도구 한도는 100개입니다.')
                    revision = previous['revision'] + 1 if previous else 1
                    if revision > 10_000_000:
                        raise HTTPException(409, '도구 revision 한도입니다.')
                    row = {'id': tool_id, 'connection_id': connection.id, 'name': tool['name'],
                           'definition': tool, 'definition_sha256': _digest(tool),
                           'connection_contract': record['connection_contract'],
                           'protocol_version': fresh['protocolVersion'], 'server_info': fresh['serverInfo'],
                           'revision': revision, 'registered_by': actor_id, 'registered_at': timestamp,
                           'preview_id': preview_id, 'catalog_sha256': record['fingerprint'], 'enabled': True,
                           'execution_available': bool(self.executor and self.executor.available(connection.id, tool))}
                    records.append(('mcp_tools', row))
                    items.append(self.summary(row))
                result = {'preview_id': preview_id, 'items': items, 'execution_available': False}
                records.append(('mcp_previews', {**record, 'registered_at': timestamp,
                                                'selected': selected, 'result': result}))
                self.store.put_many(records, connection=db)
                self.store.event(None, '검토된 MCP 도구 등록', detail={'actor_id': actor_id,
                                 'connection_id': connection.id, 'preview_id': preview_id,
                                 'catalog_sha256': record['fingerprint'], 'tools': items}, connection=db)
            return result
        finally:
            self.gate.release()

    @staticmethod
    def summary(row):
        return {key: row[key] for key in ('id', 'connection_id', 'name', 'revision', 'enabled',
                                          'definition_sha256', 'registered_by', 'registered_at',
                                          'execution_available')}

    def tools(self, limit=25, offset=0):
        # SQL projects summaries; schemas are only fetched through individual detail.
        p = self._placeholder()
        columns = ('id', 'connection_id', 'name', 'revision', 'enabled', 'definition_sha256',
                   'registered_by', 'registered_at', 'execution_available')
        expr = ','.join("'" + key + "'," + (f"data::jsonb->'{key}'" if p == '%s' else f"json_extract(data,'$.{key}')")
                        for key in columns)
        projection = ('jsonb_build_object' if p == '%s' else 'json_object') + '(' + expr + ') AS data'
        timestamp = "(data::jsonb->>'registered_at')::double precision" if p == '%s' else "json_extract(data,'$.registered_at')"
        with self.store.read_transaction() as db:
            total = db.execute("SELECT count(*) AS count FROM records WHERE kind='mcp_tools'").fetchone()['count']
            rows = db.execute(f"SELECT {projection},{timestamp} AS exact_timestamp FROM records WHERE kind='mcp_tools' ORDER BY rowid DESC LIMIT {p} OFFSET {p}",
                              (limit, offset)).fetchall()
        items = [row['data'] if isinstance(row['data'], dict) else json.loads(row['data']) for row in rows]
        for item, row in zip(items, rows):
            item['registered_at'] = row['exact_timestamp']
            item['enabled'], item['execution_available'] = bool(item['enabled']), bool(item['execution_available'])
        return {'items': items, 'total': total, 'limit': limit, 'offset': offset, 'has_more': offset + len(items) < total}

    def detail(self, tool_id):
        row = self.store.get('mcp_tools', tool_id)
        if row is None:
            raise HTTPException(404, '등록된 MCP 도구가 없습니다.')
        return self.summary(row) | {'definition': row['definition'], 'server_info': row['server_info'],
                                    'protocol_version': row['protocol_version']}

    def disable(self, tool_id, data, actor_id):
        with self.store.write_transaction() as db:
            row = self.store.get('mcp_tools', tool_id, connection=db)
            if row is None:
                raise HTTPException(404, '등록된 MCP 도구가 없습니다.')
            if row['revision'] != data.revision:
                raise HTTPException(409, '도구 revision이 변경됐습니다.')
            if not row['enabled']:
                return self.summary(row)
            if row['revision'] >= 10_000_000:
                raise HTTPException(409, '도구 revision 한도입니다.')
            changed = {**row, 'enabled': False, 'revision': row['revision'] + 1}
            self.store.put_many([('mcp_tools', changed)], connection=db)
            self.store.event(None, 'MCP 도구 등록 비활성화', detail={'actor_id': actor_id,
                             'tool_id': tool_id, 'revision': changed['revision']}, connection=db)
            return self.summary(changed)
