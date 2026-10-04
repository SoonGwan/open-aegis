"""Evidence-based, bounded follow-up proposals; proposal reads never execute tools."""
import hashlib
import json
from contextlib import nullcontext
from . import todos, observation_context

from .checks import CATALOG, CHECK_IDS
from .coverage import task_rows
from .tool_contracts import contracts_for, require_contracts, ToolContractMismatch
from .planning_history import history as read_history, continuation, PlanningConflict, MAX_ROUNDS, MAX_HISTORY

TERMINAL = {'completed', 'failed', 'stopped', 'interrupted'}
RETRYABLE = {'failed', 'cancelled', 'interrupted', 'not_recorded', 'not_started', 'running', 'stale'}


NextPlanConflict = PlanningConflict


def propose(store, task_id, policy, *, connection=None):
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        from . import goal_planner
        source = store.get('tasks', task_id, connection=db)
        if source is None:
            raise LookupError('작업이 없습니다.')
        if (not isinstance(source, dict) or source.get('id') != task_id
                or source.get('status') not in TERMINAL or not source.get('approved_at')):
            raise NextPlanConflict('승인되어 종료된 작업의 결과에서만 다음 계획을 제안할 수 있습니다.')
        if source.get('observation_execution'):
            raise NextPlanConflict('관찰 응답 계획은 출처 작업의 관찰 목록에서 새 선택 계획을 만드세요. 기본 자산 검증의 완료 근거로 사용하지 않습니다.')
        if source.get('goal_retest'):
            raise NextPlanConflict('목표 발견 재검증은 원래 과제의 발견에서 새 재검증 계획을 만드세요.')
        goal_planner.require_task(source)
        goal=source.get('goal_plan')
        history = read_history(store, task_id, connection=db)
        if goal and any(attempt.get('goal_plan')!=goal for attempt in history):
            raise NextPlanConflict('목표 과제와 다른 후속 이력이 있습니다. 새 목표 초안을 검토하세요.')
        ids, scopes, checks = source['asset_ids'], source['scope_snapshot'], source['checks']
        if (not isinstance(source.get('name'), str) or not 1 <= len(source['name']) <= 120
                or not isinstance(source.get('goal', ''), str) or len(source.get('goal', '')) > 2000
                or type(source.get('workers', 3)) is not int or not 1 <= source.get('workers', 3) <= 4
                or source.get('planner', 'rules') not in ('rules', 'ai')):
            raise NextPlanConflict('원본 작업의 이름·목표·Worker 설정을 확인하세요.')
        round_number = source.get('planning_round', 0)
        seen_checks = {check for attempt in history if attempt.get('approved_at') for check in attempt['checks']}
        ancestors = [{k: t.get(k) for k in ('id', 'planning_round', 'checks', 'approved_at', 'status',
                     'next_plan_id', 'next_plan_fingerprint', 'scope_snapshot', 'tool_contracts',
                     'followup_of', 'followup_fingerprint', 'retry_of', 'replan_of', 'replaced_by', 'retry_successor', 'goal_plan')}
                     for t in history[1:]]
        accepted, accepted_kind = continuation(store, source, connection=db)
        assets = [store.get('assets', id, connection=db) for id in ids]
        if any(not isinstance(a, dict) or a.get('id') != id or a.get('archived_at')
               or a.get('authorized') is not True for id, a in zip(ids, assets)):
            raise NextPlanConflict('현재 자산의 존재·보관·검증 권한을 확인하세요.')
        latest = {}
        current_revisions = {a['id']: a.get('revision', 1) for a in assets}
        for attempt in reversed(history):
            if not attempt.get("approved_at"):continue
            try:
                require_contracts(attempt)
                compatible = True
            except ToolContractMismatch:
                compatible = False
            rows = task_rows(store, {**attempt, "created_at": attempt.get("created_at", 0)}, get_record=lambda kind, id: store.get(kind, id, connection=db))
            revisions = {a['id']: a.get('revision', 1) for a in attempt['scope_snapshot']}
            for row in rows:
                if (type(row.get('asset_revision')) is not int
                        or row['asset_revision'] != revisions[row['asset_id']]):
                    row['status'] = 'not_recorded'
                elif current_revisions[row['asset_id']] != revisions[row['asset_id']]:
                    row['status'] = 'stale'
                if not compatible:
                    row['status'] = 'stale'
                latest[row['asset_id'], row['check']] = row
        rows = list(latest.values())
        cells = [{k: r.get(k) for k in ('id', 'asset_id', 'asset_revision', 'check', 'status')}
                 for r in rows]
        missing = [] if goal else [c['id'] for c in CATALOG if c['id'] not in seen_checks]
        retry = [c['id'] for c in CATALOG if any(r['check'] == c['id'] and r['status'] in RETRYABLE for r in rows)]
        context=todos.planning_context(store,task_id,connection=db)
        requested=todos.requested_checks(context)
        observations=observation_context.snapshot(store,task_id,connection=db)
        selected = [c['id'] for c in CATALOG if c['id'] in missing or c['id'] in retry or c['id'] in requested]
        outside_goal=[check for check in requested if check not in checks] if goal else []
        if goal:selected=list(checks) if retry or any(check in checks for check in requested) else []
        task = {'name': ('다음 계획 · ' + source['name'])[:120], 'goal': source.get('goal', ''),
                'asset_ids': ids, 'checks': selected, 'workers': source.get('workers', 3),
                'planner': source.get('planner', 'rules'),
                'worker_dependencies': source.get('worker_dependencies', {})}
        basis = {'source_task_id': task_id, 'source_status': source['status'],
                 'source_approved_at': source['approved_at'], 'goal_plan':goal, 'source_tool_contracts': source.get('tool_contracts'),
                 'round': round_number, 'ancestors': ancestors,
                 'scope_snapshot': scopes, 'assets': assets, 'coverage': cells,
                 'task': task, 'tool_contracts': contracts_for(selected) if selected else None,
                 'execution_policy': policy, 'shared_todo_context':context, 'worker_observation_context':observations}
        fingerprint = hashlib.sha256(json.dumps(basis, sort_keys=True, ensure_ascii=False,
                                                allow_nan=False, separators=(',', ':')).encode()).hexdigest()
        limited = round_number >= MAX_ROUNDS
        history_limited = len(history) >= MAX_HISTORY
        return {'format': 'aegis-next-plan-v1', 'source_task_id': task_id,
                'fingerprint': fingerprint, 'planning_round': round_number + 1,
                'round_limit': MAX_ROUNDS, 'history_limit': MAX_HISTORY, 'history_count': len(history),
                'available': bool(selected) and not outside_goal and not limited and not history_limited and accepted is None,
                'reason': 'already_accepted' if accepted else ('history_limit' if history_limited else 'round_limit' if limited else 'goal_scope_change_required' if outside_goal else ('goal_results_followup' if goal else 'results_followup') if selected else ('no_remaining_goal_checks' if goal else 'no_remaining_checks')),
                'task': task if selected and not limited and not history_limited else None,
                'goal_plan':goal,
                'shared_todo_context':context,
                'worker_observation_context':observations,
                'basis': {'missing_checks': missing, 'retry_checks': retry, 'todo_requested_checks':requested, 'coverage': cells,
                          'todo_outside_goal_checks':outside_goal,
                          'skipped_cells': [r['id'] for r in rows if r['status'] == 'skipped'],
                          'repeated_completed_cells': [r['id'] for r in rows if r['status'] == 'completed' and r['check'] in selected]},
                'scope_snapshot': assets, 'execution_policy': policy,
                'tool_contracts': basis['tool_contracts'],
                'accepted_task_id': accepted['id'] if accepted else None, 'accepted_kind': accepted_kind,
                'execution_authorized': False}
