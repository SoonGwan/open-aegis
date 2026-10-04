"""Evidence-based, bounded follow-up proposals; proposal reads never execute tools."""
import hashlib
import json

from .checks import CATALOG, CHECK_IDS
from .coverage import task_rows
from .tool_contracts import contracts_for, require_contracts, ToolContractMismatch
from .worker_dependencies import validate

TERMINAL = {'completed', 'failed', 'stopped', 'interrupted'}
RETRYABLE = {'failed', 'cancelled', 'interrupted', 'not_recorded', 'not_started', 'running', 'stale'}
MAX_ROUNDS = 8


class NextPlanConflict(ValueError):
    pass


def propose(store, task_id, policy):
    with store.read_transaction() as db:
        source = store.get('tasks', task_id, connection=db)
        if source is None:
            raise LookupError('작업이 없습니다.')
        if (not isinstance(source, dict) or source.get('id') != task_id
                or source.get('status') not in TERMINAL or not source.get('approved_at')):
            raise NextPlanConflict('승인되어 종료된 작업의 결과에서만 다음 계획을 제안할 수 있습니다.')
        ids, scopes, checks = source.get('asset_ids'), source.get('scope_snapshot'), source.get('checks')
        try:
            validate(ids, source.get('worker_dependencies', {}))
            if (len(set(ids)) != len(ids) or not isinstance(scopes, list)
                    or [a['id'] for a in scopes] != ids or not isinstance(checks, list)
                    or not 1 <= len(checks) <= 6 or len(set(checks)) != len(checks)
                    or any(type(c) is not str or c not in CHECK_IDS for c in checks)
                    or not isinstance(source.get('name'), str) or not 1 <= len(source['name']) <= 120
                    or not isinstance(source.get('goal', ''), str) or len(source.get('goal', '')) > 2000
                    or type(source.get('workers', 3)) is not int or not 1 <= source.get('workers', 3) <= 4
                    or source.get('planner', 'rules') not in ('rules', 'ai')):
                raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise NextPlanConflict('원본 작업의 범위·도구·의존 관계 기록을 확인하세요.') from None
        round_number = source.get('planning_round', 0)
        if type(round_number) is not int or not 0 <= round_number <= MAX_ROUNDS:
            raise NextPlanConflict('계획 회차 기록을 확인하세요.')
        seen_checks = set(checks)
        ancestors = []
        history = [source]
        child = source
        expected_round = round_number
        visited = {task_id}
        while expected_round:
            parent_id = child.get('followup_of')
            if not isinstance(parent_id, str) or parent_id in visited:
                raise NextPlanConflict('반복 계획의 원본 연결을 확인하세요.')
            parent = store.get('tasks', parent_id, connection=db)
            if (not isinstance(parent, dict) or parent.get('id') != parent_id
                    or type(parent.get('planning_round', 0)) is not int
                    or parent.get('planning_round', 0) != expected_round - 1
                    or parent.get('next_plan_id') != child['id']
                    or parent.get('next_plan_fingerprint') != child.get('followup_fingerprint')
                    or parent.get('asset_ids') != ids or parent.get('status') not in TERMINAL
                    or not parent.get('approved_at') or not isinstance(parent.get('checks'), list)
                    or not 1 <= len(parent['checks']) <= 6
                    or any(type(c) is not str or c not in CHECK_IDS for c in parent['checks'])
                    or len(set(parent['checks'])) != len(parent['checks'])):
                raise NextPlanConflict('반복 계획의 원본 연결을 확인하세요.')
            parent_scopes = parent.get('scope_snapshot')
            if (not isinstance(parent_scopes, list) or any(not isinstance(a, dict) for a in parent_scopes)
                    or [a.get('id') for a in parent_scopes] != ids):
                raise NextPlanConflict('반복 계획의 원본 범위를 확인하세요.')
            seen_checks.update(parent['checks'])
            history.append(parent)
            ancestors.append({k: parent.get(k) for k in ('id', 'planning_round', 'checks', 'approved_at', 'status', 'next_plan_id', 'next_plan_fingerprint', 'scope_snapshot', 'tool_contracts')})
            visited.add(parent_id)
            child = parent
            expected_round -= 1
        if child.get('followup_of'):
            raise NextPlanConflict('반복 계획의 시작 회차를 확인하세요.')
        assets = [store.get('assets', id, connection=db) for id in ids]
        if any(not isinstance(a, dict) or a.get('id') != id or a.get('archived_at')
               or a.get('authorized') is not True for id, a in zip(ids, assets)):
            raise NextPlanConflict('현재 자산의 존재·보관·검증 권한을 확인하세요.')
        latest = {}
        current_revisions = {a['id']: a.get('revision', 1) for a in assets}
        for attempt in reversed(history):
            try:
                require_contracts(attempt)
                compatible = True
            except ToolContractMismatch:
                compatible = False
            rows = task_rows(store, attempt, get_record=lambda kind, id: store.get(kind, id, connection=db))
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
        missing = [c['id'] for c in CATALOG if c['id'] not in seen_checks]
        retry = [c['id'] for c in CATALOG if any(r['check'] == c['id'] and r['status'] in RETRYABLE for r in rows)]
        selected = [c['id'] for c in CATALOG if c['id'] in missing or c['id'] in retry]
        task = {'name': ('다음 계획 · ' + source['name'])[:120], 'goal': source.get('goal', ''),
                'asset_ids': ids, 'checks': selected, 'workers': source.get('workers', 3),
                'planner': source.get('planner', 'rules'),
                'worker_dependencies': source.get('worker_dependencies', {})}
        basis = {'source_task_id': task_id, 'source_status': source['status'],
                 'source_approved_at': source['approved_at'], 'source_tool_contracts': source.get('tool_contracts'),
                 'round': round_number, 'ancestors': ancestors,
                 'scope_snapshot': scopes, 'assets': assets, 'coverage': cells,
                 'task': task, 'tool_contracts': contracts_for(selected) if selected else None,
                 'execution_policy': policy}
        fingerprint = hashlib.sha256(json.dumps(basis, sort_keys=True, ensure_ascii=False,
                                                allow_nan=False, separators=(',', ':')).encode()).hexdigest()
        limited = round_number >= MAX_ROUNDS
        return {'format': 'aegis-next-plan-v1', 'source_task_id': task_id,
                'fingerprint': fingerprint, 'planning_round': round_number + 1,
                'round_limit': MAX_ROUNDS, 'available': bool(selected) and not limited and not source.get('next_plan_id'),
                'reason': 'already_accepted' if source.get('next_plan_id') else ('round_limit' if limited else ('results_followup' if selected else 'no_remaining_checks')),
                'task': task if selected and not limited else None,
                'basis': {'missing_checks': missing, 'retry_checks': retry, 'coverage': cells,
                          'skipped_cells': [r['id'] for r in rows if r['status'] == 'skipped'],
                          'repeated_completed_cells': [r['id'] for r in rows if r['status'] == 'completed' and r['check'] in selected]},
                'scope_snapshot': assets, 'execution_policy': policy,
                'tool_contracts': basis['tool_contracts'],
                'accepted_task_id': source.get('next_plan_id'),
                'execution_authorized': False}
