"""Explicit observation response targets, frozen separately from relevance hints."""
import hashlib
import json
from pydantic import BaseModel, Field, ConfigDict, field_validator

from . import observation_context
from .planning_history import PlanningConflict

CHECKS = ('security_headers', 'transport_security', 'cookie_policy', 'cors_policy')
FORMAT = 'aegis-observation-execution-v1'


class Selection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')
    observation_ids: list[str] = Field(min_length=1, max_length=10)
    checks: list[str] = Field(min_length=1, max_length=4)
    request_id: str = Field(pattern=r'^[a-f0-9]{32}$')

    @field_validator('observation_ids', 'checks')
    @classmethod
    def unique(cls, value):
        if len(set(value)) != len(value):raise ValueError('중복 선택을 제거하세요.')
        return value

    @field_validator('checks')
    @classmethod
    def response_checks(cls, value):
        if not set(value) <= set(CHECKS):raise ValueError('관찰 응답의 설정 검증 도구만 선택하세요.')
        return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def preview(store, source_id, *, connection=None):
    source = store.get('tasks', source_id, connection=connection)
    if not source:raise LookupError('출처 작업이 없습니다.')
    if (source.get('id') != source_id or not source.get('approved_at')
            or source.get('status') not in ('completed', 'failed', 'stopped', 'interrupted')):
        raise PlanningConflict('승인된 실행이 종료된 작업에서 관찰을 선택하세요.')
    context = observation_context.snapshot(store, source_id, connection=connection)
    return {'context': context, 'checks': list(CHECKS), 'max_targets': 10,
            'execution_authorized': False}


def prepare(store, source_id, selection, *, connection=None):
    context = preview(store, source_id, connection=connection)['context']
    return prepare_context(context, selection)


def prepare_context(context, selection):
    observation_context.require(context)
    if context['fingerprint'] != selection.fingerprint:
        raise PlanningConflict('관찰 근거가 변경되었습니다. 선택 목록을 다시 확인하세요.')
    by_id = {row['id']: row for row in context['items']}
    if any(id not in by_id for id in selection.observation_ids):
        raise PlanningConflict('완료 근거와 현재 범위가 확인된 관찰만 선택할 수 있습니다.')
    targets = [by_id[id] for id in selection.observation_ids]
    if len({(row['asset_id'], row['url']) for row in targets}) != len(targets):
        raise PlanningConflict('같은 자산의 같은 URL을 중복 선택할 수 없습니다.')
    execution = {'format': FORMAT, 'source_task_id': context['source_task_id'],
                 'context_fingerprint': context['fingerprint'],
                 'observation_ids': selection.observation_ids, 'targets': targets}
    execution['fingerprint'] = digest(execution)
    return context, execution


def approval_contract(task):
    basis = {
        'execution': task['observation_execution'], 'checks': task['checks'],
        'scope_snapshot': task['scope_snapshot']}
    if task.get('goal_observation') is not None:basis['goal_observation']=task['goal_observation']
    return {'format': FORMAT, 'fingerprint': digest(basis)}


def require(task, *, approved=False):
    from . import goal_observations
    goal_observations.require(task)
    execution = task.get('observation_execution')
    if execution is None:
        if task.get('observation_execution_contract') is not None:
            raise PlanningConflict('승인한 관찰 실행 입력이 없습니다.')
        return
    try:
        context = observation_context.require(task['worker_observation_context'])
        if (type(execution) is not dict or set(execution) != {
                'format', 'source_task_id', 'context_fingerprint', 'observation_ids', 'targets', 'fingerprint'}
                or execution['format'] != FORMAT
                or execution['source_task_id'] != context['source_task_id']
                or execution['context_fingerprint'] != context['fingerprint']
                or type(execution['targets']) is not list or not 1 <= len(execution['targets']) <= 10
                or type(execution['observation_ids']) is not list
                or any(type(id) is not str for id in execution['observation_ids'])
                or len(set(execution['observation_ids'])) != len(execution['observation_ids'])
                or not set(task['checks']) <= set(CHECKS)
                or execution['fingerprint'] != digest({k:v for k,v in execution.items() if k != 'fingerprint'})):
            raise ValueError()
        expected = {row['id']: row for row in context['items']}
        if execution['targets'] != [expected[id] for id in execution['observation_ids']]:raise ValueError()
        scopes = {asset['id']: asset for asset in task['scope_snapshot']}
        if set(scopes) != {row['asset_id'] for row in execution['targets']}:raise ValueError()
        seen = set()
        for row in execution['targets']:
            asset = scopes[row['asset_id']]
            if (asset['url'] != row['scope_url'] or type(asset.get('revision', 1)) is not int
                    or asset.get('revision', 1) != row['scope_revision']
                    or (row['asset_id'], row['url']) in seen):raise ValueError()
            seen.add((row['asset_id'], row['url']))
        if approved and task.get('observation_execution_contract') != approval_contract(task):raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise PlanningConflict('선택한 관찰 실행 입력·범위·승인 계약을 확인하세요.') from None


def targets_for(task, asset):
    require(task, approved=True)
    return [row for row in task.get('observation_execution', {}).get('targets', []) if row['asset_id'] == asset['id']]
