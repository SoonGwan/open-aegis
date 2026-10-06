"""Durable explicitly requested provider checks over reviewed fixed profiles."""
import threading,time
from contextlib import nullcontext
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict
from .model_profiles import Revision,RequestID,ProfileUnavailable
from .remote_mcp import _digest
from .runtime import TaskControl
from .store_util import now


class CheckInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    expected_revision:Revision
    request_id:RequestID

class CheckError(ValueError):
    def __init__(self,code,http_status=None):self.code=code;self.http_status=http_status

class CheckControl(TaskControl):
    def __init__(self,stop,shutdown,deadline):
        super().__init__(stop,deadline);self.shutdown=shutdown

    def check(self):
        if self.shutdown.is_set():raise InterruptedError('서버가 종료 중입니다.')
        super().check()

class ProviderCheck:
    kind=''; identity=''; label=''; success_code=''

    def initial(self):raise NotImplementedError()
    def result(self,value,record):raise NotImplementedError()
    def context(self,prepared,record):return {}

    def __init__(self,store,profiles,shutdown):
        self.store=store;self.profiles=profiles;self.shutdown=shutdown
        self.stop=threading.Event();self.gate=threading.Lock()

    def start(self):
        with self.gate:
            self.stop.clear()
            while self.recover():pass

    def close(self):
        self.stop.set()
        with self.gate:pass

    def recover(self):
        with self.store.lock,self.store.write_transaction() as db:
            page=self.store.page(self.kind,limit=25,filters={'status':'started'},connection=db)
            for record in page['items']:self.finish(record,'unknown','process_receipt_unconfirmed',[],None,None,db)
            return bool(page['items'])

    def profile(self,id,revision,actor,db):
        actor=self.profiles.actor(actor,db);record=self.profiles.get(id,db)
        if record['revision']!=revision:raise HTTPException(409,'모델 프로필이 변경되었습니다. 최신 버전을 검토하세요.')
        try:prepared=self.profiles._profile(record,db)
        except ProfileUnavailable as error:raise HTTPException(409,str(error)) from None
        return record,prepared,actor

    def lookup(self,id,requested,actor,db):
        self.profiles.actor(actor,db)
        record=self.store.get(self.kind,id,connection=db)
        if record and record['request_sha256']!=requested:raise HTTPException(409,'같은 제공자 확인 요청 ID의 내용이 다릅니다.')
        return record

    def finish(self,before,status,code,models,digest,http_status,db):
        record={**before,'status':status,'result_code':code,**self.result(models,before),
                'response_sha256':digest,'http_status':http_status,'finished_at':now()}
        self.store.put_many([(self.kind,record)],connection=db)
        self.store.event(None,self.label+' 상태',detail={'query_id':record['id'],'profile_id':record['profile_id'],
                         'profile_revision':record['profile_revision'],'status':status,'result_code':code,'actor':record['actor']},connection=db)
        return record

    def read(self,id,data,actor):
        query_id=_digest([self.identity,id,actor['id'],data.request_id])[:32]
        requested=_digest(data.model_dump(exclude={'request_id'}))
        with self.store.read_transaction() as db:
            previous=self.lookup(query_id,requested,actor,db)
            if previous:return {'query':previous,'replayed':True}
        if not self.gate.acquire(blocking=False):raise HTTPException(429,'다른 제공자 확인 요청이 진행 중입니다. 같은 요청으로 다시 확인하세요.')
        try:
            if self.stop.is_set() or self.shutdown.is_set():raise HTTPException(503,'서버가 종료 중입니다.')
            with self.store.lock,self.store.write_transaction() as db:
                previous=self.lookup(query_id,requested,actor,db)
                if previous:return {'query':previous,'replayed':True}
                profile,prepared,actor=self.profile(id,data.expected_revision,actor,db)
                if self.store.page(self.kind,limit=1,filters={'task_id':id},connection=db)['total']>=200:
                    raise HTTPException(409,'프로필별 확인 기록은 최대200개입니다.')
                record={'id':query_id,'profile_id':id,'task_id':id,'profile_revision':profile['revision'],
                        'profile_snapshot':{key:profile[key] for key in ('id','name','model','revision','destination_id')},
                        'profile_fingerprint':profile['fingerprint'],'destination_id':profile['destination_id'],
                        'destination_fingerprint':prepared[3],'request_sha256':requested,'actor':actor,'status':'started',
                        'created_at':now(),**self.initial(),'result_code':'awaiting_response'}
                record.update(self.context(prepared,record))
                self.store.put_many([(self.kind,record)],connection=db)
                self.store.event(None,self.label+' 시작',detail={'query_id':query_id,'profile_id':id,'profile_revision':profile['revision'],'actor':actor},connection=db)
            control=CheckControl(self.stop,self.shutdown,time.monotonic()+8)
            status,code,models,digest,http_status='failed','connection_failed',[],None,None
            try:
                with getattr(self.store,'execution_permit',nullcontext)():
                    models,digest=self.fetch(record,prepared,control)
                status,code,http_status='completed',self.success_code,200
            except CheckError as error:code,http_status=error.code,error.http_status
            except (HTTPException,ProfileUnavailable):status,code='blocked','profile_review_changed'
            except InterruptedError:status,code='unknown','request_stopped'
            except (OSError,ValueError):pass
            with self.store.lock,self.store.write_transaction() as db:
                current=self.store.get(self.kind,query_id,connection=db)
                if not current or current['status']!='started':raise RuntimeError('Provider check receipt changed before completion')
                return {'query':self.finish(current,status,code,models,digest,http_status,db),'replayed':False}
        finally:self.gate.release()

