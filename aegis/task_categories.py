"""Versioned task organization; classification never grants execution authority."""
from typing import Annotated
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .remote_mcp import _digest
from .store_util import now

KIND='task_categories'
HISTORY='task_category_history'
MAX_REVISION=9_007_199_254_740_991
RecordID=Annotated[str,Field(min_length=1,max_length=80,pattern=r'^[A-Za-z0-9_-]+$')]
RequestID=Annotated[str,Field(strict=True,min_length=16,max_length=80,pattern=r'^[A-Za-z0-9_-]+$')]
Revision=Annotated[int,Field(strict=True,ge=0,le=MAX_REVISION)]


class CategoryInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=80)
    request_id:RequestID


class CategoryEdit(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=80)
    expected_revision:Revision


class CategoryArchive(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_revision:Revision
    archived:bool=Field(strict=True)


class CategoryAssignment(BaseModel):
    model_config=ConfigDict(extra='forbid')
    task_ids:list[RecordID]=Field(min_length=1,max_length=25)
    category_id:RecordID|None
    expected_revisions:dict[RecordID,Revision]=Field(min_length=1,max_length=25)
    request_id:RequestID

    @model_validator(mode='after')
    def exact_revisions(self):
        if len(set(self.task_ids))!=len(self.task_ids) or set(self.expected_revisions)!=set(self.task_ids):
            raise ValueError('작업마다 중복 없는 ID와 현재 분류 버전을 지정하세요.')
        return self


class Categories:
    def __init__(self,store):self.store=store

    def actor(self,actor,db):
        user=self.store.user(id=actor['id'],connection=db)
        if not user or user['disabled'] or user['role'] not in ('admin','operator'):
            raise HTTPException(403,'운영자 또는 관리자 권한이 필요합니다.')
        return {key:user[key] for key in ('id','name','username','role')}

    def get(self,id,db=None):
        record=self.store.get(KIND,id,connection=db)
        if not record:raise HTTPException(404,'작업 분류가 없습니다.')
        return record

    def name(self,value):
        value=value.strip()
        if not value:raise HTTPException(422,'작업 분류 이름을 입력하세요.')
        return value

    def unique(self,name,id,db):
        pg=getattr(self.store,'backend',None)=='postgres';marker='%s' if pg else '?'
        field=lambda key:f"data::jsonb->>'{key}'" if pg else f"json_extract(data,'$.{key}')"
        if db.execute(f"SELECT 1 FROM records WHERE kind={marker} AND id!={marker} AND {field('status')}='active' AND {field('name_key')}={marker} LIMIT 1",(KIND,id,name.casefold())).fetchone():
            raise HTTPException(409,'같은 이름의 활성 분류가 있습니다.')

    def save(self,record,actor,action,db):
        row={'id':record['id']+':'+str(record['revision']),'task_id':record['id'],'revision':record['revision'],
             'snapshot':record,'actor':actor,'action':action,'created_at':now()}
        self.store.put_many([(KIND,record),('task_category_versions',row)],connection=db)
        self.store.event(None,'작업 분류 '+action,detail={'category_id':record['id'],'revision':record['revision'],'actor':actor},connection=db)
        return record

    def create(self,data,actor):
        name=self.name(data.name);id=_digest(['aegis-task-category-v1',actor['id'],data.request_id])[:32]
        requested=_digest({'name':name})
        with self.store.lock,self.store.write_transaction() as db:
            actor=self.actor(actor,db);existing=self.store.get(KIND,id,connection=db)
            if existing:
                if existing['creation_sha256']!=requested:raise HTTPException(409,'같은 분류 저장 요청 ID의 내용이 다릅니다.')
                return {'category':existing,'replayed':True,'created_revision':1}
            marker='%s' if getattr(self.store,'backend',None)=='postgres' else '?'
            if db.execute(f'SELECT count(*) AS count FROM records WHERE kind={marker}',(KIND,)).fetchone()['count']>=1000:
                raise HTTPException(409,'작업 분류 한도(1,000개)에 도달했습니다.')
            self.unique(name,id,db)
            record={'id':id,'name':name,'name_key':name.casefold(),'status':'active','revision':1,
                    'created_at':now(),'updated_at':now(),'created_by':actor,'creation_sha256':requested}
            return {'category':self.save(record,actor,'생성',db),'replayed':False,'created_revision':1}

    def change(self,id,data,actor):
        with self.store.lock,self.store.write_transaction() as db:
            actor=self.actor(actor,db);before=self.get(id,db)
            if before['revision']!=data.expected_revision:raise HTTPException(409,'작업 분류 버전이 변경되었습니다.')
            if isinstance(data,CategoryEdit):
                name=self.name(data.name)
                if before['status']=='active':self.unique(name,id,db)
                change={'name':name,'name_key':name.casefold()};action='수정'
            else:
                status='archived' if data.archived else 'active'
                if status==before['status']:return before
                if status=='active':self.unique(before['name'],id,db)
                change={'status':status};action='보관' if data.archived else '복원'
            if before['revision']>=MAX_REVISION:raise HTTPException(409,'작업 분류 버전 한도에 도달했습니다.')
            return self.save({**before,**change,'revision':before['revision']+1,'updated_at':now()},actor,action,db)

    def assign(self,data,actor):
        ids=sorted(data.task_ids)
        requested=_digest({'task_ids':ids,'category_id':data.category_id,'expected_revisions':data.expected_revisions})
        operation_id=_digest(['aegis-task-category-assignment-v1',actor['id'],data.request_id])[:32]
        with self.store.lock,self.store.write_transaction() as db:
            actor=self.actor(actor,db)
            existing=self.store.get('task_category_operations',operation_id,connection=db)
            if existing:
                if existing['request_sha256']!=requested:raise HTTPException(409,'같은 분류 변경 요청 ID의 내용이 다릅니다.')
                return {**existing['result'],'replayed':True}
            category=self.get(data.category_id,db) if data.category_id else None
            if category and category['status']!='active':raise HTTPException(409,'보관된 분류를 새로 지정할 수 없습니다.')
            ref={key:category[key] for key in ('id','name','revision')} if category else None
            records=[];results=[]
            for id in ids:
                task=self.store.get('tasks',id,connection=db)
                if not task:raise HTTPException(404,'분류를 변경할 작업이 없습니다.')
                revision=task.get('category_revision',0)
                if type(revision) is not int or revision!=data.expected_revisions[id]:raise HTTPException(409,'작업의 분류가 변경되었습니다. 선택한 작업을 다시 확인하세요.')
                if revision>=MAX_REVISION:raise HTTPException(409,'작업 분류 변경 버전 한도에 도달했습니다.')
                after={**task,'category_ref':ref,'category_revision':revision+1}
                after.pop('category_origin_task_id',None)
                entry={'id':operation_id+':'+id,'task_id':id,'operation_id':operation_id,'action':'분류 변경',
                       'revision':revision+1,'before':task.get('category_ref'),'before_origin_task_id':task.get('category_origin_task_id'),
                       'after':ref,'actor':actor,'created_at':now()}
                records.extend([('tasks',after),(HISTORY,entry)])
                results.append({'task_id':id,'category_revision':revision+1,'category_ref':ref})
            result={'operation_id':operation_id,'assignments':results,'replayed':False,'execution_authorized':False}
            records.append(('task_category_operations',{'id':operation_id,'request_sha256':requested,'result':result,'actor':actor,'created_at':now()}))
            self.store.put_many(records,connection=db)
            for id in ids:self.store.event(id,'작업 분류를 변경했습니다.',detail={'operation_id':operation_id,'category_ref':ref,'actor':actor,'execution_authorized':False},connection=db)
            return result
