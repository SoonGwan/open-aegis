"""Administrator-reviewed notification channels; secrets stay in fixed environment destinations."""
from typing import Annotated,Literal
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .remote_mcp import _digest
from .store_util import now
from .notification_transport import DispatchError

ID=Annotated[str,Field(min_length=1,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')]
REVISION=Annotated[int,Field(strict=True,ge=1,le=9_007_199_254_740_991)]
TaskStatus=Literal['completed','failed','stopped','interrupted','rejected']
KIND='notification_channels'

class ChannelInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    name:str=Field(min_length=1,max_length=100)
    destination_id:ID
    task_statuses:list[TaskStatus]=Field(default_factory=lambda:['failed','interrupted'],min_length=1,max_length=5)
    enabled:bool=False
    interval_seconds:int=Field(default=60,ge=1,le=3600)
    request_id:ID=Field(min_length=16)

    @model_validator(mode='after')
    def distinct(self):
        if len(set(self.task_statuses))!=len(self.task_statuses):raise ValueError('알림 상태는 중복 없이 선택하세요.')
        return self

class ChannelEdit(ChannelInput):
    expected_revision:REVISION

class Channels:
    def __init__(self,store,webhooks):self.store=store;self.webhooks=webhooks

    def actor(self,actor,db):
        user=self.store.user(id=actor['id'],connection=db)
        if not user or user['disabled'] or user['role']!='admin':raise HTTPException(403,'관리자 권한이 필요합니다.')
        return {key:user[key] for key in ('id','name','username','role')}

    def get(self,id,db=None):
        channel=self.store.get(KIND,id,connection=db)
        if not channel:raise HTTPException(404,'알림 채널이 없습니다.')
        return channel

    def public(self,record):
        keys=('id','name','destination_id','task_statuses','enabled','interval_seconds','revision','created_at','updated_at','activated_at')
        result={key:record[key] for key in keys}
        try:prepared=self.webhooks.prepare(record['destination_id']);configured=True;reviewed=prepared.fingerprint==record['destination_fingerprint']
        except DispatchError:configured=False;reviewed=False
        return {**result,'configured':configured,'destination_review_current':reviewed}

    def definition(self,data):
        name=data.name.strip()
        if not name:raise HTTPException(422,'알림 채널 이름을 입력하세요.')
        if data.destination_id not in self.webhooks.destinations:raise HTTPException(404,'설정된 알림 수신처가 없습니다.')
        try:prepared=self.webhooks.prepare(data.destination_id)
        except DispatchError:
            if data.enabled:raise HTTPException(409,'수신처 설정을 확인한 뒤 알림을 활성화하세요.') from None
            prepared=None
        return {'name':name,'name_key':name.casefold(),'destination_id':data.destination_id,'task_statuses':sorted(data.task_statuses),
                'enabled':data.enabled,'status':'active' if data.enabled else 'disabled','interval_seconds':data.interval_seconds,
                'destination_fingerprint':prepared.fingerprint if data.enabled else None}

    def save(self,record,actor,action,db):
        version={'id':record['id']+':'+str(record['revision']),'task_id':record['id'],'revision':record['revision'],
                 'snapshot':record,'actor':actor,'action':action,'created_at':now()}
        self.store.put_many([(KIND,record),('notification_channel_versions',version)],connection=db)
        self.store.event(None,'알림 채널 '+action,detail={'channel_id':record['id'],'revision':record['revision'],'enabled':record['enabled'],'actor':actor},connection=db)
        return record

    def unique(self,definition,id,db):
        pg=getattr(self.store,'backend',None)=='postgres';marker='%s' if pg else '?'
        name="data::jsonb->>'name_key'" if pg else "json_extract(data,'$.name_key')"
        if db.execute(f'SELECT 1 FROM records WHERE kind={marker} AND id!={marker} AND {name}={marker} LIMIT 1',(KIND,id,definition['name_key'])).fetchone():raise HTTPException(409,'같은 이름의 알림 채널이 있습니다.')

    def create(self,data,actor):
        id=_digest(['aegis-notification-channel-v1',actor['id'],data.request_id])[:32]
        requested=_digest(data.model_dump(exclude={'request_id'}))
        with self.store.lock,self.store.write_transaction() as db:
            actor=self.actor(actor,db);existing=self.store.get(KIND,id,connection=db)
            if existing:
                if existing['creation_sha256']!=requested:raise HTTPException(409,'같은 채널 저장 요청의 내용이 다릅니다.')
                return {'channel':self.public(existing),'replayed':True}
            definition=self.definition(data)
            marker='%s' if getattr(self.store,'backend',None)=='postgres' else '?'
            if db.execute(f'SELECT count(*) AS count FROM records WHERE kind={marker}',(KIND,)).fetchone()['count']>=25:raise HTTPException(409,'알림 채널은 최대25개입니다.')
            self.unique(definition,id,db);timestamp=now()
            record={**definition,'id':id,'revision':1,'created_at':timestamp,'updated_at':timestamp,'activated_at':timestamp if data.enabled else None,
                    'approved_by':actor if data.enabled else None,'source_after':self.store.event_progress(0,connection=db)['latest_event_seq'],'creation_sha256':requested}
            return {'channel':self.public(self.save(record,actor,'생성',db)),'replayed':False}

    def change(self,id,data,actor):
        operation_id=_digest(['aegis-notification-edit-v1',id,actor['id'],data.request_id])[:32]
        requested=_digest(data.model_dump(exclude={'request_id'}))
        with self.store.lock,self.store.write_transaction() as db:
            actor=self.actor(actor,db);before=self.get(id,db);operation=self.store.get('notification_channel_operations',operation_id,connection=db)
            if operation:
                if operation['request_sha256']!=requested:raise HTTPException(409,'같은 채널 수정 요청의 내용이 다릅니다.')
                return {'channel':self.public(operation['snapshot']),'replayed':True}
            if before['revision']!=data.expected_revision:raise HTTPException(409,'알림 채널 버전이 변경되었습니다.')
            if before['revision']>=9_007_199_254_740_991:raise HTTPException(409,'알림 채널 버전 한도에 도달했습니다.')
            definition=self.definition(data)
            self.unique(definition,id,db);timestamp=now()
            record={**before,**definition,'revision':before['revision']+1,'updated_at':timestamp,'activated_at':timestamp if data.enabled else None,'approved_by':actor if data.enabled else None,'source_after':self.store.event_progress(0,connection=db)['latest_event_seq']}
            self.save(record,actor,'수정',db)
            self.store.put_many([('notification_channel_operations',{'id':operation_id,'channel_id':id,'request_sha256':requested,'snapshot':record,'created_at':timestamp})],connection=db)
            return {'channel':self.public(record),'replayed':False}


class DeliveryRetry(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    expected_attempts:int=Field(ge=0,le=3)
    request_id:ID=Field(min_length=16)
    confirm_possible_duplicate:bool=False


class ChannelTest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    expected_revision:REVISION
    request_id:ID=Field(min_length=16)
