"""Human decisions shared by a verified planning family; never execution authority."""
import hashlib
import json
import re
from contextlib import nullcontext
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from .planning_history import history
from .findings import public_actor
from .store_util import identifier, now
from .checks import CATALOG, CHECK_IDS
from .planning_history import PlanningConflict


class TodoConflict(ValueError):
    pass


def checked_ids(value):
    if len(set(value)) != len(value) or not set(value) <= CHECK_IDS:
        raise ValueError("등록된 검증 도구를 중복 없이 선택하세요.")
    return [c["id"] for c in CATALOG if c["id"] in value]


class TodoCreate(BaseModel):
    model_config = {'extra': 'forbid'}
    request_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=4000)
    assignee_id: str | None = Field(default=None, min_length=1, max_length=80)
    check_ids: list[str] = Field(default_factory=list, max_length=6)

    @field_validator('check_ids')
    @classmethod
    def checks(cls,value):return checked_ids(value)

    @field_validator('title','description')
    @classmethod
    def trim(cls,value):return value.strip()

    @model_validator(mode='after')
    def nonempty(self):
        if not self.title:raise ValueError('할 일 제목을 입력하세요.')
        return self


class TodoUpdate(BaseModel):
    model_config = {'extra': 'forbid'}
    expected_revision: int = Field(ge=1, strict=True)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    status: Literal['open','in_progress','done','cancelled'] | None = None
    assignee_id: str | None = Field(default=None, min_length=1, max_length=80)
    resolution_note: str | None = Field(default=None, max_length=2000)
    check_ids: list[str] | None = Field(default=None, max_length=6)

    @field_validator('check_ids')
    @classmethod
    def checks(cls,value):return checked_ids(value) if value is not None else value

    @field_validator('title','description','resolution_note')
    @classmethod
    def trim(cls,value):return value.strip() if value is not None else value

    @model_validator(mode='after')
    def changes(self):
        changed=self.model_fields_set-{'expected_revision'}
        if not changed or any(getattr(self,key) is None for key in changed-{'assignee_id'}):
            raise ValueError('변경할 할 일 항목을 입력하세요.')
        if 'title' in changed and not self.title:raise ValueError('할 일 제목을 입력하세요.')
        return self


def root(store, task_id, db):
    return history(store,task_id,connection=db)[-1]['id']


def record(store, todo_id, root_id, db):
    getter=getattr(store,'get_optional',store.get)
    row=getter('todos',todo_id,connection=db)
    if row is None or row.get('task_id')!=root_id:raise LookupError('이 계획의 할 일이 없습니다.')
    if row.get('id')!=todo_id or type(row.get('revision')) is not int or row['revision']<1:
        raise TodoConflict('할 일의 저장 ID·버전을 확인하세요.')
    return row


def get(store, task_id, todo_id):
    with store.read_transaction() as db:
        return record(store,todo_id,root(store,task_id,db),db)


def assignee(store, assignee_id, db):
    if assignee_id is None:return {'assignee_id':None,'assignee_name':None,'assignee_username':None}
    user=store.user(id=assignee_id,connection=db)
    if not user or user['disabled'] or user['role'] not in ('admin','operator'):
        raise ValueError('활성 관리자 또는 운영자를 담당자로 선택하세요.')
    return {key:user[field] for key,field in (('assignee_id','id'),('assignee_name','name'),('assignee_username','username'))}


def commit(store, row, before, action, actor, task_id, db):
    entry={'id':identifier(),'task_id':row['task_id'],'origin_task_id':task_id,'todo_id':row['id'],
           'action':action,'actor':public_actor(actor),'created_at':now(), 'revision':row['revision'],
           'reason':row.get('resolution_note',''),
           'changes':{key:{'before':before.get(key),'after':row.get(key)} for key in
                      ('title','description','status','assignee_id','assignee_name','resolution_note','check_ids')
                      if before.get(key)!=row.get(key)}}
    store.put_many([('todos',row),('todo_history',entry)],connection=db)
    store.event(task_id,'공유 할 일 기록을 저장했습니다.',detail={
        'todo_id':row['id'],'root_task_id':row['task_id'],'revision':row['revision'],
        'actor_id':actor['id'],'action':action},connection=db)
    return row


