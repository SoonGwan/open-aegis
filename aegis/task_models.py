"""Reviewed future-call model selection for an individual task and existing role."""
from fastapi import HTTPException
from .model_profiles import DefaultEdit,Revision,Choice,ProfileUnavailable
from .remote_mcp import _digest
from .store_util import now

KIND='task_model_selections'

class TaskModelEdit(DefaultEdit):
    expected_archive_revision:Revision

class TaskModels:
    def __init__(self,store,profiles):self.store=store;self.profiles=profiles

    def key(self,task_id,purpose):return _digest(['aegis-task-model-v1',task_id,purpose])[:32]

    def fingerprint(self,record):
        return _digest({key:record.get(key) for key in ('id','task_id','purpose','revision','profile_id','profile_revision','profile_fingerprint','actor')})

    def task(self,task_id,db=None):
        task=self.store.get('tasks',task_id,connection=db)
        if not task:raise HTTPException(404,'작업이 없습니다.')
        revision=task.get('archive_revision',0)
        if task.get('id')!=task_id or type(revision) is not int or not 0<=revision<=9_007_199_254_740_991:
            raise HTTPException(409,'작업의 저장된 참조를 확인하세요.')
        return task

    def get(self,task_id,purpose,db=None):
        return self.store.get(KIND,self.key(task_id,purpose),connection=db) or {
            'id':self.key(task_id,purpose),'task_id':task_id,'purpose':purpose,'revision':0,
            'profile_id':None,'profile_revision':None,'profile_fingerprint':None}

    def public(self,task_id,purpose):
        with self.store.read_transaction() as db:
            task=self.task(task_id,db);selection=self.get(task_id,purpose,db)
        try:available=self.capture(purpose,task_id) is not None
        except (ProfileUnavailable,HTTPException):available=False
        return {**selection,'configuration_available':available,'archive_revision':task.get('archive_revision',0),
                'task_archived':bool(task.get('archived_at'))}

    def version_records(self,task_id,purpose,revision,profile,actor):
        record={'id':self.key(task_id,purpose),'task_id':task_id,'purpose':purpose,'revision':revision,
                'profile_id':profile['id'] if profile else None,'profile_revision':profile['revision'] if profile else None,
                'profile_fingerprint':profile['fingerprint'] if profile else None,'actor':actor,'updated_at':now()}
        record['fingerprint']=self.fingerprint(record)
        version={'id':record['id']+':'+str(revision),'task_id':task_id,'purpose':purpose,
                 'revision':revision,'snapshot':record,'actor':actor,'created_at':record['updated_at']}
        return record,[(KIND,record),('task_model_versions',version)]

    def change(self,task_id,purpose,data,actor):
        if (data.profile_id is None)!=(data.expected_profile_revision is None):raise HTTPException(422,'프로필과 현재 버전을 함께 지정하세요.')
        operation_id=_digest(['aegis-task-model-save-v1',task_id,purpose,actor['id'],data.request_id])[:32]
        requested=_digest(data.model_dump(exclude={'request_id'}))
        with self.store.lock,self.store.write_transaction() as db:
            actor=self.profiles.actor(actor,db);operation=self.store.get('task_model_operations',operation_id,connection=db)
            if operation:
                if operation['request_sha256']!=requested:raise HTTPException(409,'같은 작업 모델 요청 ID의 내용이 다릅니다.')
                return {'selection':operation['snapshot'],'replayed':True,'execution_authorized':False}
            task=self.task(task_id,db)
            if task.get('archived_at') or task.get('archive_revision',0)!=data.expected_archive_revision:
                raise HTTPException(409,'작업의 보관 상태가 변경되었습니다. 최신 작업을 검토하세요.')
            before=self.get(task_id,purpose,db)
            if type(before.get('revision')) is not int or before['revision']!=data.expected_revision:
                raise HTTPException(409,'작업 모델 선택이 변경되었습니다. 최신 버전을 검토하세요.')
            if before['revision']>=200:raise HTTPException(409,'작업 모델 선택은 용도별 최대200개 버전입니다.')
            profile=self.profiles.get(data.profile_id,db) if data.profile_id else None
            if profile:
                if profile['revision']!=data.expected_profile_revision:raise HTTPException(409,'모델 프로필 버전이 변경되었습니다.')
                try:self.profiles._profile(profile,db)
                except ProfileUnavailable as error:raise HTTPException(409,str(error)) from None
            record,records=self.version_records(task_id,purpose,before['revision']+1,profile,actor)
            self.store.put_many(records+[('task_model_operations',{'id':operation_id,'snapshot':record,'request_sha256':requested})],connection=db)
            self.store.event(task_id,'작업 모델 선택 저장',detail={'purpose':purpose,'revision':record['revision'],
                             'profile_id':record['profile_id'],'profile_revision':record['profile_revision'],'actor':actor},connection=db)
            return {'selection':record,'replayed':False,'execution_authorized':False}

    def capture(self,purpose,task_id):
        with self.store.read_transaction() as db:
            stored=self.store.get(KIND,self.key(task_id,purpose),connection=db);selection=stored or self.get(task_id,purpose,db)
            if (selection.get('id')!=self.key(task_id,purpose) or selection.get('task_id')!=task_id or selection.get('purpose')!=purpose
                    or type(selection.get('revision')) is not int or not 0<=selection['revision']<=200):
                raise ProfileUnavailable('작업 모델 선택 참조를 확인하세요.')
            if stored:
                try:task=self.task(task_id,db)
                except HTTPException:raise ProfileUnavailable('작업의 저장된 참조를 확인하세요.') from None
                if task.get('archived_at'):raise ProfileUnavailable('보관된 작업의 모델을 호출할 수 없습니다.')
                if selection['revision']==0 or selection.get('fingerprint')!=self.fingerprint(selection):
                    raise ProfileUnavailable('작업 모델 선택 버전·지문을 확인하세요.')
                actor=selection.get('actor');fresh=self.store.user(id=actor['id'],connection=db) if isinstance(actor,dict) and isinstance(actor.get('id'),str) else None
                if not fresh or fresh['disabled'] or fresh['role']!='admin':raise ProfileUnavailable('작업 모델 선택의 관리자 검토를 확인하세요.')
            profile_id=selection.get('profile_id')
            if profile_id is None:
                if selection.get('profile_revision') is not None or selection.get('profile_fingerprint') is not None:
                    raise ProfileUnavailable('작업 모델의 프로필 참조를 확인하세요.')
                choice=None
            else:
                if not isinstance(profile_id,str) or type(selection.get('profile_revision')) is not int or not isinstance(selection.get('profile_fingerprint'),str):
                    raise ProfileUnavailable('작업 모델의 프로필 참조를 확인하세요.')
                profile=self.store.get('model_profiles',profile_id,connection=db)
                if not profile or profile.get('revision')!=selection['profile_revision'] or profile.get('fingerprint')!=selection['profile_fingerprint']:
                    raise ProfileUnavailable('작업에 선택한 모델 프로필을 다시 검토하세요.')
                base,key,local,binding=self.profiles._profile(profile,db)
                reference={'kind':'profile','purpose':purpose,'profile_id':profile_id,'profile_revision':profile['revision'],
                           'profile_fingerprint':profile['fingerprint'],'destination_id':profile['destination_id'],'model':profile['model'],
                           'selection_revision':selection['revision'],'selection_fingerprint':selection['fingerprint'],'destination_fingerprint':binding}
                choice=Choice(base,key,profile['model'],local,reference)
        if profile_id is None:choice=self.profiles.capture(purpose)
        if choice is None:return None
        snapshot={key:selection.get(key) for key in ('task_id','purpose','revision','profile_id','profile_revision')}
        snapshot['fingerprint']=self.fingerprint(selection)
        return Choice(choice.base,choice.key,choice.model,choice.local,{**choice.reference,'task_model_snapshot':snapshot})
