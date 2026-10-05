"""Versioned task defaults. Applying a template creates a fresh pending plan."""
from typing import Any
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .remote_mcp import _decode, _digest, _encode
from .store_util import now

KIND = 'task_templates'
HISTORY = 'task_template_history'


class TemplateInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=2000)
    category: str = Field(default='', max_length=80)
    definition: dict[str, Any] = Field(default_factory=dict)
    request_id: str = Field(min_length=16, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')

    @field_validator('name','description','category')
    @classmethod
    def trimmed(cls, value):
        return value.strip()


class TemplateEdit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(strict=True, ge=1, le=9_007_199_254_740_991)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=2000)
    category: str = Field(default='', max_length=80)
    definition: dict[str, Any]


class TemplateArchive(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(strict=True, ge=1, le=9_007_199_254_740_991)
    archived: bool


class TemplateApply(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(strict=True, ge=1, le=9_007_199_254_740_991)
    request_id: str = Field(min_length=16, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    overrides: dict[str, Any] = Field(default_factory=dict)


class Templates:
    def __init__(self, store, task_model):
        self.store, self.task_model = store, task_model

    def definition(self, raw, name, *, portable=True):
        try:
            if set(raw)-set(self.task_model.model_fields):raise ValueError()
            raw=_decode(_encode(raw, 32768))
            empty=not raw.get('asset_ids')
            if empty and portable and raw.get('worker_dependencies'):raise ValueError()
            value={**raw,'name':raw.get('name',name)}
            if empty and portable:value['asset_ids']=['template-default-asset']
            result=self.task_model(**value).model_dump()
            if empty and portable:result['asset_ids']=[]
            _encode(result,32768)
            return result
        except (ValueError,TypeError,KeyError):
            raise HTTPException(422,'템플릿의 작업 설정·자산·검사·Worker 의존 관계를 확인하세요.') from None

    def actor(self, actor, db):
        fresh=self.store.user(id=actor['id'],connection=db)
        if not fresh or fresh['disabled'] or fresh['role'] not in ('admin','operator'):
            raise HTTPException(403,'운영자 또는 관리자 권한이 필요합니다.')
        return {key:fresh[key] for key in ('id','name','username','role')}

    def get(self, id, *, connection=None):
        value=self.store.get(KIND,id,connection=connection)
        if not value:raise HTTPException(404,'작업 템플릿이 없습니다.')
        return value

    def name_available(self, name, id, db):
        marker='%s' if getattr(self.store,'backend',None)=='postgres' else '?'
        field=lambda key: f"data::jsonb->>'{key}'" if marker=='%s' else f"json_extract(data,'$.{key}')"
        if db.execute(f"SELECT 1 FROM records WHERE kind={marker} AND id!={marker} AND {field('status')}='active' AND {field('name_key')}={marker} LIMIT 1",(KIND,id,name.casefold())).fetchone():
            raise HTTPException(409,'같은 이름의 활성 템플릿이 있습니다.')

    def save(self, record, actor, action, db):
        record['fingerprint']=_digest({key:record[key] for key in ('id','name','description','category','definition','status','revision')})
        history={'id':record['id']+':'+str(record['revision']),'task_id':record['id'],
                 'revision':record['revision'],'snapshot':record,'actor':actor,'action':action,'created_at':now()}
        self.store.put_many([(KIND,record),(HISTORY,history)],connection=db)
        self.store.event(None,'작업 템플릿 '+action,detail={'template_id':record['id'],'revision':record['revision'],'fingerprint':record['fingerprint'],'actor':actor},connection=db)
        return record

    def create(self, data, actor):
        name=data.name.strip()
        if not name:raise HTTPException(422,'템플릿 이름을 입력하세요.')
        definition=self.definition(data.definition,name)
        id=_digest(['aegis-task-template-v1',actor['id'],data.request_id])[:32]
        requested=_digest({'name':name,'description':data.description,'category':data.category,'definition':definition})
        with self.store.lock,self.store.write_transaction() as db:
            actor=self.actor(actor,db)
            existing=self.store.get(KIND,id,connection=db)
            if existing:
                if existing['creation_sha256']!=requested:raise HTTPException(409,'같은 저장 요청 ID의 내용이 다릅니다.')
                return {'template':existing,'created_revision':1,'replayed':True}
            marker='%s' if getattr(self.store,'backend',None)=='postgres' else '?'
            if db.execute(f'SELECT count(*) AS count FROM records WHERE kind={marker}',(KIND,)).fetchone()['count']>=1000:raise HTTPException(409,'작업 템플릿 한도(1,000개)에 도달했습니다.')
            self.name_available(name,id,db)
            record={'id':id,'name':name,'name_key':name.casefold(),'description':data.description,'category':data.category,
                    'definition':definition,'approval_mode':'administrator','status':'active','revision':1,
                    'created_at':now(),'updated_at':now(),'created_by':actor,'creation_sha256':requested}
            return {'template':self.save(record,actor,'생성',db),'created_revision':1,'replayed':False}

    def edit(self, id, data, actor):
        name=data.name.strip()
        if not name:raise HTTPException(422,'템플릿 이름을 입력하세요.')
        definition=self.definition(data.definition,name)
        with self.store.lock,self.store.write_transaction() as db:
            actor=self.actor(actor,db);original=self.get(id,connection=db)
            if original['revision']!=data.expected_revision:raise HTTPException(409,'템플릿이 변경되었습니다. 현재 버전과 작성한 내용을 비교하세요.')
            if original['status']=='active':self.name_available(name,id,db)
            record={**original,'name':name,'name_key':name.casefold(),'description':data.description.strip(),
                    'category':data.category.strip(),'definition':definition,'updated_at':now(),'revision':original['revision']+1}
            return self.save(record,actor,'수정',db)

    def archive(self, id, data, actor):
        with self.store.lock,self.store.write_transaction() as db:
            actor=self.actor(actor,db);original=self.get(id,connection=db)
            if original['revision']!=data.expected_revision:raise HTTPException(409,'템플릿 버전이 변경되었습니다.')
            status='archived' if data.archived else 'active'
            if original['status']==status:return original
            if status=='active':self.name_available(original['name'],id,db)
            return self.save({**original,'status':status,'revision':original['revision']+1,'updated_at':now()},actor,'보관' if data.archived else '복원',db)

    def application(self, id, data, actor):
        application_id=_digest(['aegis-template-application-v1',id,actor['id'],data.request_id])[:32]
        try:request_sha=_digest(_decode(_encode(data.model_dump(),32768)))
        except (ValueError,TypeError):
            raise HTTPException(422,'템플릿 적용 요청의 크기와 설정을 확인하세요.') from None
        existing=self.store.get('template_applications',application_id)
        if existing:
            if existing['request_sha256']!=request_sha:raise HTTPException(409,'같은 계획 생성 요청 ID의 내용이 다릅니다.')
            task=self.store.get('tasks',existing['task_id'])
            if not task:raise HTTPException(409,'저장된 템플릿 계획을 확인할 수 없습니다.')
            return task,None,None
        template=self.get(id)
        if template['revision']!=data.expected_revision or template['status']!='active':raise HTTPException(409,'현재 활성 템플릿을 다시 확인하세요.')
        definition=self.definition({**template['definition'],**data.overrides},template['definition']['name'],portable=False)
        return None,definition,{'template':template,'application_id':application_id,'request_sha256':request_sha,'actor':actor}

    def origin(self, request):
        source=request['template']
        return {'template_id':source['id'],'revision':source['revision'],'fingerprint':source['fingerprint'],
                'name':source['name'],'category':source['category'],'definition':source['definition'],
                'application_id':request['application_id']}

    def commit(self, request, task, records, assets, db):
        source=request['template'];actor=self.actor(request['actor'],db)
        current=self.get(source['id'],connection=db)
        if current!=source or current['status']!='active':raise HTTPException(409,'템플릿이 변경되었습니다. 새 버전을 검토하세요.')
        existing=self.store.get('template_applications',request['application_id'],connection=db)
        if existing:
            if existing['request_sha256']!=request['request_sha256']:raise HTTPException(409,'같은 계획 생성 요청 ID의 내용이 다릅니다.')
            saved=self.store.get('tasks',existing['task_id'],connection=db)
            if not saved:raise HTTPException(409,'저장된 템플릿 계획을 확인할 수 없습니다.')
            return saved
        if any(self.store.get('assets',asset['id'],connection=db)!=asset for asset in assets):raise HTTPException(409,'자산 범위가 변경되었습니다. 새 범위를 확인하세요.')
        application={'id':request['application_id'],'task_id':task['id'],'template_id':source['id'],'template_revision':source['revision'],
                     'request_sha256':request['request_sha256'],'created_at':now(),'actor':actor,'origin':task['template_origin']}
        self.store.put_many(records+[('template_applications',application)],connection=db)
        self.store.event(task['id'],'템플릿에서 현재 범위의 승인 대기 계획을 만들었습니다.',detail={'template_origin':task['template_origin'],'actor':actor},connection=db)
        return task