def create(store, task_id, data, actor):
    payload=TodoCreate.model_validate(data).model_dump()
    with store.write_transaction() as db:
        root_id=root(store,task_id,db)
        todo_id=hashlib.sha256((root_id+':'+actor['id']+':'+payload['request_id']).encode()).hexdigest()
        digest=hashlib.sha256(json.dumps({k:v for k,v in payload.items() if k!='request_id' and (k!='check_ids' or v)},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        existing=store.get('todos',todo_id,connection=db)
        if existing is not None:
            existing=record(store,todo_id,root_id,db)
            if existing.get('creation_digest')!=digest:raise TodoConflict('같은 생성 요청 ID의 내용이 다릅니다.')
            return existing
        row={'id':todo_id,'task_id':root_id,'origin_task_id':task_id,'title':payload['title'],
             'description':payload['description'],'check_ids':payload['check_ids'],'status':'open','revision':1,'resolution_note':'',
             'created_at':now(),'updated_at':now(),'creation_digest':digest,
             'created_by':public_actor(actor),**assignee(store,payload['assignee_id'],db)}
        return commit(store,row,{},'created',actor,task_id,db)


def update(store, task_id, todo_id, data, actor):
    payload=TodoUpdate.model_validate(data).model_dump(exclude_unset=True)
    with store.write_transaction() as db:
        row=record(store,todo_id,root(store,task_id,db),db)
        if payload.pop('expected_revision')!=row['revision']:
            raise TodoConflict('다른 사용자가 할 일을 변경했습니다. 최신 기록을 확인한 뒤 다시 저장하세요.')
        if payload.get('check_ids')==row.get('check_ids',[]) and 'check_ids' in payload:payload.pop('check_ids')
        after={**row,**payload}
        if after['status'] in ('done','cancelled') and (not after.get('resolution_note') or
                (after['status']!=row['status'] and not payload.get('resolution_note'))):
            raise ValueError('완료·취소 사유를 입력하세요. 할 일 완료는 검증 성공 판정이 아닙니다.')
        if after['status'] not in ('done','cancelled') and after['status']!=row['status'] and 'resolution_note' not in payload:
            after['resolution_note']=''
        if 'assignee_id' in payload and payload['assignee_id']!=row.get('assignee_id'):
            after.update(assignee(store,payload['assignee_id'],db))
        if after==row:return row
        after.update(revision=row['revision']+1,updated_at=now())
        return commit(store,after,row,'updated',actor,task_id,db)


def page(store, task_id, *, todo_id=None, connection=None, **options):
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        root_id=root(store,task_id,db)
        filters={'task_id':root_id}
        if todo_id is not None:
            record(store,todo_id,root_id,db);filters['todo_id']=todo_id
        result=store.page('todos' if todo_id is None else 'todo_history',filters=filters,connection=db,**options)
        return {**result,'root_task_id':root_id,'source_task_id':task_id,'execution_authorized':False}


# Full bounded context, never a silently truncated page. Older rows have no check_ids.
MAX_CONTEXT_TODOS = 100
MAX_CONTEXT_BYTES = 64 * 1024

def planning_context(store, task_id, *, connection=None):
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        root_id=root(store,task_id,db)
        result=store.page('todos',limit=MAX_CONTEXT_TODOS,offset=0,filters={'task_id':root_id},connection=db)
        if result['total'] > MAX_CONTEXT_TODOS:
            raise PlanningConflict('공유 할 일 계획 맥락 한도(100개)를 초과했습니다. 별도 계획으로 과제를 분리하세요.')
        items=[];seen=set()
        for item in result['items']:
            try:
                if not isinstance(item.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',item['id']):raise ValueError('invalid identity')
                row=record(store,item['id'],root_id,db)
                if row != item or row['id'] in seen:raise ValueError('duplicate or mismatched identity')
                seen.add(row['id'])
                parsed=TodoCreate.model_validate({'request_id':'0'*32,'title':row['title'],
                    'description':row['description'],'assignee_id':row.get('assignee_id'),
                    'check_ids':row.get('check_ids',[])}).model_dump()
                if row['status'] not in ('open','in_progress','done','cancelled'):raise ValueError('invalid status')
                note=row.get('resolution_note','')
                if not isinstance(note,str) or len(note)>2000 or (row['status'] in ('done','cancelled') and not note.strip()):raise ValueError('invalid reason')
                items.append({'id':row['id'],'revision':row['revision'],'status':row['status'],
                    'title':parsed['title'],'description':parsed['description'],
                    'check_ids':parsed['check_ids'],'resolution_note':note})
            except (KeyError,TypeError,ValueError,LookupError) as exc:
                raise PlanningConflict('공유 할 일의 저장 내용·ID·버전을 확인하세요.') from exc
        items.sort(key=lambda row:row['id'])
        context={'format':'aegis-todo-context-v1','root_task_id':root_id,'items':items}
        encoded=json.dumps(context,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        if len(encoded)>MAX_CONTEXT_BYTES:
            raise PlanningConflict('공유 할 일 계획 맥락 한도(64 KiB)를 초과했습니다. 내용을 정리하세요.')
        context['fingerprint']=hashlib.sha256(encoded).hexdigest()
        return context


def require_context(context):
    if not isinstance(context,dict) or set(context)!={'format','root_task_id','items','fingerprint'}:
        raise PlanningConflict('저장된 할 일 계획 맥락의 형식을 확인하세요.')
    if context['format']!='aegis-todo-context-v1' or not isinstance(context['root_task_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',context['root_task_id']):
        raise PlanningConflict('저장된 할 일 계획 맥락의 원본을 확인하세요.')
    items=context['items']
    if not isinstance(items,list) or len(items)>MAX_CONTEXT_TODOS:
        raise PlanningConflict('저장된 할 일 계획 맥락의 한도를 확인하세요.')
    seen=set()
    for row in items:
        if (not isinstance(row,dict) or set(row)!={'id','revision','status','title','description','check_ids','resolution_note'}
                or not isinstance(row['id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',row['id']) or row['id'] in seen
                or type(row['revision']) is not int or row['revision']<1
                or row['status'] not in ('open','in_progress','done','cancelled')
                or not isinstance(row['resolution_note'],str) or len(row['resolution_note'])>2000
                or (row['status'] in ('done','cancelled') and not row['resolution_note'].strip())):
            raise PlanningConflict('저장된 할 일 계획 맥락의 항목을 확인하세요.')
        seen.add(row['id'])
        try:TodoCreate.model_validate({'request_id':'0'*32,'title':row['title'],'description':row['description'],'check_ids':row['check_ids']})
        except ValueError as exc:raise PlanningConflict('저장된 할 일 계획 맥락의 도구·내용을 확인하세요.') from exc
    encoded=json.dumps({k:v for k,v in context.items() if k!='fingerprint'},ensure_ascii=False,
                       sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if len(encoded)>MAX_CONTEXT_BYTES or hashlib.sha256(encoded).hexdigest()!=context['fingerprint']:
        raise PlanningConflict('저장된 할 일 계획 맥락의 지문을 확인하세요.')
    return context


def requested_checks(context):
    require_context(context)
    requested={check for row in context['items'] if row['status'] in ('open','in_progress') for check in row['check_ids']}
    return [c['id'] for c in CATALOG if c['id'] in requested]
