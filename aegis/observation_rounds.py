"""Selected observed URL/check follow-ups; proposal preparation never sends requests."""
import re
from . import observation_execution as execution, goal_observations, todos
from .planning_history import PlanningConflict,has_execution_approval,history,continuation,MAX_ROUNDS,MAX_HISTORY
from .coverage import task_rows
from .tool_contracts import require_contracts,ToolContractMismatch,contracts_for

FORMAT='aegis-observation-cells-v1'


def all_cells(task):
    return [{'observation_id':target['id'],'check':check}
            for target in task['observation_execution']['targets'] for check in task['checks']]


def require(task):
    selection=task.get('observation_cells')
    if selection is None:
        if task.get('observation_execution') and task.get('followup_of'):
            raise PlanningConflict('관찰 후속 회차의 선택 계약이 없습니다.')
        return
    try:
        cells=selection['cells'];allowed=all_cells(task)
        if (type(selection) is not dict or set(selection)!={'format','source_task_id','cells','fingerprint'}
                or selection['format']!=FORMAT or type(selection['source_task_id']) is not str
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',selection['source_task_id'])
                or selection['source_task_id']!=task.get('followup_of')
                or type(cells) is not list or not 1<=len(cells)<=40
                or any(type(row) is not dict or set(row)!={'observation_id','check'} for row in cells)
                or cells!=[row for row in allowed if row in cells]
                or selection['fingerprint']!=execution.digest({key:value for key,value in selection.items() if key!='fingerprint'})):
            raise ValueError()
    except (ValueError,KeyError,TypeError):
        raise PlanningConflict('관찰 후속 회차의 URL·검사 선택 계약을 확인하세요.') from None


def selected_cells(task):
    require(task)
    return task['observation_cells']['cells'] if task.get('observation_cells') else all_cells(task)


def checks_for(task,asset_id,ordered):
    if not task.get('observation_cells'):return list(ordered)
    ids={row['id'] for row in task['observation_execution']['targets'] if row['asset_id']==asset_id}
    chosen={row['check'] for row in selected_cells(task) if row['observation_id'] in ids}
    return [check for check in ordered if check in chosen]


def targets_for(task,targets,check):
    if not task.get('observation_cells'):return targets
    chosen={row['observation_id'] for row in selected_cells(task) if row['check']==check}
    return [target for target in targets if target['id'] in chosen]


