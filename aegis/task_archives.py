"""Atomic terminal-task organization; source evidence and execution state are preserved."""
from typing import Annotated
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .remote_mcp import _digest
from .store_util import now

ID=Annotated[str,Field(min_length=1,max_length=80,pattern=r'^[A-Za-z0-9_-]+$')]
REQUEST_ID=Annotated[str,Field(min_length=16,max_length=80,pattern=r'^[A-Za-z0-9_-]+$')]
REVISION=Annotated[int,Field(strict=True,ge=0,le=9_007_199_254_740_991)]
TERMINAL={'completed','failed','stopped','interrupted','rejected'}

class ArchiveInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    task_ids:list[ID]=Field(min_length=1,max_length=25)
    expected_revisions:dict[ID,REVISION]
    archived:bool
    request_id:REQUEST_ID

    @model_validator(mode='after')
    def exact_tasks(self):
        if len(set(self.task_ids))!=len(self.task_ids) or set(self.task_ids)!=set(self.expected_revisions):
            raise ValueError('선택한 작업과 보관 버전을 정확히 확인하세요.')
        return self

class Archives:
    def __init__(self,store):self.store=store

    def change(self,data,actor):
        operation_id=_digest(['aegis-task-archive-v1',actor['id'],data.request_id])[:32]
        requested=_digest({'task_ids':sorted(data.task_ids),'expected_revisions':data.expected_revisions,'archived':data.archived})
        with self.store.lock,self.store.write_transaction() as db:
            fresh=self.store.user(id=actor['id'],connection=db)
            if not fresh or fresh['disabled'] or fresh['role'] not in ('admin','operator'):
                raise HTTPException(403,'운영자 또는 관리자 권한이 필요합니다.')
            actor={key:fresh[key] for key in ('id','name','username','role')}
            previous=self.store.get('task_archive_operations',operation_id,connection=db)
            if previous:
                if previous['request_sha256']!=requested:raise HTTPException(409,'같은 작업 보관 요청의 내용이 다릅니다.')
                return {**previous['result'],'replayed':True}
            tasks=[]
            for id in sorted(data.task_ids):
                task=self.store.get('tasks',id,connection=db)
                if task is None:raise HTTPException(404,'선택한 작업이 없습니다.')
                revision=task.get('archive_revision',0)
                if type(revision) is not int or revision!=data.expected_revisions[id]:raise HTTPException(409,'작업 보관 버전이 변경되었습니다.')
                if task['status'] not in TERMINAL:raise HTTPException(409,'종료된 작업만 보관·복원할 수 있습니다.')
                if bool(task.get('archived_at'))!=data.archived and revision>=9_007_199_254_740_991:raise HTTPException(409,'작업 보관 버전 한도에 도달했습니다.')
                tasks.append(task)
            timestamp=now();rows=[];assignments=[]
            for task in tasks:
                before=bool(task.get('archived_at'));revision=task.get('archive_revision',0)
                if before!=data.archived:
                    revision+=1
                    changed={**task,'archived_at':timestamp if data.archived else None,'archive_revision':revision}
                    history={'id':task['id']+':'+str(revision),'task_id':task['id'],'revision':revision,
                             'archived':data.archived,'before_archived_at':task.get('archived_at'),
                             'archived_at':changed['archived_at'],'actor':actor,'created_at':timestamp,'operation_id':operation_id}
                    rows.extend([('tasks',changed),('task_archive_history',history)])
                assignments.append({'task_id':task['id'],'archive_revision':revision,'archived':data.archived})
            result={'assignments':assignments,'execution_authorized':False,'replayed':False}
            rows.append(('task_archive_operations',{'id':operation_id,'request_sha256':requested,'result':result,'actor':actor,'created_at':timestamp}))
            self.store.put_many(rows,connection=db)
            self.store.event(None,'작업 보관 변경',detail={'operation_id':operation_id,'task_ids':sorted(data.task_ids),'archived':data.archived,'actor':actor},connection=db)
            return result
