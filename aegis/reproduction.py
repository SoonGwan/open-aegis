"""Portable approved API policy snapshots and explicitly invoked scoped GET replay."""
from dataclasses import replace
import time
from typing import Literal
from urllib.parse import urljoin, urlsplit
from pydantic import BaseModel, Field, field_validator, model_validator
from . import __version__
from .checks import run_check
from .network import Transport, normalize_url, in_scope
from .policy_models import AuthorizationRule
from .runtime import ExecutionPolicy, OriginLimiter, TaskControl

MAX_MANIFEST_BYTES = 8 * 1024 * 1024


class Limits(BaseModel):
    model_config = {'extra': 'forbid'}
    target_rps: float = Field(ge=.1, le=20, allow_inf_nan=False)
    request_timeout: float = Field(ge=.1, le=30, allow_inf_nan=False)
    dns_timeout: float = Field(ge=.1, le=30, allow_inf_nan=False)
    task_timeout: float = Field(ge=.2, le=3600, allow_inf_nan=False)
    request_budget: int = Field(ge=1, le=240, strict=True)
    request_retries: int = Field(ge=0, le=2, strict=True)
    retry_delay: float = Field(ge=.05, le=10, allow_inf_nan=False)


class PolicyAsset(BaseModel):
    model_config = {'extra': 'forbid'}
    id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    revision: int = Field(ge=1, strict=True)
    url: str = Field(max_length=2000)
    authorization_rules: list[AuthorizationRule] = Field(min_length=1, max_length=20)

    @field_validator('url')
    @classmethod
    def url_scope(cls, value):
        value = normalize_url(value)
        if urlsplit(value).query:
            raise ValueError('자산 주소에 쿼리를 넣을 수 없습니다.')
        return value

    @model_validator(mode='after')
    def rules_in_scope(self):
        if any(not in_scope(urljoin(self.url, rule.path), self.url) for rule in self.authorization_rules):
            raise ValueError('권한 규칙이 자산 범위를 벗어났습니다.')
        return self


class PolicyManifest(BaseModel):
    model_config = {'extra': 'forbid'}
    format: Literal['aegis-api-policy-v1']
    source_version: str = Field(min_length=1, max_length=80)
    task_id: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    approved_at: float = Field(gt=0, allow_inf_nan=False)
    limits: Limits
    assets: list[PolicyAsset] = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def unique_assets(self):
        if len({asset.id for asset in self.assets}) != len(self.assets) or len({asset.url for asset in self.assets}) != len(self.assets):
            raise ValueError('중복 자산이 있습니다.')
        return self


def build_manifest(task):
    if not task.get('approved_at') or 'api_authorization' not in task.get('checks', []):
        raise ValueError('승인된 API 권한 검증 작업만 내보낼 수 있습니다.')
    if not task.get('execution_policy'):
        raise ValueError('실행 제한이 없는 이전 작업은 새 계획으로 승인하세요.')
    assets = [{'id': asset['id'], 'revision': asset.get('revision', 1), 'url': asset['url'],
               'authorization_rules': asset['authorization_rules']}
              for asset in task['scope_snapshot'] if asset.get('authorization_rules')]
    if not assets:
        raise ValueError('내보낼 API 권한 규칙이 없습니다.')
    return PolicyManifest.model_validate({
        'format': 'aegis-api-policy-v1', 'source_version': __version__, 'task_id': task['id'],
        'approved_at': task['approved_at'], 'assets': assets,
        'limits': {key: task['execution_policy'][key] for key in Limits.model_fields}})


def replay(manifest, *, lab=False):
    # Local environment can tighten approved limits, never expand them.
    current = ExecutionPolicy.from_env()
    limits = manifest.limits.model_dump()
    policy = replace(current, **{key: (max if key == 'retry_delay' else min)(value, getattr(current, key))
                                 for key, value in limits.items()}, target_parallel=1)
    control = TaskControl(deadline=time.monotonic() + policy.task_timeout)
    limiter = OriginLimiter(policy)
    outcomes = []
    for item in manifest.assets:
        requests = 0

        def count_request(_):
            nonlocal requests
            requests += 1

        transport = Transport(item.url, allow_private=lab, record=count_request, policy=policy,
                              limiter=limiter, control=control)
        try:
            control.check()
            response = transport.get()
            if not 200 <= response['status'] < 300:
                raise ValueError('기본 응답을 확인할 수 없습니다.')
            findings, _, _ = run_check('api_authorization', item.model_dump(), transport, response)
            control.check()
            outcomes.append({'asset_id': item.id, 'status': 'mismatch' if findings else 'passed',
                             'findings': [{'code': issue['code'], 'severity': issue['severity']} for issue in findings],
                             'requests': requests})
        except Exception as exc:
            outcomes.append({'asset_id': item.id, 'status': 'inconclusive', 'error_type': type(exc).__name__,
                             'requests': requests})
    return {'format': 'aegis-api-policy-result-v1', 'task_id': manifest.task_id,
            'executed': True, 'passed': all(item['status'] == 'passed' for item in outcomes),
            'limits': {key: getattr(policy, key) for key in Limits.model_fields}, 'assets': outcomes}
