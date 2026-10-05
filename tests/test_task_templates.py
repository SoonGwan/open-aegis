"""Template revisions, role boundaries and pending plans on both storage engines."""
import copy
import pytest
from tests.test_mcp_registry import client
from tests.test_postgres_transfer import postgres
from tests.test_validation import lab, register, finish
from tests.test_identity import add, login
from aegis.task_templates import Templates

BASE='/api/task-templates'


def body(**changes):
    return {'name':'Baseline checks','description':'Reusable defaults','category':'Web security',
            'definition':{'checks':['security_headers'],'workers':2,'planner':'rules'},
            'request_id':'template-create-0001',**changes}


def create(client,**changes):
    response=client.post(BASE,json=body(**changes));assert response.status_code==200,response.text
    return response.json()['template']


def apply_body(template,asset,**changes):
    return {'expected_revision':template['revision'],'request_id':'template-apply-0001',
            'overrides':{'asset_ids':[asset['id']]},**changes}


def edit_body(template,**changes):
    return {'expected_revision':template['revision'],**{key:template[key] for key in ('name','description','category','definition')},**changes}


def test_portable_template_pending_plan_approval_provenance_and_replay(client,lab):
    asset=register(client,lab[0]);template=create(client)
    assert template['definition']['asset_ids']==[]
    assert template['approval_mode']=='administrator'
    route=BASE+'/'+template['id'];payload=apply_body(template,asset)
    first=client.post(route+'/apply',json=payload);assert first.status_code==200,first.text
    task=first.json();assert task['status']=='pending' and task['approved_at'] is None
    assert task['scope_snapshot'][0]['revision']==asset['revision']
    assert task['template_origin']['revision']==1 and task['template_origin']['fingerprint']==template['fingerprint']
    assert task['template_origin']['definition']==template['definition'] and not lab[1].requests
    assert client.post(route+'/apply',json=payload).json()==task
    assert client.app.state.store.count('template_applications')==1
    edited=client.put(route,json=edit_body(template,name='Revised checks')).json()
    assert edited['revision']==2 and client.post(route+'/apply',json=payload).json()==task
    assert client.post(route+'/apply',json=apply_body(template,asset,request_id='template-apply-0002')).status_code==409
    assert client.post('/api/tasks/'+task['id']+'/approve').status_code==200
    assert finish(client,task['id'])['task']['status']=='completed' and len(lab[1].requests)==1
    assert client.get('/api/tasks/'+task['id']).json()['task']['template_origin']['name']==template['name']
    assert client.app.state.store.audit_integrity()['valid']


def test_revision_archive_restore_duplicate_names_and_history(client):
    template=create(client);route=BASE+'/'+template['id']
    assert client.post(BASE,json=body(request_id='other-create-0001',name='BASELINE CHECKS')).status_code==409
    edited=client.put(route,json=edit_body(template,description='Human edit')).json();assert edited['revision']==2
    assert client.put(route,json=edit_body(template,name='Stale edit')).status_code==409
    archived=client.post(route+'/archive',json={'expected_revision':2,'archived':True}).json();assert archived['revision']==3
    assert client.get(BASE).json()['total']==0 and client.get(BASE,params={'status':'archived'}).json()['total']==1
    assert client.post(route+'/apply',json={'expected_revision':3,'request_id':'archived-apply-001','overrides':{}}).status_code==409
    assert client.post(route+'/archive',json={'expected_revision':3,'archived':True}).json()==archived
    duplicate=create(client,request_id='other-create-0002')
    assert client.post(route+'/archive',json={'expected_revision':3,'archived':False}).status_code==409
    assert client.put(BASE+'/'+duplicate['id'],json=edit_body(duplicate,name='Different name')).status_code==200
    assert client.post(route+'/archive',json={'expected_revision':3,'archived':False}).json()['revision']==4
    history=client.get(route+'/history').json();assert history['total']==4
    original=next(row['snapshot'] for row in history['items'] if row['revision']==1)
    assert original==template
    replay=client.post(BASE,json=body()).json();assert replay['replayed'] and replay['template']['revision']==4
    assert client.post(BASE,json=body(description='different retry')).status_code==409