def propose(store,source,policy,*,connection=None):
    from .next_plan import RETRYABLE
    if source.get('retest_of'):
        raise PlanningConflict('발견 재검증은 원래 발견에서 새 재검증 계획을 만드세요.')
    if (type(source.get('name')) is not str or not 1<=len(source['name'])<=120
            or type(source.get('goal','')) is not str or len(source.get('goal',''))>2000
            or type(source.get('workers',3)) is not int or not 1<=source.get('workers',3)<=4
            or source.get('planner','rules') not in ('rules','ai')):
        raise PlanningConflict('관찰 계획의 이름·목표·Worker 설정을 확인하세요.')
    execution.require(source,approved=True)
    family=history(store,source['id'],connection=connection)
    accepted,kind=continuation(store,source,connection=connection)
    assets=[store.get('assets',id,connection=connection) for id in source['asset_ids']]
    if any(not asset or not asset.get('authorized') or asset.get('archived_at') for asset in assets):
        raise PlanningConflict('현재 관찰 자산의 범위와 권한을 확인하세요.')
    origin=source.get('goal_observation');root=source['observation_execution']['source_task_id']
    reviewed=goal_observations.preview(store,root,origin['objective_id'],connection=connection) if origin else execution.preview(store,root,connection=connection)
    selection=execution.Selection(fingerprint=reviewed.get('fingerprint',reviewed['context']['fingerprint']),
        observation_ids=source['observation_execution']['observation_ids'],checks=source['checks'],
        request_id=origin['request_id'] if origin else execution.digest({'followup':source['id']})[:32])
    if origin:
        context,targets,fresh_origin=goal_observations.prepare(store,root,origin['objective_id'],selection,connection=connection)
        if any(fresh_origin[key]!=origin[key] for key in goal_observations.ORIGIN):
            raise PlanningConflict('원래 목표 과제가 변경되었습니다. 관찰 선택을 다시 검토하세요.')
    else:
        context,targets=execution.prepare(store,root,selection,connection=connection);fresh_origin=None
    wanted=all_cells(source);latest={}
    for attempt in reversed(family):
        if not has_execution_approval(attempt):continue
        execution.require(attempt,approved=True)
        old_origin=attempt.get('goal_observation')
        if bool(old_origin)!=bool(origin) or (origin and any(old_origin[key]!=origin[key] for key in goal_observations.ORIGIN)):
            raise PlanningConflict('관찰 후속 이력의 원래 목표 과제가 일치하지 않습니다.')
        if (attempt['observation_execution']['source_task_id']!=root
                or attempt['observation_execution']['observation_ids']!=source['observation_execution']['observation_ids']
                or attempt['checks']!=source['checks']):
            raise PlanningConflict('관찰 후속 회차의 원본 선택 이력이 일치하지 않습니다.')
        try:require_contracts(attempt);compatible=True
        except ToolContractMismatch:compatible=False
        rows={(row['asset_id'],row['check']):row for row in task_rows(store,attempt,get_record=lambda k,id:store.get(k,id,connection=connection))}
        by_id={row['id']:row for row in attempt['observation_execution']['targets']}
        revisions={a['id']:a.get('revision',1) for a in assets}
        for cell in selected_cells(attempt):
            target=by_id[cell['observation_id']];row=rows.get((target['asset_id'],cell['check']),{})
            results=row.get('targets',[])
            matches=[result for result in results if type(result) is dict and result.get('observation_id')==target['id'] and result.get('url')==target['url']] if type(results) is list else []
            status=matches[0].get('status') if len(matches)==1 else 'not_recorded'
            if (status not in {'completed','failed','cancelled'} or type(row.get('asset_revision')) is not int
                    or row['asset_revision']!=target['scope_revision']):status='not_recorded'
            if not compatible or target['scope_revision']!=revisions[target['asset_id']]:status='stale'
            latest[cell['observation_id'],cell['check']]=status
    shared=todos.planning_context(store,source['id'],connection=connection)
    requested=todos.requested_checks(shared);outside=[check for check in requested if check not in source['checks']]
    cells=[cell for cell in wanted if latest.get((cell['observation_id'],cell['check']),'not_recorded') in RETRYABLE or cell['check'] in requested]
    frozen={'format':FORMAT,'source_task_id':source['id'],'cells':cells}
    frozen['fingerprint']=execution.digest(frozen)
    task={'name':('관찰 다음 계획 · '+source['name'])[:120],'goal':source.get('goal',''),'asset_ids':source['asset_ids'],
          'checks':source['checks'],'workers':source.get('workers',3),'planner':source.get('planner','rules'),
          'worker_dependencies':source.get('worker_dependencies',{})}
    by_target={row['id']:row for row in targets['targets']}
    proof_cells=[dict(cell,id=cell['observation_id']+':'+cell['check'],
        asset_id=by_target[cell['observation_id']]['asset_id'],asset_revision=by_target[cell['observation_id']]['scope_revision'],
        url=by_target[cell['observation_id']]['url'],status=latest.get((cell['observation_id'],cell['check']),'not_recorded')) for cell in wanted]
    basis={'source':source,'family':family,'assets':assets,'coverage':proof_cells,
           'policy':policy,'todos':shared,'context':context,'execution':targets,'origin':fresh_origin,'selection':frozen,'task':task,
           'tool_contracts':contracts_for(source['checks'])}
    round_limited=source.get('planning_round',0)>=MAX_ROUNDS
    history_limited=len(family)>=MAX_HISTORY
    limited=round_limited or history_limited
    return {'format':'aegis-next-plan-v1','source_task_id':source['id'],'fingerprint':execution.digest(basis),
        'planning_round':source.get('planning_round',0)+1,'round_limit':MAX_ROUNDS,'history_limit':MAX_HISTORY,'history_count':len(family),
        'available':bool(cells) and not outside and not limited and accepted is None,
        'reason':'already_accepted' if accepted else 'history_limit' if history_limited else 'round_limit' if round_limited else 'observation_scope_change_required' if outside else 'observation_results_followup' if cells else 'no_remaining_observation_checks',
        'task':task if cells and not limited else None,'scope_snapshot':assets,'execution_policy':policy,'tool_contracts':basis['tool_contracts'],
        'observation_cells':frozen if cells else None,'observation_execution':targets,'observation_selection':selection.model_dump(),
        'goal_observation':fresh_origin,'worker_observation_context':context,'shared_todo_context':shared,
        'basis':{'coverage':basis['coverage'],'todo_requested_checks':requested,'todo_outside_goal_checks':outside,
                 'missing_checks':[],'retry_checks':list(dict.fromkeys(cell['check'] for cell in cells)),
                 'skipped_cells':[],'repeated_completed_cells':[]},
        'accepted_task_id':accepted['id'] if accepted else None,'accepted_kind':kind,'execution_authorized':False}
