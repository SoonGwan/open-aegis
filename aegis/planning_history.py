"""Bounded immutable continuation links; metadata consistency is not a signature."""
import json
import re
from contextlib import nullcontext

from .checks import CHECK_IDS
from .worker_dependencies import validate

MAX_ROUNDS = 8
MAX_HISTORY = 32
TERMINAL = {'completed', 'failed', 'stopped', 'interrupted'}
STATES = TERMINAL | {'pending', 'queued', 'running', 'stopping', 'rejected'}


class PlanningConflict(ValueError):
    pass


def record(store, id, db):
    if type(id) is not str or not id:raise PlanningConflict('작업 ID를 확인하세요.')
    task = store.get('tasks', id, connection=db)
    if task is None:raise LookupError('작업이 없습니다.')
    try:
        ids, scopes, checks = task['asset_ids'], task['scope_snapshot'], task['checks']
        validate(ids, task.get('worker_dependencies', {}))
        if (task.get('id') != id or len(set(ids)) != len(ids)
                or not isinstance(scopes, list) or any(not isinstance(a, dict) for a in scopes)
                or [a.get('id') for a in scopes] != ids or not isinstance(checks, list)
                or not 1 <= len(checks) <= 6
                or any(type(c) is not str or c not in CHECK_IDS for c in checks)
                or len(set(checks)) != len(checks) or task.get('status') not in STATES
                or type(task.get('planning_round', 0)) is not int
                or not 0 <= task.get('planning_round', 0) <= MAX_ROUNDS
                or (task.get('planning_round', 0) and (type(task.get('followup_of')) is not str
                    or type(task.get('followup_fingerprint')) is not str
                    or not re.fullmatch(r'[a-f0-9]{64}', task['followup_fingerprint'])))):
            raise ValueError()
    except (TypeError, ValueError, KeyError):
        raise PlanningConflict('계획의 자산·도구·회차 기록을 확인하세요.') from None
    forwards = [key for key in ('next_plan_id', 'retry_successor', 'replaced_by') if task.get(key)]
    if (len(forwards) > 1
            or (task.get('next_plan_id') and (task['status'] not in TERMINAL or not task.get('approved_at')))
            or (task.get('retry_successor') and task['status'] not in {'failed', 'interrupted', 'stopped'})
            or (task.get('replaced_by') and (task['status'] != 'rejected'
                or task.get('termination_reason') != 'replanned' or task.get('approved_at')))):
        raise PlanningConflict('계획의 상태와 후속 연결이 충돌합니다.')
    return task


def linked_record(store, id, db):
    try:return record(store, id, db)
    except LookupError:
        raise PlanningConflict('연결된 원본 계획을 찾을 수 없습니다.') from None


def metadata(task):
    result = {'planning_round': task.get('planning_round', 0)}
    if task.get('followup_of') is not None:
        result.update(followup_of=task['followup_of'], followup_fingerprint=task.get('followup_fingerprint'))
    return result


def _same_round(parent, child):
    if (metadata(parent) != metadata(child) or parent['asset_ids'] != child['asset_ids']
            or parent['checks'] != child['checks']
            or json.dumps(parent.get('worker_dependencies', {}), sort_keys=True)
            != json.dumps(child.get('worker_dependencies', {}), sort_keys=True)):
        raise PlanningConflict('교체·재실행의 회차·범위·검증 관계가 일치하지 않습니다.')


def _attempt_edge(parent, child, kind):
    _same_round(parent, child)
    if kind == 'replan_of':
        if (parent.get('replaced_by') != child['id'] or parent.get('status') != 'rejected'
                or parent.get('termination_reason') != 'replanned' or parent.get('approved_at')):
            raise PlanningConflict('교체 계획의 원본 연결이 일치하지 않습니다.')
    elif parent.get('next_plan_id'):
        raise PlanningConflict('후속 계획과 재실행 연결이 충돌합니다.')
    elif parent.get('status') not in {'failed', 'interrupted', 'stopped'}:
        raise PlanningConflict('재실행 계획의 원본 상태가 일치하지 않습니다.')
    elif parent.get('retry_successor') not in (None, child['id']):
        raise PlanningConflict('재실행 계획의 원본 연결이 일치하지 않습니다.')


