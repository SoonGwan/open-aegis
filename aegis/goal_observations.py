"""Objective-bound, explicitly selected observed-response plans; never goal proof."""
from contextlib import nullcontext
import re
from . import goal_planner, observation_execution, observation_context
from .planning_history import PlanningConflict

FORMAT = 'aegis-goal-observation-v1'
FIELDS = {'format','source_task_id','source_task_name','source_plan_fingerprint','objective_id',
          'objective_title','objective_asset_ids','objective_checks','request_id','selection_fingerprint','fingerprint'}
ORIGIN = FIELDS - {'request_id','selection_fingerprint','fingerprint'}


def preview(store, source_id, objective_id, *, connection=None):
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        source = store.get('tasks',source_id,connection=db)
        if not source:raise LookupError('출처 작업이 없습니다.')
        goal_planner.require_task(source)
        if not source.get('goal_plan') or not goal_planner.has_execution_approval(source):
            raise PlanningConflict('승인된 목표 작업의 과제에서 관찰을 선택하세요.')
        objective = next((row for row in source['goal_plan']['decomposition']['objectives'] if row['id']==objective_id),None)
        if not objective:raise LookupError('목표 과제가 없습니다.')
        context = observation_execution.preview(store,source_id,connection=db)['context']
        included = [row for row in context['items'] if row['asset_id'] in objective['asset_ids']]
        counts = {**context['counts'],'included':len(included),
                  'excluded':context['counts']['excluded']+len(context['items'])-len(included)}
        context = {**context,'items':included,'counts':counts}
        context['fingerprint'] = observation_execution.digest({key:value for key,value in context.items() if key!='fingerprint'})
        observation_context.require(context)
        origin = {'format':FORMAT,'source_task_id':source_id,'source_task_name':source['name'],
                  'source_plan_fingerprint':source['goal_plan']['fingerprint'],'objective_id':objective_id,
                  'objective_title':objective['title'],'objective_asset_ids':objective['asset_ids'],
                  'objective_checks':objective['checks']}
        fingerprint = goal_planner.digest({'origin':origin,'context':context['fingerprint']})
        return {'context':context,'fingerprint':fingerprint,'origin':origin,
                'checks':[check for check in observation_execution.CHECKS if check in objective['checks']],
                'max_targets':10,'execution_authorized':False,'goal_verified':False}


def prepare(store, source_id, objective_id, selection, *, connection=None):
    reviewed = preview(store,source_id,objective_id,connection=connection)
    if reviewed['fingerprint'] != selection.fingerprint or not set(selection.checks)<=set(reviewed['checks']):
        raise PlanningConflict('목표 과제·관찰 근거 또는 선언한 응답 검사가 변경되었습니다.')
    context, execution = observation_execution.prepare_context(reviewed['context'],
        selection.model_copy(update={'fingerprint':reviewed['context']['fingerprint']}))
    ref = {**reviewed['origin'],'request_id':selection.request_id,'selection_fingerprint':selection.fingerprint}
    ref['fingerprint'] = goal_planner.digest(ref)
    return context, execution, ref


def require(task):
    ref = task.get('goal_observation')
    if ref is None:
        selection,execution=task.get('observation_selection'),task.get('observation_execution')
        if isinstance(selection,dict) and isinstance(execution,dict) and selection.get('fingerprint')!=execution.get('context_fingerprint'):
            raise PlanningConflict('목표 과제에 연결한 관찰 선택 참조가 제거되었습니다.')
        return
    try:
        selection=observation_execution.Selection.model_validate(task['observation_selection'])
        if (type(ref) is not dict or set(ref)!=FIELDS or ref['format']!=FORMAT
                or any(type(ref[key]) is not str or not ref[key] for key in FIELDS-{'objective_asset_ids','objective_checks'})
                or ref['objective_id'] not in {'g'+str(i) for i in range(1,13)}
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',ref['source_task_id'])
                or len(ref['source_task_name'])>120 or len(ref['objective_title'])>200
                or any(not re.fullmatch(r'[a-f0-9]{64}',ref[key]) for key in ('source_plan_fingerprint','selection_fingerprint','fingerprint'))
                or not re.fullmatch(r'[a-f0-9]{32}',ref['request_id'])
                or type(ref['objective_asset_ids']) is not list or not 1<=len(ref['objective_asset_ids'])<=20
                or type(ref['objective_checks']) is not list or not 1<=len(ref['objective_checks'])<=6
                or any(type(value) is not str for key in ('objective_asset_ids','objective_checks') for value in ref[key])
                or len(set(ref['objective_asset_ids']))!=len(ref['objective_asset_ids'])
                or len(set(ref['objective_checks']))!=len(ref['objective_checks'])
                or ref['fingerprint']!=goal_planner.digest({key:value for key,value in ref.items() if key!='fingerprint'})
                or task.get('goal_plan') or task.get('goal_retest')
                or not set(task['asset_ids'])<=set(ref['objective_asset_ids'])
                or not set(task['checks'])<=set(ref['objective_checks'])
                or not set(ref['objective_checks'])<=goal_planner.CHECK_IDS
                or selection.checks!=task['checks']
                or selection.observation_ids!=task['observation_execution']['observation_ids']
                or task['observation_execution']['source_task_id']!=ref['source_task_id']
                or task['observation_selection']['request_id']!=ref['request_id']
                or task['observation_selection']['fingerprint']!=ref['selection_fingerprint']):
            raise ValueError()
    except (ValueError,KeyError,TypeError):
        raise PlanningConflict('관찰 응답 계획의 원래 목표 과제·선택 참조를 확인하세요.') from None
