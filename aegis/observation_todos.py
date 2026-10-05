"""Durable failure notes from verified observation proposals; no execution request."""
import re
from . import todos,observation_execution
from .findings import public_actor
from .next_plan import RETRYABLE
from .planning_history import PlanningConflict
from .store_util import now,identifier

FORMAT='aegis-observation-todo-v1'


def ensure(store,task_id,proposal,db):
    if not proposal.get('observation_execution'):return {'status':'not_applicable'}
    cells=[{key:row[key] for key in ('observation_id','check')} for row in proposal['basis']['coverage'] if row['status'] in RETRYABLE]
    if not cells:return {'status':'no_failures'}
    context=todos.planning_context(store,task_id,connection=db);root=context['root_task_id']
    identity={'format':FORMAT,'root_task_id':root,'cells':cells}
    todo_id=observation_execution.digest(identity)
    existing=store.get('todos',todo_id,connection=db)
    if existing is not None:
        existing=todos.record(store,todo_id,root,db)
        origin=existing.get('automatic_origin')
        try:
            if (type(origin) is not dict or set(origin)!={'format','root_task_id','source_task_id','cells','fingerprint'}
                    or any(origin[key]!=identity[key] for key in identity)
                    or type(origin['source_task_id']) is not str
                    or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',origin['source_task_id'])
                    or origin['source_task_id']!=existing.get('origin_task_id')
                    or origin['fingerprint']!=observation_execution.digest({key:value for key,value in origin.items() if key!='fingerprint'})):
                raise ValueError()
        except (ValueError,KeyError,TypeError):
            raise PlanningConflict('자동 관찰 할 일의 원본 참조를 확인하세요.') from None
        return {'status':'existing','todo_id':todo_id}
    if len(context['items'])>=todos.MAX_CONTEXT_TODOS:return {'status':'limited'}
    origin={**identity,'source_task_id':task_id};origin['fingerprint']=observation_execution.digest(origin)
    timestamp=now()
    row={'id':todo_id,'task_id':root,'origin_task_id':task_id,'automatic_origin':origin,
        'title':f'관찰 응답 미완료 조합 {len(cells)}개 확인',
        'description':f'승인된 관찰 검사 작업 {task_id}의 실패·누락 결과에서 자동 기록했습니다. 원본 작업의 URL별 근거를 확인하세요. 검사 실패는 취약점이나 목표 달성 판정이 아닙니다. 검사 요청을 자동 추가하지 않으며 후속 실행에는 새 승인이 필요합니다.',
        'check_ids':[],'status':'open','revision':1,'resolution_note':'','created_at':timestamp,'updated_at':timestamp,
        'created_by':public_actor(task_id=task_id),**todos.assignee(store,None,db)}
    item={key:row[key] for key in ('id','revision','status','title','description','check_ids','resolution_note')}
    candidate={key:value for key,value in context.items() if key!='fingerprint'}
    candidate['items']=sorted([*context['items'],item],key=lambda item:item['id'])
    candidate['fingerprint']=observation_execution.digest(candidate)
    try:todos.require_context(candidate)
    except PlanningConflict:return {'status':'limited'}
    entry={'id':identifier(),'task_id':root,'origin_task_id':task_id,'todo_id':todo_id,'action':'automatically_created',
        'actor':public_actor(task_id=task_id),'created_at':timestamp,'revision':1,'reason':'승인된 관찰 검사 미완료 결과',
        'changes':{key:{'before':None,'after':row[key]} for key in ('title','description','status','check_ids')}}
    store.put_many([('todos',row),('todo_history',entry)],connection=db)
    store.event(task_id,'관찰 검사 미완료 결과의 공유 할 일을 자동 기록했습니다.',
        detail={'todo_id':todo_id,'root_task_id':root,'action':'automatically_created','execution_authorized':False},connection=db)
    return {'status':'created','todo_id':todo_id}
