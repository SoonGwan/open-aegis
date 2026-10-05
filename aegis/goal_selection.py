"""Immutable per-round subsets of an unchanged reviewed goal decomposition."""
from .planning_history import PlanningConflict

FORMAT = 'aegis-goal-selection-v1'


def pairs(plan):
    return {(asset, check) for objective in plan['decomposition']['objectives']
            for asset in objective['asset_ids'] for check in objective['checks']}


def prepare(task, rows, requested):
    from .goal_planner import digest
    from .next_plan import RETRYABLE
    allowed = pairs(task['goal_plan'])
    selected = {(row['asset_id'], row['check']) for row in rows
                if row['status'] in RETRYABLE and (row['asset_id'], row['check']) in allowed}
    selected.update(pair for pair in allowed if pair[1] in requested)
    # Handoffs are task-local: revalidate the full declared parent, recursively.
    dependencies = task.get('worker_dependencies', {})
    active = {asset for asset, _ in selected}
    pending = list(active)
    while pending:
        for parent in dependencies.get(pending.pop(), []):
            selected.update(pair for pair in allowed if pair[0] == parent)
            if parent not in active:
                active.add(parent); pending.append(parent)
    if not selected:
        return None
    value = {'format':FORMAT, 'source_task_id':task['id'],
             'cells':[{'asset_id':asset, 'check':check} for asset in task['asset_ids']
                      for check in task['checks'] if (asset, check) in selected]}
    return {**value, 'fingerprint':digest(value)}


def require(task, *, approved=False):
    from .goal_planner import digest
    value = task.get('goal_selection')
    if value is None:
        if task.get('goal_selection_contract') is not None:
            raise PlanningConflict('승인된 목표 회차의 선택 계약이 제거되었습니다.')
        return
    try:
        if (type(value) is not dict or set(value) != {'format','source_task_id','cells','fingerprint'}
                or value['format'] != FORMAT or type(value['source_task_id']) is not str
                or not value['source_task_id'] or task.get('followup_of') != value['source_task_id']
                or type(task.get('goal_plan')) is not dict
                or task['goal_plan'].get('execution') != 'objective_pairs'
                or type(value['cells']) is not list or not 1 <= len(value['cells']) <= 120
                or any(type(row) is not dict or set(row) != {'asset_id','check'}
                       or type(row['asset_id']) is not str or type(row['check']) is not str
                       for row in value['cells'])):
            raise ValueError()
        selected = {(row['asset_id'], row['check']) for row in value['cells']}
        allowed = pairs(task['goal_plan'])
        canonical = [{'asset_id':asset, 'check':check} for asset in task['asset_ids']
                     for check in task['checks'] if (asset, check) in selected]
        if (not selected <= allowed or canonical != value['cells']
                or value['fingerprint'] != digest({key:item for key,item in value.items() if key != 'fingerprint'})):
            raise ValueError()
        for child in {asset for asset, _ in selected}:
            for parent in task.get('worker_dependencies', {}).get(child, []):
                if not {pair for pair in allowed if pair[0] == parent} <= selected:
                    raise ValueError()
        if (approved or task.get('goal_selection_contract') is not None) and task.get('goal_selection_contract') != value:
            raise ValueError()
    except (ValueError,KeyError,TypeError):
        raise PlanningConflict('목표 후속 회차의 선택 조합·승인 계약을 확인하세요.') from None
