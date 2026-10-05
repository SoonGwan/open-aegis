"""Administrator-reviewed model profiles over fixed environment destinations."""
import os
from dataclasses import dataclass
from typing import Annotated, Literal
from urllib.parse import urlsplit
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .remote_mcp import _decode, _digest
from .store_util import now

ID=Annotated[str,Field(strict=True,min_length=1,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')]
RequestID=Annotated[str,Field(strict=True,min_length=16,max_length=80,pattern=r'^[A-Za-z0-9_-]+$')]
Revision=Annotated[int,Field(strict=True,ge=0,le=9_007_199_254_740_991)]
Purpose=Literal['planner','conversation']
KIND='model_profiles';HISTORY='model_profile_versions';DEFAULTS='model_defaults'

class Destination(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    id:ID
    name:str=Field(min_length=1,max_length=100)
    base_env:str=Field(pattern=r'^[A-Z][A-Z0-9_]{0,99}$')
    key_env:str=Field(pattern=r'^[A-Z][A-Z0-9_]{0,99}$')
    lab_http:bool=False

class ProfileInput(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    name:str=Field(min_length=1,max_length=100)
    model:str=Field(min_length=1,max_length=160)
    destination_id:ID
    enabled:bool=False
    request_id:RequestID

class ProfileEdit(ProfileInput):
    expected_revision:Revision

class DefaultEdit(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    expected_revision:Revision
    profile_id:ID|None
    expected_profile_revision:Revision|None=None
    request_id:RequestID

@dataclass(frozen=True)
class Choice:
    base:str
    key:str
    model:str
    local:bool
    reference:dict

class ProfileUnavailable(ValueError):pass

class Destinations:
    def __init__(self):
        try:
            raw=os.environ.get('AEGIS_MODEL_DESTINATIONS','[]').encode()
            if len(raw)>32768:raise ValueError()
            definitions=_decode(raw)
            if not isinstance(definitions,list) or len(definitions)>10:raise ValueError()
            self.items={'environment-default':Destination(id='environment-default',name='기본 환경 설정',base_env='AEGIS_LLM_BASE_URL',key_env='AEGIS_LLM_API_KEY')}
            for definition in definitions:
                item=Destination(**definition)
                if item.id in self.items:raise ValueError()
                self.items[item.id]=item
        except (ValueError,TypeError,UnicodeError):
            raise RuntimeError('모델 수신처 설정을 확인하세요. 추가 고정 수신처는 최대10개입니다.') from None

    def prepare(self,id,model,allow_local=False):
        item=self.items.get(id)
        if item is None:raise ProfileUnavailable('설정된 모델 수신처가 없습니다.')
        base=os.environ.get(item.base_env,'https://api.openai.com/v1' if id=='environment-default' else '').rstrip('/')
        key=os.environ.get(item.key_env,'')
        if not base or not key:raise ProfileUnavailable('모델 수신처 인증 설정을 확인하세요.')
        if (len(base)>2000 or any(ord(c)<=32 or ord(c)>126 for c in base) or len(key)>4096
                or any(ord(c)<32 or ord(c)>126 for c in key) or not model.strip()
                or len(model)>160 or any(ord(c)<32 or ord(c)>126 for c in model)):
            raise ProfileUnavailable('모델 수신처 주소·인증·모델 이름의 형식을 확인하세요.')
        try:
            parsed=urlsplit(base);port=parsed.port
            local=(item.lab_http and parsed.hostname in ('127.0.0.1','::1') or
                   id=='environment-default' and allow_local and parsed.hostname in ('localhost','127.0.0.1','::1'))
            if (port is not None and not 1<=port<=65535 or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
                    or parsed.scheme!='https' and not(local and parsed.scheme=='http')):raise ValueError()
        except ValueError:raise ProfileUnavailable('모델 수신처 주소의 형식을 확인하세요.') from None
        fingerprint=_digest({'id':id,'base':base,'key':key,'local':bool(local)})
        return base,key,bool(local),fingerprint

    def public(self,allow_local=False):
        result=[]
        for item in self.items.values():
            try:self.prepare(item.id,'configuration-review',allow_local);available=True
            except ProfileUnavailable:available=False
            result.append({'id':item.id,'name':item.name,'configuration_available':available})
        return result

class Profiles:
    def __init__(self,store,allow_local=False):
        self.store=store;self.allow_local=allow_local;self.destinations=Destinations()

    def actor(self,actor,db):
        fresh=self.store.user(id=actor['id'],connection=db)
        if not fresh or fresh['disabled'] or fresh['role']!='admin':raise HTTPException(403,'관리자 권한이 필요합니다.')
        return {key:fresh[key] for key in ('id','name','username','role')}

    def get(self,id,db=None):
        record=self.store.get(KIND,id,connection=db)
        if not record:raise HTTPException(404,'모델 프로필이 없습니다.')
        return record

    def public(self,record):
        try:
            prepared=self.destinations.prepare(record['destination_id'],record['model'],self.allow_local)
            available=True;current=prepared[3]==record['destination_fingerprint']
        except ProfileUnavailable:available=current=False
        actor=record.get('approved_by')
        fresh=self.store.user(id=actor['id']) if isinstance(actor,dict) and isinstance(actor.get('id'),str) else None
        approved=bool(fresh and not fresh['disabled'] and fresh['role']=='admin')
        return {**record,'configuration_available':available,'destination_review_current':current,'admin_review_current':approved}

    def fingerprint(self,record):
        return _digest({key:record.get(key) for key in ('id','name','model','destination_id','enabled','revision','destination_fingerprint','approved_by')})

    def definition(self,data,actor):
        name=data.name.strip();model=data.model.strip()
        if not name or not model:raise HTTPException(422,'프로필 이름과 모델 이름을 입력하세요.')
        if any(ord(c)<32 or ord(c)==127 for c in data.name):raise HTTPException(422,'프로필 이름에 제어 문자를 사용할 수 없습니다.')
        if data.destination_id not in self.destinations.items:raise HTTPException(404,'설정된 모델 수신처가 없습니다.')
        if any(ord(c)<32 or ord(c)>126 for c in data.model):raise HTTPException(422,'모델 이름의 형식을 확인하세요.')
        try:prepared=self.destinations.prepare(data.destination_id,model,self.allow_local)
        except ProfileUnavailable as error:
            if data.enabled:raise HTTPException(409,str(error)) from None
            prepared=None
        return {'name':name,'name_key':name.casefold(),'model':model,'destination_id':data.destination_id,
                'enabled':data.enabled,'status':'active' if data.enabled else 'disabled',
                'destination_fingerprint':prepared[3] if data.enabled and prepared else None,'approved_by':actor if data.enabled else None}

    def unique(self,name,id,db):
        pg=getattr(self.store,'backend',None)=='postgres';marker='%s' if pg else '?'
        expr="data::jsonb->>'name_key'" if pg else "json_extract(data,'$.name_key')"
        if db.execute(f'SELECT 1 FROM records WHERE kind={marker} AND id!={marker} AND {expr}={marker} LIMIT 1',(KIND,id,name.casefold())).fetchone():
            raise HTTPException(409,'같은 이름의 모델 프로필이 있습니다.')

    def save(self,record,actor,operation_id,requested,db):
        record['fingerprint']=self.fingerprint(record)
        version={'id':record['id']+':'+str(record['revision']),'task_id':record['id'],'revision':record['revision'],
                 'snapshot':record,'actor':actor,'created_at':record['updated_at']}
        operation={'id':operation_id,'request_sha256':requested,'snapshot':record,'created_at':record['updated_at']}
        self.store.put_many([(KIND,record),(HISTORY,version),('model_profile_operations',operation)],connection=db)
        self.store.event(None,'모델 프로필 버전 저장',detail={'profile_id':record['id'],'revision':record['revision'],'fingerprint':record['fingerprint'],'actor':actor},connection=db)
        return {'profile':self.public(record),'replayed':False}

    def change(self,id,data,actor):
        creation=id is None
        if creation:id=_digest(['aegis-model-profile-v1',actor['id'],data.request_id])[:32]
        operation_id=_digest(['aegis-model-profile-save-v1',id,actor['id'],data.request_id])[:32]
        requested=_digest(data.model_dump(exclude={'request_id'}))
        with self.store.lock,self.store.write_transaction() as db:
            actor=self.actor(actor,db);operation=self.store.get('model_profile_operations',operation_id,connection=db)
            if operation:
                if operation['request_sha256']!=requested:raise HTTPException(409,'같은 프로필 저장 요청 ID의 내용이 다릅니다.')
                return {'profile':self.public(operation['snapshot']),'replayed':True}
            before=None if creation else self.get(id,db)
            if before and before['revision']!=data.expected_revision:raise HTTPException(409,'모델 프로필이 변경되었습니다. 최신 버전과 초안을 비교하세요.')
            if creation and self.store.page(KIND,limit=1,connection=db)['total']>=25:raise HTTPException(409,'모델 프로필은 최대25개입니다.')
            revision=1 if creation else before['revision']+1
            if revision>200:raise HTTPException(409,'모델 프로필은 최대200개 버전을 보존합니다.')
            definition=self.definition(data,actor);self.unique(definition['name'],id,db);timestamp=now()
            record={**definition,'id':id,'revision':revision,'created_at':before['created_at'] if before else timestamp,'updated_at':timestamp}
            return self.save(record,actor,operation_id,requested,db)

    def default(self,purpose,db=None):
        return self.store.get(DEFAULTS,purpose,connection=db) or {'id':purpose,'purpose':purpose,'revision':0,'profile_id':None,'profile_revision':None,'profile_fingerprint':None}

    def choose(self,purpose,data,actor):
        if (data.profile_id is None)!=(data.expected_profile_revision is None):raise HTTPException(422,'프로필과 현재 버전을 함께 지정하세요.')
        operation_id=_digest(['aegis-model-default-v1',purpose,actor['id'],data.request_id])[:32]
        requested=_digest(data.model_dump(exclude={'request_id'}))
        with self.store.lock,self.store.write_transaction() as db:
            actor=self.actor(actor,db);operation=self.store.get('model_default_operations',operation_id,connection=db)
            if operation:
                if operation['request_sha256']!=requested:raise HTTPException(409,'같은 모델 선택 요청 ID의 내용이 다릅니다.')
                return {'selection':operation['snapshot'],'replayed':True}
            before=self.default(purpose,db)
            if type(before.get('revision')) is not int or before['revision']!=data.expected_revision:raise HTTPException(409,'모델 선택이 변경되었습니다. 현재 설정을 검토하세요.')
            if before['revision']>=200:raise HTTPException(409,'모델 선택은 용도별 최대200개 버전을 보존합니다.')
            profile=self.get(data.profile_id,db) if data.profile_id else None
            if profile:
                if profile['revision']!=data.expected_profile_revision:raise HTTPException(409,'프로필 버전이 변경되었습니다.')
                try:self._profile(profile,db)
                except ProfileUnavailable as error:raise HTTPException(409,str(error)) from None
            record={'id':purpose,'purpose':purpose,'revision':before['revision']+1,'profile_id':profile['id'] if profile else None,
                    'profile_revision':profile['revision'] if profile else None,'profile_fingerprint':profile['fingerprint'] if profile else None,'actor':actor,'updated_at':now()}
            record['fingerprint']=self.selection_fingerprint(record)
            version={'id':purpose+':'+str(record['revision']),'task_id':purpose,'snapshot':record,'created_at':record['updated_at'],'actor':actor,'revision':record['revision']}
            operation={'id':operation_id,'snapshot':record,'request_sha256':requested}
            self.store.put_many([(DEFAULTS,record),('model_default_versions',version),('model_default_operations',operation)],connection=db)
            self.store.event(None,'용도별 모델 선택 저장',detail={'purpose':purpose,'revision':record['revision'],'profile_id':record['profile_id'],'actor':actor},connection=db)
            return {'selection':record,'replayed':False}

    def selection_fingerprint(self,record):
        return _digest({key:record.get(key) for key in ('id','purpose','revision','profile_id','profile_revision','profile_fingerprint','actor')})

    def _profile(self,record,db):
        if (type(record.get('enabled')) is not bool or type(record.get('revision')) is not int or
                not 1<=record['revision']<=200 or not all(isinstance(record.get(key),str) for key in ('id','name','model','destination_id','fingerprint'))):
            raise ProfileUnavailable('모델 프로필의 형식을 확인하세요.')
        if not record['enabled'] or record.get('fingerprint')!=self.fingerprint(record):raise ProfileUnavailable('활성 모델 프로필의 버전을 확인하세요.')
        actor=record.get('approved_by');fresh=self.store.user(id=actor['id'],connection=db) if isinstance(actor,dict) and isinstance(actor.get('id'),str) else None
        if not fresh or fresh['disabled'] or fresh['role']!='admin':raise ProfileUnavailable('모델 프로필의 관리자 검토를 다시 확인하세요.')
        prepared=self.destinations.prepare(record['destination_id'],record['model'],self.allow_local)
        if prepared[3]!=record['destination_fingerprint']:raise ProfileUnavailable('수신처 인증 설정이 바뀌었습니다. 프로필과 모델 선택을 다시 검토하세요.')
        return prepared

    def capture(self,purpose):
        with self.store.read_transaction() as db:
            stored=self.store.get(DEFAULTS,purpose,connection=db)
            selection=stored or self.default(purpose,db)
            if (selection.get('id')!=purpose or selection.get('purpose')!=purpose or type(selection.get('revision')) is not int
                    or not 0<=selection['revision']<=200):raise ProfileUnavailable('모델 선택의 버전을 확인하세요.')
            if stored is not None and selection['revision']==0:raise ProfileUnavailable('저장된 모델 선택의 버전을 확인하세요.')
            profile_id=selection.get('profile_id')
            if profile_id is None:
                if selection.get('profile_revision') is not None or selection.get('profile_fingerprint') is not None:raise ProfileUnavailable('모델 선택의 프로필 참조를 확인하세요.')
            elif not isinstance(profile_id,str) or type(selection.get('profile_revision')) is not int or not isinstance(selection.get('profile_fingerprint'),str):
                raise ProfileUnavailable('모델 선택의 프로필 참조를 확인하세요.')
            if selection['revision']>0:
                if selection.get('fingerprint')!=self.selection_fingerprint(selection):raise ProfileUnavailable('모델 선택의 지문을 확인하세요.')
                actor=selection.get('actor')
                fresh=self.store.user(id=actor['id'],connection=db) if isinstance(actor,dict) and isinstance(actor.get('id'),str) else None
                if not fresh or fresh['disabled'] or fresh['role']!='admin':raise ProfileUnavailable('용도별 모델 선택의 관리자 검토를 다시 확인하세요.')
            if selection['profile_id']:
                record=self.store.get(KIND,selection['profile_id'],connection=db)
                if not record:raise ProfileUnavailable('선택된 모델 프로필이 없습니다.')
                if record.get('revision')!=selection['profile_revision'] or record.get('fingerprint')!=selection['profile_fingerprint']:
                    raise ProfileUnavailable('모델 프로필이 바뀌었습니다. 용도별 모델 선택을 다시 검토하세요.')
                base,key,local,binding=self._profile(record,db);model=record['model']
                reference={'kind':'profile','profile_id':record['id'],'profile_revision':record['revision'],'profile_fingerprint':record['fingerprint'],'destination_id':record['destination_id'],'model':model}
            else:
                model=os.environ.get('AEGIS_LLM_MODEL','')
                if not model or not os.environ.get('AEGIS_LLM_API_KEY'):return None
                base,key,local,binding=self.destinations.prepare('environment-default',model,self.allow_local)
                reference={'kind':'environment','destination_id':'environment-default','model':model}
            reference.update(purpose=purpose,selection_revision=selection['revision'],selection_fingerprint=self.selection_fingerprint(selection),destination_fingerprint=binding)
            return Choice(base,key,model,local,reference)

    def guard(self,choice):
        current=self.capture(choice.reference['purpose'])
        if current is None or current!=choice:raise ProfileUnavailable('호출 준비 중 모델 설정이 바뀌었습니다.')

    def model_name(self,purpose):
        selection=self.default(purpose)
        if selection['profile_id']:
            record=self.store.get(KIND,selection['profile_id'])
            return record.get('model','') if record else ''
        return os.environ.get('AEGIS_LLM_MODEL','')

    def configured(self,purpose):
        try:return self.capture(purpose) is not None
        except (ProfileUnavailable,HTTPException):return False


def get_profiles(store,allow_local=False):
    return getattr(store,'model_profiles',None) or Profiles(store,allow_local)