def history(store, task_id, *, connection=None):
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        current = record(store, task_id, db)
        result, visited = [], set()
        while True:
            if current['id'] in visited or len(result) >= MAX_HISTORY:
                raise PlanningConflict('계획 연결이 순환하거나 이력 한도(32개)를 초과했습니다.')
            result.append(current);visited.add(current['id'])
            retry, replan = current.get('retry_of'), current.get('replan_of')
            if retry and replan:raise PlanningConflict('교체와 재실행 원본이 동시에 지정되었습니다.')
            previous = retry or replan
            if previous:
                if type(previous) is not str:raise PlanningConflict('원본 작업 ID를 확인하세요.')
                parent = linked_record(store, previous, db)
                _attempt_edge(parent, current, 'retry_of' if retry else 'replan_of')
            elif current.get('planning_round', 0):
                previous = current.get('followup_of')
                if type(previous) is not str:raise PlanningConflict('후속 계획의 원본 ID를 확인하세요.')
                parent = linked_record(store, previous, db)
                if (parent.get('planning_round', 0) != current['planning_round'] - 1
                        or parent.get('next_plan_id') != current['id']
                        or not current.get('followup_fingerprint')
                        or parent.get('next_plan_fingerprint') != current.get('followup_fingerprint')
                        or parent['asset_ids'] != current['asset_ids']
                        or parent.get('status') not in TERMINAL or not parent.get('approved_at')):
                    raise PlanningConflict('후속 계획의 회차·원본 연결이 일치하지 않습니다.')
            else:
                if current.get('followup_of') or current.get('followup_fingerprint'):
                    raise PlanningConflict('시작 회차의 원본 연결을 확인하세요.')
                break
            current = parent
        return result


def resolve(store, first_id, *, connection=None):
    """Find the current attempt of one round without traversing later follow-up rounds."""
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        current = record(store, first_id, db)
        visited = set()
        while current.get('replaced_by') or current.get('retry_successor'):
            if current['id'] in visited or len(visited) >= MAX_HISTORY - 1:
                raise PlanningConflict('계획 연결이 순환하거나 이력 한도(32개)를 초과했습니다.')
            visited.add(current['id'])
            if current.get('replaced_by') and current.get('retry_successor'):
                raise PlanningConflict('교체와 재실행 연결이 충돌합니다.')
            key = 'replan_of' if current.get('replaced_by') else 'retry_of'
            child = linked_record(store, current.get('replaced_by') or current.get('retry_successor'), db)
            if child.get(key) != current['id']:raise PlanningConflict('연결된 계획의 원본 ID가 일치하지 않습니다.')
            _attempt_edge(current, child, key)
            current = child
        history(store, current["id"], connection=db)
        return current


def continuation(store, source, *, connection=None):
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        if source.get('next_plan_id') and source.get('retry_successor'):
            raise PlanningConflict('후속 계획과 재실행 연결이 충돌합니다.')
        kind = 'followup' if source.get('next_plan_id') else 'retry' if source.get('retry_successor') else None
        if kind is None:return None, None
        first = linked_record(store, source['next_plan_id'] if kind == 'followup' else source['retry_successor'], db)
        if kind == 'followup':
            if (first.get('followup_of') != source['id']
                    or first.get('planning_round') != source.get('planning_round', 0) + 1
                    or first.get('followup_fingerprint') != source.get('next_plan_fingerprint')
                    or first['asset_ids'] != source['asset_ids']):
                raise PlanningConflict('후속 계획의 원본 연결이 일치하지 않습니다.')
        else:
            if first.get('retry_of') != source['id']:raise PlanningConflict('재실행 원본 ID가 일치하지 않습니다.')
            _attempt_edge(source, first, 'retry_of')
        return resolve(store, first['id'], connection=db), kind
