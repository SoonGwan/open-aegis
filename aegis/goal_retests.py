"""Immutable objective origin for separately approved finding retests."""
from . import goal_evidence, goal_planner
from .planning_history import PlanningConflict

FIELDS={'format','objective_title','source_task_name','source_task_id','objective_id','source_plan_fingerprint','finding_id',
        'finding_fingerprint','asset_id','check','request_id','fingerprint'}


def prepare(store, source_id, objective_id, finding_id, request_id, *, connection=None):
    page=goal_evidence.page(store,source_id,objective_id,limit=1,finding_id=finding_id,connection=connection)
    if not page['items']:raise PlanningConflict('원래 과제의 출처 증거가 일치하는 발견만 재검증할 수 있습니다.')
    source=store.get('tasks',source_id,connection=connection)
    finding=store.get('findings',finding_id,connection=connection)
    objective=next(row for row in source['goal_plan']['decomposition']['objectives'] if row['id']==objective_id)
    value={'format':'aegis-goal-retest-v1','objective_title':objective['title'],'source_task_name':source['name'],'source_task_id':source_id,'objective_id':objective_id,
           'source_plan_fingerprint':source['goal_plan']['fingerprint'],'finding_id':finding_id,
           'finding_fingerprint':finding['fingerprint'],'asset_id':finding['asset_id'],
           'check':finding['check'],'request_id':request_id}
    value['fingerprint']=goal_planner.digest(value)
    return value


def require(task):
    value=task.get('goal_retest')
    if value is None:return
    try:
        if (type(value) is not dict or set(value)!=FIELDS or value['format']!='aegis-goal-retest-v1'
                or any(type(value[key]) is not str or not value[key] for key in FIELDS)
                or value['fingerprint']!=goal_planner.digest({key:v for key,v in value.items() if key!='fingerprint'})
                or task.get('retest_of')!=value['finding_id'] or task['asset_ids']!=[value['asset_id']]
                or task['checks']!=[value['check']] or type(task.get('scope_snapshot')) is not list
                or len(task['scope_snapshot'])!=1 or task['scope_snapshot'][0]['id']!=value['asset_id'] or task.get('goal_plan') or task.get('observation_execution')):
            raise ValueError()
    except (ValueError,TypeError,KeyError):
        raise PlanningConflict('목표 재검증의 과제 참조와 실행 계약이 일치하지 않습니다.') from None