@pytest.mark.parametrize('definition',[{'status':'completed'},{'approved_at':1},{'checks':['not-a-tool']},{'workers':9},
    {'planner':'unknown'},{'worker_dependencies':{'missing':['other']}},{'asset_ids':['same','same']},
    {'remote_connection_id':'http://not-an-id'},{'goal':'x'*2001}])
def test_invalid_or_authority_bearing_defaults_rejected_without_records(client,definition):
    before=client.app.state.store.count('task_templates')
    assert client.post(BASE,json=body(definition=definition)).status_code==422
    assert client.app.state.store.count('task_templates')==before


def test_sql_search_pagination_and_snapshot_without_full_scan(client,monkeypatch):
    for index in range(28):create(client,name=f'Example {index}',request_id=f'create-page-{index:04}',category='category needle' if index%2 else 'other')
    def forbidden(*args,**kwargs):raise AssertionError('Template listing must use bounded SQL')
    monkeypatch.setattr(client.app.state.store,'all',forbidden)
    first=client.get(BASE,params={'limit':10,'search':'category needle'}).json()
    assert first['total']==14 and len(first['items'])==10
    second=client.get(BASE,params={'limit':10,'offset':10,'snapshot':first['snapshot'],'search':'category needle'}).json()
    assert len(second['items'])==4 and not ({r['id'] for r in first['items']} & {r['id'] for r in second['items']})
    assert client.get(BASE,params={'limit':26}).status_code==422


def test_viewer_read_operator_create_apply_and_admin_only_execution(client,lab):
    asset=register(client,lab[0]);viewer=add(client,'viewer');operator=add(client,'operator')
    with login(client.app,operator['username']) as other:
        template=create(other);route=BASE+'/'+template['id']
        task=other.post(route+'/apply',json=apply_body(template,asset)).json()
        assert task['status']=='pending' and other.post('/api/tasks/'+task['id']+'/approve').status_code==403
    with login(client.app,viewer['username']) as read:
        assert read.get(route).status_code==200 and read.get(route+'/history').status_code==200
        assert read.post(BASE,json=body(request_id='viewer-create-0001')).status_code==403
        assert read.put(route,json=edit_body(template)).status_code==403
        assert read.post(route+'/archive',json={'expected_revision':1,'archived':True}).status_code==403
        assert read.post(route+'/apply',json=apply_body(template,asset,request_id='viewer-apply-0001')).status_code==403
    assert not lab[1].requests


@pytest.mark.parametrize('operation',['create','edit','archive','apply'])
def test_audit_failure_rolls_back_templates_history_plan_and_application(client,lab,monkeypatch,operation):
    template=create(client);asset=register(client,lab[0]);store=client.app.state.store
    client.app.state.event_planner.close()
    kinds=('task_templates','task_template_history','tasks','coverage','template_applications')
    before={kind:store.all(kind) for kind in kinds};audit=store.audit_integrity();original=store.event
    def reject(task_id,message,*args,**kwargs):
        if message.startswith(('작업 템플릿','템플릿에서')):raise RuntimeError('Owned template audit failure')
        return original(task_id,message,*args,**kwargs)
    route=BASE+'/'+template['id']
    with monkeypatch.context() as patch:
        patch.setattr(store,'event',reject)
        with pytest.raises(RuntimeError,match='template audit failure'):
            if operation=='create':client.post(BASE,json=body(name='Other',request_id='failed-create-0001'))
            elif operation=='edit':client.put(route,json=edit_body(template,name='Changed'))
            elif operation=='archive':client.post(route+'/archive',json={'expected_revision':1,'archived':True})
            else:client.post(route+'/apply',json=apply_body(template,asset))
    assert {kind:store.all(kind) for kind in kinds}==before and store.audit_integrity()==audit
    assert not lab[1].requests


