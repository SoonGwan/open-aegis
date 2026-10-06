"""Explicit, bounded provider catalog reads over reviewed fixed model profiles."""
import hashlib,threading,time
from contextlib import nullcontext
from urllib.parse import urlsplit
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict
from .model_profiles import Revision,RequestID,ProfileUnavailable
from .remote_mcp import _decode,_digest
from .network import PinnedHTTP,PinnedHTTPS,resolve
from .runtime import TaskControl,RequestGuard
from .store_util import now

KIND='model_catalog_queries'
MAX_BYTES=1024*1024
MAX_MODELS=256

class CatalogInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    expected_revision:Revision
    request_id:RequestID

class CatalogError(ValueError):
    def __init__(self,code,http_status=None):self.code=code;self.http_status=http_status

class Catalog:
    def __init__(self,store,profiles,shutdown):
        self.store=store;self.profiles=profiles;self.stop=shutdown;self.gate=threading.Lock()

    def close(self):
        self.stop.set()
        with self.gate:pass

    def recover(self):
        with self.store.lock,self.store.write_transaction() as db:
            page=self.store.page(KIND,limit=25,filters={'status':'started'},connection=db)
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
        record=self.store.get(KIND,id,connection=db)
        if record and record['request_sha256']!=requested:raise HTTPException(409,'같은 모델 목록 요청 ID의 내용이 다릅니다.')
        return record

    def finish(self,before,status,code,models,digest,http_status,db):
        record={**before,'status':status,'result_code':code,'models':models,'model_count':len(models),
                'response_sha256':digest,'http_status':http_status,'finished_at':now()}
        self.store.put_many([(KIND,record)],connection=db)
        self.store.event(None,'제공자 모델 목록 조회 상태',detail={'query_id':record['id'],'profile_id':record['profile_id'],
                         'profile_revision':record['profile_revision'],'status':status,'result_code':code,'actor':record['actor']},connection=db)
        return record

    def read(self,id,data,actor):
        query_id=_digest(['aegis-model-catalog-v1',id,actor['id'],data.request_id])[:32]
        requested=_digest(data.model_dump(exclude={'request_id'}))
        with self.store.read_transaction() as db:
            previous=self.lookup(query_id,requested,actor,db)
            if previous:return {'query':previous,'replayed':True}
        if not self.gate.acquire(blocking=False):raise HTTPException(429,'다른 모델 목록 조회가 진행 중입니다. 같은 요청으로 다시 확인하세요.')
        try:
            if self.stop.is_set():raise HTTPException(503,'서버가 종료 중입니다.')
            with self.store.lock,self.store.write_transaction() as db:
                previous=self.lookup(query_id,requested,actor,db)
                if previous:return {'query':previous,'replayed':True}
                profile,prepared,actor=self.profile(id,data.expected_revision,actor,db)
                if self.store.page(KIND,limit=1,filters={'task_id':id},connection=db)['total']>=200:
                    raise HTTPException(409,'프로필별 모델 목록 조회 기록은 최대200개입니다.')
                record={'id':query_id,'profile_id':id,'task_id':id,'profile_revision':profile['revision'],
                        'profile_snapshot':{key:profile[key] for key in ('id','name','model','revision','destination_id')},
                        'profile_fingerprint':profile['fingerprint'],'destination_id':profile['destination_id'],
                        'destination_fingerprint':prepared[3],'request_sha256':requested,'actor':actor,'status':'started',
                        'created_at':now(),'models':[],'model_count':0,'result_code':'awaiting_response'}
                self.store.put_many([(KIND,record)],connection=db)
                self.store.event(None,'제공자 모델 목록 조회 시작',detail={'query_id':query_id,'profile_id':id,'profile_revision':profile['revision'],'actor':actor},connection=db)
            control=TaskControl(self.stop,time.monotonic()+8)
            status,code,models,digest,http_status='failed','connection_failed',[],None,None
            try:
                with getattr(self.store,'execution_permit',nullcontext)():
                    models,digest=self.fetch(record,prepared,control)
                status,code,http_status='completed','catalog_response_valid',200
            except CatalogError as error:code,http_status=error.code,error.http_status
            except (HTTPException,ProfileUnavailable):status,code='blocked','profile_review_changed'
            except InterruptedError:status,code='unknown','request_stopped'
            except (OSError,ValueError):pass
            with self.store.lock,self.store.write_transaction() as db:
                current=self.store.get(KIND,query_id,connection=db)
                if not current or current['status']!='started':raise RuntimeError('Catalog receipt changed before completion')
                return {'query':self.finish(current,status,code,models,digest,http_status,db),'replayed':False}
        finally:self.gate.release()

    def fetch(self,record,prepared,control):
        base,key,local,_=prepared;parsed=urlsplit(base)
        port=parsed.port or (443 if parsed.scheme=='https' else 80)
        address=resolve(parsed.hostname,port,allow_private=local,control=control,timeout=control.timeout(4))[0]
        connection=(PinnedHTTPS if parsed.scheme=='https' else PinnedHTTP)(parsed.hostname,port,address,timeout=control.timeout(8))
        try:
            with self.store.read_transaction() as db:
                profile,current,_=self.profile(record['profile_id'],record['profile_revision'],record['actor'],db)
                if current!=prepared or profile['fingerprint']!=record['profile_fingerprint']:raise ProfileUnavailable('Model profile changed')
            with RequestGuard(connection,control,8) as guard:
                connection.request('GET',parsed.path.rstrip('/')+'/models',headers={'Authorization':'Bearer '+key,'Accept':'application/json','Accept-Encoding':'identity'})
                guard.sock=connection.sock;response=connection.getresponse()
                if response.status!=200:raise CatalogError('provider_status',response.status)
                if response.getheader('Content-Encoding','identity').lower()!='identity':raise CatalogError('response_encoding',200)
                if response.getheader('Content-Type','').split(';')[0].strip().lower()!='application/json':raise CatalogError('response_content_type',200)
                if response.length is not None and response.length>MAX_BYTES:raise CatalogError('response_byte_budget',200)
                raw=response.read(MAX_BYTES+1)
                if len(raw)>MAX_BYTES:raise CatalogError('response_byte_budget',200)
            control.check()
            try:
                body=_decode(raw);rows=body['data']
                if not isinstance(rows,list) or len(rows)>MAX_MODELS:raise ValueError()
                models=[];seen=set()
                for row in rows:
                    name=row['id']
                    if (not isinstance(name,str) or not name or len(name)>160 or
                            any(ord(c)<=32 or ord(c)>126 for c in name) or key in name or base in name or name in seen):raise ValueError()
                    models.append(name);seen.add(name)
                return models,hashlib.sha256(raw).hexdigest()
            except (ValueError,TypeError,KeyError,AttributeError):raise CatalogError('response_shape',200) from None
        finally:connection.close()
