"""Creation receipts and initial model choices commit before planning, never approval."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from tests.test_model_profiles import client,provider,create,change,choose
from tests.test_postgres_transfer import postgres
from tests.test_conversation import seed_proofs
from aegis.model_profiles import ProfileUnavailable

def definition(client):
    asset=client.post('/api/assets',json={'name':'Owned initial model asset','url':'https://example.invalid/lab','authorized':True}).json()
    return {'name':'Owned initial model task','asset_ids':[asset['id']],'checks':['security_headers','cookie_policy'],'planner':'ai'}

def payload(client,profile,**changes):
    return {'task':definition(client),'models':{purpose:{'profile_id':profile['id'],'expected_profile_revision':profile['revision']} for purpose in ('planner','conversation')},
            'request_id':'owned-initial-model-create-001',**changes}

def submit(client,body):return client.post('/api/tasks/with-models',json=body)

def test_creation_pins_first_planning_and_keeps_execution_pending(client,provider,monkeypatch):
    monkeypatch.setenv('OWNED_MODEL_BASE',provider[0]);profile=create(client,enabled=True).json()['profile'];body=payload(client,profile)
    response=submit(client,body);assert response.status_code==200,response.text
    result=response.json();task=result['task'];store=client.app.state.store
    assert not result['replayed'] and not result['execution_authorized'] and task['status']=='pending' and not task['approved_at']
    assert set(result['creation']['selections'])=={'planner','conversation'}
    for purpose in ('planner','conversation'):
        choice=client.app.state.model_profiles.capture(purpose,task['id'])
        assert choice.model==profile['model'] and choice.reference['task_model_snapshot']['revision']==1
    assert not store.all('llm_calls') and not store.all('traffic')
    monkeypatch.setattr('aegis.engine.completion',__import__('aegis.llm',fromlist=['completion']).completion)
    assert client.app.state.engine.plan(task)==['cookie_policy','security_headers']
    assert len(provider[1])==1 and provider[1][0]['model']==profile['model']
    assert store.all('llm_calls')[0]['model_profile_snapshot']['task_model_snapshot']['revision']==1
    assert store.get('tasks',task['id'])['status']=='pending' and not store.all('traffic') and store.audit_integrity()['valid']

def test_creation_replay_preserves_current_task_and_original_choices_after_edits(client):
    profile=create(client,enabled=True).json()['profile'];body=payload(client,profile);first=submit(client,body).json();task=first['task'];store=client.app.state.store
    revised=change(client,profile,model='owned-revised-after-creation').json()['profile']
    assert client.put('/api/tasks/'+task['id']+'/models/planner',json={'profile_id':revised['id'],'expected_profile_revision':revised['revision'],
        'expected_revision':1,'expected_archive_revision':0,'request_id':'owned-initial-later-select-001'}).status_code==200
    store.patch('tasks',task['id'],status='rejected',finished_at=1)
    replay=submit(client,body);assert replay.status_code==200,replay.text
    assert replay.json()['replayed'] and replay.json()['task']==store.get('tasks',task['id'])
    assert replay.json()['creation']==first['creation'] and store.count('tasks')==1
    assert store.count('task_model_creation_operations')==1 and store.count('task_model_versions')==3
    changed={**body,'task':{**body['task'],'name':'Changed creation body'}};assert submit(client,changed).status_code==409
    assert not store.all('traffic') and not store.all('llm_calls') and store.audit_integrity()['valid']

def test_creation_concurrent_same_request_is_one_task_and_two_selection_versions(client):
    profile=create(client,enabled=True).json()['profile'];body=payload(client,profile)
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:submit(client,body),range(2)))
    assert [r.status_code for r in responses]==[200,200]
    assert sorted(r.json()['replayed'] for r in responses)==[False,True]
    store=client.app.state.store;assert store.count('tasks')==1 and store.count('task_model_versions')==2
    assert store.count('task_model_creation_operations')==1 and store.audit_integrity()['valid']

def test_first_conversation_uses_creation_choice_without_workspace_default(client,provider,monkeypatch):
    monkeypatch.setenv('OWNED_MODEL_BASE',provider[0]);monkeypatch.setenv('AEGIS_LLM_CHAT_ENABLED','1')
    profile=create(client,enabled=True).json()['profile'];body=payload(client,profile);task=submit(client,body).json()['task'];store=client.app.state.store
    # Explicit synthetic stored evidence is conversation input, not an executed target check.
    proof=seed_proofs(store);store.put('evidence',{**proof,'task_id':task['id']})
    finding=store.get('findings','cited-finding');store.put('findings',{**finding,'task_ids':[task['id']]})
    from aegis.llm import completion
    monkeypatch.setattr('aegis.conversation_ai.completion',completion)
    request={'content':'저장된 근거 확인','mode':'ai','request_id':'owned-initial-first-chat-001'}
    response=client.post('/api/tasks/'+task['id']+'/messages',json=request);assert response.status_code==200,response.text
    snapshot=response.json()['assistant_generation']['model_profile_snapshot']
    assert snapshot['profile_id']==profile['id'] and snapshot['task_model_snapshot']['revision']==1
    assert len(provider[1])==1 and provider[1][0]['model']==profile['model']
    assert client.post('/api/tasks/'+task['id']+'/messages',json=request).json()==response.json() and len(provider[1])==1
    assert not store.all('model_defaults') and not store.all('traffic') and store.get('tasks',task['id'])['status']=='pending'

@pytest.mark.parametrize('changed',['role','key'])
def test_review_change_after_prepare_is_rechecked_before_creation_commit(client,monkeypatch,changed):
    profile=create(client,enabled=True).json()['profile'];body=payload(client,profile);store=client.app.state.store;service=client.app.state.task_model_creation
    original=service.prepare
    def intervening(data,actor):
        result=original(data,actor)
        if changed=='role':store.update_user(actor['id'],role='operator')
        else:monkeypatch.setenv('OWNED_MODEL_KEY','owned-key-changed-after-prepare')
        return result
    monkeypatch.setattr(service,'prepare',intervening)
    assert submit(client,body).status_code in (403,409)
    for kind in ('tasks','coverage','task_model_selections','task_model_versions','task_model_creation_operations'):assert store.count(kind)==0

def test_asset_changed_at_atomic_commit_rolls_back_every_creation_record(client,monkeypatch):
    profile=create(client,enabled=True).json()['profile'];body=payload(client,profile);store=client.app.state.store;service=client.app.state.task_model_creation
    original=service.commit;before=store.get('assets',body['task']['asset_ids'][0])
    def intervening(request,task,records,assets,db):
        store.put_many([('assets',{**before,'name':'Changed at commit'})],connection=db)
        return original(request,task,records,assets,db)
    monkeypatch.setattr(service,'commit',intervening)
    assert submit(client,body).status_code==409 and store.get('assets',before['id'])==before
    for kind in ('tasks','coverage','task_model_selections','task_model_versions','task_model_creation_operations'):assert store.count(kind)==0

@pytest.mark.parametrize('failure',['stale','disabled','key','missing','asset'])
def test_invalid_creation_review_has_no_partial_records(client,monkeypatch,failure):
    profile=create(client,enabled=True).json()['profile'];body=payload(client,profile)
    if failure=='stale':change(client,profile,model='owned-current-profile')
    elif failure=='disabled':change(client,profile,enabled=False)
    elif failure=='key':monkeypatch.setenv('OWNED_MODEL_KEY','owned-changed-initial-key')
    elif failure=='missing':body['models']['planner']['profile_id']='missing-profile'
    else:client.app.state.store.patch('assets',body['task']['asset_ids'][0],archived_at=1)
    response=submit(client,body);assert response.status_code in (404,409),response.text
    store=client.app.state.store
    for kind in ('tasks','coverage','task_model_selections','task_model_versions','task_model_creation_operations','traffic','llm_calls'):assert store.count(kind)==0
    assert store.audit_integrity()['valid']

def test_creation_audit_failure_rolls_back_task_coverage_choices_and_receipt(client,monkeypatch):
    profile=create(client,enabled=True).json()['profile'];body=payload(client,profile);store=client.app.state.store
    def failed(*args,**kwargs):raise RuntimeError('owned creation audit failure')
    monkeypatch.setattr(store,'event',failed)
    with pytest.raises(RuntimeError,match='owned creation audit failure'):submit(client,body)
    for kind in ('tasks','coverage','task_model_selections','task_model_versions','task_model_creation_operations'):assert store.count(kind)==0
    assert store.audit_integrity()['valid']

def test_omitted_role_inherits_default_and_standard_creation_does_not_pin(client):
    profile=create(client,enabled=True).json()['profile'];assert choose(client,profile,'conversation').status_code==200
    body=payload(client,profile);del body['models']['conversation'];created=submit(client,body).json();task=created['task']
    choice=client.app.state.model_profiles.capture('conversation',task['id']);assert choice.reference['task_model_snapshot']['revision']==0
    assert not created['creation']['selections'].get('conversation')
    ordinary=client.post('/api/tasks',json={**body['task'],'name':'Ordinary creation'});assert ordinary.status_code==200
    assert 'model_creation' not in ordinary.json()
    assert client.app.state.task_models.get(ordinary.json()['id'],'planner')['revision']==0
    assert client.app.state.store.count('task_model_versions')==1 and not client.app.state.store.all('traffic')

def test_creation_replay_requires_current_admin_and_refuses_missing_task(client):
    profile=create(client,enabled=True).json()['profile'];body=payload(client,profile);first=submit(client,body).json();store=client.app.state.store
    store.patch('tasks',first['task']['id'],model_creation={})
    assert submit(client,body).status_code==409 and store.count('tasks')==1
    admin=store.user(username='admin');store.update_user(admin['id'],role='operator')
    assert submit(client,body).status_code==401
    assert client.post('/api/auth/login',json={'username':'admin','password':'aegis-test-password-only'}).status_code==200
    assert submit(client,body).status_code==403 and store.count('tasks')==1

@pytest.mark.parametrize('models',[{}, {'unknown':{'profile_id':'profile','expected_profile_revision':1}},
    {'planner':{'profile_id':'profile','expected_profile_revision':0}},
    {'planner':{'profile_id':'profile','expected_profile_revision':True}},
    {'planner':{'profile_id':'profile','expected_profile_revision':1,'endpoint':'https://unreviewed.invalid'}}])
def test_invalid_creation_models_are_rejected_without_task(client,models):
    body={'task':definition(client),'models':models,'request_id':'owned-initial-invalid-001'}
    assert submit(client,body).status_code==422 and not client.app.state.store.all('tasks')