@pytest.mark.parametrize('change',['asset','template','actor'])
def test_changed_scope_template_or_role_at_commit_rejects_plan(client,lab,monkeypatch,change):
    template=create(client);asset=register(client,lab[0]);store=client.app.state.store
    original=Templates.commit
    def changed(self,request,task,records,assets,db):
        if change=='asset':
            record=store.get('assets',asset['id'],connection=db);record['revision']+=1;store.put_many([('assets',record)],connection=db)
        elif change=='template':
            record=store.get('task_templates',template['id'],connection=db);record['revision']+=1;store.put_many([('task_templates',record)],connection=db)
        else:
            user=store.user(id=request['actor']['id'],connection=db)
            marker='%s' if getattr(store,'backend',None)=='postgres' else '?'
            db.execute(f'UPDATE users SET role={marker} WHERE id={marker}',('viewer',user['id']))
        return original(self,request,task,records,assets,db)
    monkeypatch.setattr(Templates,'commit',changed)
    response=client.post(BASE+'/'+template['id']+'/apply',json=apply_body(template,asset))
    assert response.status_code==(403 if change=='actor' else 409),response.text
    assert store.count('tasks')==0 and store.count('template_applications')==0 and not lab[1].requests


def test_replan_preserves_original_template_version_with_fresh_scope(client,lab):
    asset=register(client,lab[0]);template=create(client)
    task=client.post(BASE+'/'+template['id']+'/apply',json=apply_body(template,asset)).json()
    assert client.put(BASE+'/'+template['id'],json=edit_body(template,name='Later version')).status_code==200
    client.app.state.store.patch('assets',asset['id'],revision=2)
    response=client.post('/api/tasks/'+task['id']+'/replan');assert response.status_code==200,response.text
    replanned=response.json()
    assert replanned['template_origin']==task['template_origin']
    assert replanned['scope_snapshot'][0]['revision']==2 and replanned['status']=='pending'
    assert not lab[1].requests


@pytest.mark.parametrize('override',[{'status':'completed'},{'approved_at':1},{'scope_snapshot':[]},{'checks':[]},{'asset_ids':[]}])
def test_apply_rejects_authority_overrides_and_invalid_selection(client,lab,override):
    asset=register(client,lab[0]);template=create(client)
    data=apply_body(template,asset);data['overrides'].update(override)
    response=client.post(BASE+'/'+template['id']+'/apply',json=data)
    assert response.status_code==422,response.text
    assert client.app.state.store.count('tasks')==0 and not lab[1].requests


def test_apply_uses_current_asset_revision_and_archival_refuses_new_plan(client,lab):
    asset=register(client,lab[0]);template=create(client,definition={'checks':['security_headers'],'asset_ids':[asset['id']]})
    store=client.app.state.store;store.patch('assets',asset['id'],revision=2)
    route=BASE+'/'+template['id']+'/apply';data=apply_body(template,asset);data['overrides']={}
    response=client.post(route,json=data);assert response.status_code==200,response.text
    assert response.json()['scope_snapshot'][0]['revision']==2
    store.patch('assets',asset['id'],archived_at=1,revision=3)
    assert client.post(route,json={**data,'request_id':'archived-scope-0001'}).status_code==409
    assert client.post(route,json=data).json()['id']==response.json()['id']
    assert store.count('tasks')==1 and not lab[1].requests


def test_oversized_apply_request_is_a_bounded_client_error_without_write(client,lab):
    asset=register(client,lab[0]);template=create(client)
    payload=apply_body(template,asset);payload['overrides']['goal']='x'*40000
    response=client.post(BASE+'/'+template['id']+'/apply',json=payload)
    assert response.status_code==422 and 'x'*100 not in response.text
    assert client.app.state.store.count('tasks')==0 and not lab[1].requests


from tests.test_mcp_task_execution import workspace,register as register_remote
from tests.test_mcp_execution import service,target


def test_remote_template_requires_current_registered_tool_and_separate_approval(workspace,target):
    client=workspace;url,state=target
    tool=register_remote(client,['security_headers'])[0]
    asset=register(client,url)
    template=create(client,definition={'checks':['security_headers'],'remote_connection_id':'owned-server'})
    route=BASE+'/'+template['id']+'/apply';payload=apply_body(template,asset)
    response=client.post(route,json=payload);assert response.status_code==200,response.text
    task=response.json()
    assert task['remote_execution']['connection_id']=='owned-server' and not state['requests']
    assert client.post('/api/integrations/mcp/tools/'+tool['id']+'/disable',json={'revision':tool['revision']}).status_code==200
    assert client.post('/api/tasks/'+task['id']+'/approve').status_code==409
    assert client.post(route,json={**payload,'request_id':'disabled-remote-001'}).status_code==409
    assert client.post(route,json=payload).json()['id']==task['id'] and not state['requests']
