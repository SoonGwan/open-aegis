"""Atomic administrator task creation with reviewed initial model selections."""
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from .model_profiles import ID,ProfileUnavailable
from .remote_mcp import _digest
from .store_util import now

KIND='task_model_creation_operations'

class InitialModel(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    profile_id:ID
    expected_profile_revision:int=Field(strict=True,ge=1,le=9_007_199_254_740_991)

class TaskModelCreation:
    def __init__(self,store,profiles,selections):
        self.store=store;self.profiles=profiles;self.selections=selections

    def prepare(self,data,actor):
        requested=_digest(data.model_dump(exclude={'request_id'}))
        operation_id=_digest(['aegis-task-model-creation-v1',actor['id'],data.request_id])[:32]
        with self.store.read_transaction() as db:
            actor=self.profiles.actor(actor,db)
            previous=self.store.get(KIND,operation_id,connection=db)
            if previous:
                if previous['request_sha256']!=requested:
                    raise HTTPException(409,'같은 작업 생성 요청 ID의 내용이 다릅니다.')
                task=self.store.get('tasks',operation_id,connection=db)
                if not task or task.get('model_creation')!={'operation_id':operation_id,'request_sha256':requested}:
                    raise HTTPException(409,'원래 생성 작업의 저장된 참조를 확인하세요.')
                return None,{'task':task,'creation':previous,'replayed':True,'execution_authorized':False}
            if self.store.get('tasks',operation_id,connection=db):
                raise HTTPException(409,'작업 생성 참조가 이미 존재합니다. 저장된 기록을 확인하세요.')
        return {'id':operation_id,'request_sha256':requested,'actor':actor,
                'models':{purpose:selection.model_dump() for purpose,selection in data.models.items()}},None

    def commit(self,request,task,records,assets,db):
        actor=self.profiles.actor(request['actor'],db)
        if (task['id']!=request['id'] or self.store.get('tasks',task['id'],connection=db)
                or self.store.get(KIND,request['id'],connection=db)):
            raise HTTPException(409,'작업 생성 참조가 변경되었습니다.')
        if any(self.store.get('assets',asset['id'],connection=db)!=asset for asset in assets):
            raise HTTPException(409,'검토한 자산이 변경되었습니다. 생성 입력을 다시 검토하세요.')
        snapshots={}
        for purpose,selected in sorted(request['models'].items()):
            profile=self.profiles.get(selected['profile_id'],db)
            if profile['revision']!=selected['expected_profile_revision']:
                raise HTTPException(409,'생성 시 선택한 모델 프로필 버전이 변경되었습니다.')
            try:self.profiles._profile(profile,db)
            except ProfileUnavailable as error:raise HTTPException(409,str(error)) from None
            record,versions=self.selections.version_records(task['id'],purpose,1,profile,actor)
            snapshots[purpose]=record;records.extend(versions)
        task['model_creation']={'operation_id':request['id'],'request_sha256':request['request_sha256']}
        receipt={'id':request['id'],'task_id':task['id'],'request_sha256':request['request_sha256'],
                 'actor':actor,'selections':snapshots,'created_at':now()}
        self.store.put_many(records+[(KIND,receipt)],connection=db)
        self.store.event(task['id'],'검토한 모델 선택과 작업 생성. 별도 실행 승인을 기다립니다.',
                         detail={'operation_id':receipt['id'],'selections':snapshots,'actor':actor},connection=db)
        return {'task':task,'creation':receipt,'replayed':False,'execution_authorized':False}
