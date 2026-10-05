"""Configured, administrator-reviewed scoped GET adapters for approved Workers."""
from contextlib import nullcontext
import hashlib
import os
import threading
import time
from types import SimpleNamespace

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .coverage import slot
from .mcp_execution_server import tools_for
from .mcp_process import cancel, discover, invoke
from .mcp_result_store import AUTHORITY_FIELDS, admit
from .mcp_scope import OBSERVATION_CHECK, RequestLimits, issue_grant
from .remote_mcp import _decode, _digest, _encode
from .store_util import now


class ExecutionConfigError(ValueError):
    pass


class ExecutorConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    connection_id: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_.-]+$')
    scope_key_env: str = Field(max_length=120, pattern=r'^AEGIS_MCP_SCOPE_[A-Z0-9_]+$')
    allow_private: bool = False


class Executors:
    def __init__(self, registry, configurations):
        self.registry, self.store = registry, registry.store
        self.configurations, self.gates = {}, {}
        if not isinstance(configurations, list) or len(configurations) > 10:
            raise ValueError('executor_configuration')
        for value in configurations:
            config = ExecutorConfig(**value)
            if config.connection_id in self.configurations or config.connection_id not in registry.connections:
                raise ValueError('executor_connection')
            self.configurations[config.connection_id] = config
            self.gates[config.connection_id] = threading.Lock()
            self._key(config)

    @classmethod
    def from_env(cls, registry):
        try:
            raw = os.environ.get('AEGIS_MCP_EXECUTORS', '[]').encode()
            if len(raw) > 32768:
                raise ValueError()
            return cls(registry, _decode(raw))
        except (ValueError, TypeError, UnicodeError):
            raise RuntimeError('AEGIS_MCP_EXECUTORS의 고정 연결과 별도 서명 키 설정을 확인하세요.') from None

    def _key(self, config):
        connection = self.registry.connections[config.connection_id]
        key = os.environ.get(config.scope_key_env, '').encode()
        bearer = os.environ.get(connection.token_env, '') if connection.token_env else ''
        if (not 32 <= len(key) <= 4096 or config.scope_key_env == connection.token_env
                or bearer and (key.decode() in bearer or bearer in key.decode())):
            raise ExecutionConfigError('원격 실행의 별도 서명 키를 확인하세요.')
        return key

    def profile(self, connection_id, definition):
        config = self.configurations.get(connection_id)
        if not config:
            raise ExecutionConfigError('운영자가 실행 연결을 구성해야 합니다.')
        profile = definition.get('_meta', {}).get('org.openaegis/scopedExecution', {})
        if (profile.get('server_id') != connection_id or type(profile.get('allow_private')) is not bool
                or type(profile.get('credential_envs')) is not list):
            raise ExecutionConfigError('검토된 GET 실행 계약이 아닙니다.')
        ceiling = RequestLimits(**profile.get('ceiling', {}))
        # Validate environment-name admission without instantiating a server or ledger.
        import re
        if (len(profile['credential_envs']) > 20
                or any(not isinstance(name, str) or not re.fullmatch(r'AEGIS_TEST_[A-Z0-9_]+', name)
                       for name in profile['credential_envs'])):
            raise ExecutionConfigError('테스트 계정 계약을 확인하세요.')
        expected = tools_for(SimpleNamespace(server_id=connection_id, ceiling=ceiling,
            allow_private=profile['allow_private'], credential_envs=profile['credential_envs']))
        if not any(_digest(tool) == _digest(definition) for tool in expected):
            raise ExecutionConfigError('현재 코드의 검토된 GET 어댑터만 실행할 수 있습니다.')
        return profile

    def available(self, connection_id, definition):
        try:
            self.profile(connection_id, definition)
            self._key(self.configurations[connection_id])
            return True
        except (ValueError, TypeError, KeyError, AttributeError):
            return False

    def snapshot(self, connection_id, checks, *, connection=None, observation=False):
        try:
            config = self.configurations[connection_id]
            endpoint = self.registry._connection(connection_id)
            key = self._key(config)
            rows, profiles, catalogs = [], [], set()
            for check in ([OBSERVATION_CHECK] if observation else checks):
                row = self.store.get('mcp_tools', self.registry._tool_id(connection_id, 'validate_' + check), connection=connection)
                if not row or not row['enabled'] or not row['execution_available']:
                    raise ValueError()
                profile = self.profile(connection_id, row['definition'])
                if row['connection_contract'] != self.registry._contract(endpoint):
                    raise ValueError()
                catalogs.add(row['catalog_sha256'])
                rows.append({name: row[name] for name in ('id', 'name', 'revision', 'definition_sha256')})
                profiles.append({name: profile[name] for name in ('ceiling', 'allow_private', 'credential_envs')})
            if len(catalogs) != 1 or not profiles or any(profile != profiles[0] for profile in profiles):
                raise ValueError()
            return {'format': 'aegis-approved-mcp-get-v1', 'connection_id': connection_id,
                    'url': endpoint.url,
                    'connection_contract': self.registry._contract(endpoint), 'key_sha256': hashlib.sha256(key).hexdigest(),
                    'catalog_sha256': catalogs.pop(), 'tools': rows, 'profile': profiles[0],
                    'allow_private': config.allow_private,
                    'mode': 'observation-response' if observation else 'base-response'}
        except (ValueError, TypeError, KeyError, AttributeError, HTTPException):
            raise ExecutionConfigError('관찰 응답 배치 도구의 설정과 관리자 검토·등록을 확인하고 새 계획을 검토하세요.'
                if observation else '원격 실행 설정 또는 관리자 도구 검토가 변경됐습니다. 새 계획을 검토하세요.') from None

    def public(self):
        from .checks import CHECK_IDS
        result = []
        for connection_id in self.configurations:
            checks = []
            for check in sorted(CHECK_IDS):
                try:
                    self.snapshot(connection_id, [check])
                    checks.append(check)
                except ExecutionConfigError:
                    pass
            if checks:
                result.append({'id': connection_id, 'url': self.registry.connections[connection_id].url, 'check_ids': checks})
        return result

    def require(self, task, *, refresh=False, control=None, connection=None):
        stored = task.get('remote_execution')
        if not stored:
            if task.get('remote_connection_id'):
                raise ExecutionConfigError('원격 작업의 실행 계약이 없습니다.')
            return
        from . import observation_execution
        observation_execution.require(task, approved=bool(task.get('approved_at')))
        current = self.snapshot(task['remote_connection_id'], task['checks'], connection=connection,
                                observation=bool(task.get('observation_execution')))
        if _digest(stored) != _digest(current):
            raise ExecutionConfigError('승인된 원격 실행 계약이 변경됐습니다. 새 계획을 검토하세요.')
        if 'api_authorization' in task['checks']:
            from .goal_planner import execution_checks
            allowed = set(current['profile']['credential_envs'])
            if any(rule.get('credential_env') and rule['credential_env'] not in allowed
                   for asset in task['scope_snapshot'] if 'api_authorization' in execution_checks(task, asset['id'])
                   for rule in asset.get('authorization_rules', [])):
                raise ExecutionConfigError('선택한 서버가 허용한 테스트 계정 이름으로 규칙을 구성하세요.')
        if refresh:
            endpoint = self.registry.connections[current['connection_id']]
            with self.store.execution_permit() if getattr(self.store, 'backend', None) == 'postgres' else nullcontext():
                catalog = discover(endpoint, control.stop if control else self.registry.stop)
            if _digest(catalog) != current['catalog_sha256']:
                raise ExecutionConfigError('원격 서버 목록이 변경됐습니다. 관리자 검토부터 다시 진행하세요.')

    def run_asset(self, task, asset, checks, control):
        contract = task['remote_execution']
        server_id = contract['connection_id']
        endpoint = self.registry.connections[server_id]
        config = self.configurations[server_id]
        gate = self.gates[server_id]
        outcome = {'asset_id': asset['id'], 'completed_checks': [], 'fingerprints': [], 'errors': []}
        budget = task['execution_policy']['request_budget']
        jobs = [OBSERVATION_CHECK] if task.get('observation_execution') else checks
        for check in jobs:
            attempt_id = _digest([task['id'], asset['id'], check, server_id])
            acquired = False
            dispatched, token = False, None
            try:
                while not acquired:
                    control.check()
                    acquired = gate.acquire(blocking=False)
                    if not acquired:
                        control.wait(.02)
                self.require(task, control=control)
                if budget < 1:
                    raise ExecutionConfigError('승인된 자산 요청 예산이 소진됐습니다.')
                key = self._key(config)
                remaining = min(300, int(control.deadline - time.monotonic())) if control.deadline else 60
                if remaining < 1:
                    raise TimeoutError()
                token = issue_grant(task, asset['id'], check, server_id, key, ttl=remaining,
                    allow_private=config.allow_private, request_budget=budget)
                grant_sha = hashlib.sha256(token.encode()).hexdigest()
                with self.store.lock, self.store.write_transaction() as db:
                    control.check()
                    self.require(task, connection=db)
                    current = self.store.get('tasks', task['id'], connection=db)
                    if (not current or current.get('status') != 'running'
                            or _digest({name: current.get(name) for name in AUTHORITY_FIELDS})
                            != _digest({name: task.get(name) for name in AUTHORITY_FIELDS})):
                        raise ExecutionConfigError('작업 실행 승인이 변경됐습니다.')
                    live_asset = self.store.get('assets', asset['id'], connection=db)
                    if (not live_asset or live_asset.get('archived_at')
                            or live_asset.get('authorized') is not True
                            or live_asset.get('url') != asset['url']
                            or type(live_asset.get('revision', 1)) is not int
                            or live_asset.get('revision', 1) != asset.get('revision', 1)):
                        raise ExecutionConfigError('자산 실행 범위가 변경됐습니다.')
                    if self.store.get('mcp_execution_attempts', attempt_id, connection=db):
                        raise ExecutionConfigError('이미 전송한 검사는 자동 재호출하지 않습니다.')
                    attempt = {'id': attempt_id, 'task_id': task['id'], 'asset_id': asset['id'], 'check': check,
                        'server_id': server_id, 'state': 'dispatching', 'created_at': now(),
                        'grant_sha256': grant_sha, 'contract_sha256': _digest(contract), 'request_budget': budget}
                    self.store.put_many([('mcp_execution_attempts', attempt)] +
                        [('coverage', {**slot(task, asset, actual), 'status': 'running', 'started_at': now()})
                         for actual in (checks if check == OBSERVATION_CHECK else [check])], connection=db)
                    self.store.event(task['id'], '승인된 원격 검증 전송을 기록했습니다.', detail={
                        'asset_id': asset['id'], 'worker_id': task['id'] + ':' + asset['id'], 'check': check,
                        'server_id': server_id, 'attempt_id': attempt_id, 'grant_sha256': grant_sha}, connection=db)
                definition = next(tool for tool in contract['tools'] if tool['name'] == 'validate_' + check)
                dispatched = True
                response = invoke(endpoint, definition['name'], {'grant': token}, contract['catalog_sha256'],
                                  definition['definition_sha256'], control)
                receipt = admit(self.store, task, asset['id'], check, token, key, server_id, response,
                    ceiling=RequestLimits(**contract['profile']['ceiling']),
                    allow_private=contract['profile']['allow_private'],
                    protected_values=(os.environ.get(endpoint.token_env, '') if endpoint.token_env else '',),
                    attempt_id=attempt_id, control=control)
                budget -= len(receipt['traffic_ids'])
                if check == OBSERVATION_CHECK:
                    outcome['completed_checks'].extend(actual for actual, status in receipt['coverage_statuses'].items() if status == 'completed')
                    outcome['errors'].extend(actual for actual, status in receipt['coverage_statuses'].items() if status != 'completed')
                elif receipt['coverage_status'] == 'completed':
                    outcome['completed_checks'].append(check)
                outcome['fingerprints'].extend(receipt['fingerprints'])
            except Exception as exc:
                outcome['errors'].extend(checks if check == OBSERVATION_CHECK else [check])
                cancellation = None
                if dispatched:
                    cancellation = {'state': 'unconfirmed', 'requested_at': now()}
                    try:
                        cancel(endpoint, token)
                        cancellation.update(state='acknowledged', acknowledged_at=now())
                    except Exception:
                        pass
                with self.store.lock, self.store.write_transaction() as db:
                    attempt = self.store.get('mcp_execution_attempts', attempt_id, connection=db)
                    if attempt and attempt['state'] == 'dispatching':
                        self.store.put_many([('mcp_execution_attempts', {**attempt, 'state': 'unconfirmed',
                            'finished_at': now(), **({'cancellation': cancellation} if cancellation else {})})], connection=db)
                    for remaining_check in (checks if check == OBSERVATION_CHECK else checks[checks.index(check):]):
                        self.store.put_many([('coverage', {**slot(task, asset, remaining_check),
                            'status': 'cancelled' if control.stop.is_set() else 'failed',
                            'reason': '원격 실행 결과를 확인하지 못했습니다. 자동 재호출하지 않습니다.',
                            'error_type': type(exc).__name__, 'finished_at': now()})], connection=db)
                    self.store.event(task['id'], '원격 실행 결과를 확인하지 못해 Worker를 종료합니다.', 'warning',
                        {'asset_id': asset['id'], 'worker_id': task['id'] + ':' + asset['id'],
                         'check': check, 'server_id': server_id, 'error_type': type(exc).__name__}, connection=db)
                    if cancellation:
                        self.store.event(task['id'], '원격 서버의 취소 기록을 확인했습니다.'
                            if cancellation['state'] == 'acknowledged' else '원격 서버의 취소 확인을 받지 못했습니다.',
                            'info' if cancellation['state'] == 'acknowledged' else 'warning',
                            {'asset_id': asset['id'], 'worker_id': task['id'] + ':' + asset['id'],
                             'check': check, 'server_id': server_id, 'attempt_id': attempt_id,
                             'cancellation': cancellation}, connection=db)
                break
            finally:
                if acquired:
                    gate.release()
        return outcome


def recover_attempts(store, task):
    """Bounded point reads; a restart never resumes potentially dispatched RPCs."""
    server_id = task['remote_execution']['connection_id']
    records = []
    with store.lock, store.write_transaction() as db:
        for asset in task['scope_snapshot']:
            for check in ([OBSERVATION_CHECK] if task.get('observation_execution') else task['checks']):
                attempt_id = _digest([task['id'], asset['id'], check, server_id])
                attempt = store.get('mcp_execution_attempts', attempt_id, connection=db)
                if attempt and attempt.get('state') == 'dispatching':
                    records.append(('mcp_execution_attempts', {**attempt, 'state': 'unconfirmed',
                        'finished_at': now(), 'termination_reason': 'source_restart'}))
        if records:
            store.put_many(records, connection=db)
            store.event(task['id'], '재시작 전 원격 전송 결과를 확인할 수 없어 자동 재호출하지 않습니다.',
                'warning', {'attempts': len(records), 'server_id': server_id}, connection=db)
