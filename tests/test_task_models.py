"""Task-specific model review never changes scope or authorizes execution."""
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from tests.test_model_profiles import client,provider,create,choose,change
from tests.test_postgres_transfer import postgres
from tests.test_conversation import seed_proofs
from aegis.model_profiles import ProfileUnavailable
from aegis.task_models import TaskModelEdit
from aegis.llm import completion

def task(client):
    row={'id':'owned-task-model','name':'Owned model plan','status':'pending','planner':'ai','checks':['security_headers','cookie_policy'],
         'goal':'Owned checks','scope_snapshot':[],'archive_revision':0}
    client.app.state.store.put('tasks',row);return row

def select(client,profile,purpose='planner',task_id='owned-task-model',**changes):
    return client.put('/api/tasks/'+task_id+'/models/'+purpose,json={'expected_revision':0,'expected_archive_revision':0,
                      'profile_id':profile['id'] if profile else None,'expected_profile_revision':profile['revision'] if profile else None,
                      'request_id':'owned-task-model-select-001',**changes})

def test_task_selection_replay_keeps_original_review_and_scope_without_execution(client):
    row=task(client);profile=create(client,enabled=True).json()['profile']
    first=select(client,profile);assert first.status_code==200,first.text
    assert not first.json()['execution_authorized'] and first.json()['selection']['revision']==1
    assert select(client,None,expected_revision=1,request_id='owned-task-model-select-002').status_code==200
    assert select(client,profile).json()['selection']==first.json()['selection'] and select(client,profile).json()['replayed']
    assert select(client,None).status_code==409
    store=client.app.state.store;assert store.get('tasks',row['id'])==row
    page=client.get('/api/tasks/'+row['id']+'/models/planner/history').json()
    assert page['total']==2 and len(page['items'])==2
    assert not store.all('llm_calls') and not store.all('traffic') and store.audit_integrity()['valid']

def test_task_pin_drives_actual_planner_and_does_not_follow_workspace_changes(client,provider,monkeypatch):
    row=task(client);monkeypatch.setenv('OWNED_MODEL_BASE',provider[0])
    first=create(client,enabled=True).json()['profile']
    second=create(client,name='Owned global second',model='owned-global-model',enabled=True,request_id='owned-task-model-profile-002').json()['profile']
    assert choose(client,second).status_code==200 and select(client,first).status_code==200
    monkeypatch.setattr('aegis.engine.completion',completion)
    assert client.app.state.engine.plan(row)==['cookie_policy','security_headers']
    assert provider[1][0]['model']==first['model'] and provider[1][0]['authorization']=='Bearer owned-model-secret'
    store=client.app.state.store;metadata=store.get('tasks',row['id'])['llm_usage'];snapshot=metadata['model_profile_snapshot']
    assert snapshot['profile_id']==first['id'] and snapshot['task_model_snapshot']['revision']==1
    assert snapshot['task_model_snapshot']['task_id']==row['id']
    assert store.get('llm_calls',metadata['call_id'])['model_profile_snapshot']==snapshot
    revised=change(client,first,model='owned-updated-pinned-model').json()['profile']
    with pytest.raises(ProfileUnavailable):client.app.state.model_profiles.capture('planner',row['id'])
    assert client.app.state.engine.plan(store.get('tasks',row['id']))==row['checks']
    assert len(provider[1])==1
    assert select(client,revised,expected_revision=1,request_id='owned-task-model-select-002').status_code==200
    assert client.app.state.engine.plan(store.get('tasks',row['id']))==['cookie_policy','security_headers']
    assert provider[1][1]['model']==revised['model'] and not store.all('traffic')

def test_task_conversation_pin_works_without_global_model_and_replay_preserves_old_snapshot(client,provider,monkeypatch):
    monkeypatch.setenv('OWNED_MODEL_BASE',provider[0]);monkeypatch.setenv('AEGIS_LLM_CHAT_ENABLED','1');seed_proofs(client.app.state.store)
    first=create(client,enabled=True).json()['profile']
    second=create(client,name='Owned second pin',model='owned-second-pinned-model',enabled=True,request_id='owned-task-model-profile-002').json()['profile']
    assert select(client,first,'conversation','chat-task').status_code==200
    monkeypatch.setattr('aegis.conversation_ai.completion',completion)
    payload={'content':'저장 근거','mode':'ai','request_id':'owned-task-model-chat-001'};provider[3].clear()
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(client.post,'/api/tasks/chat-task/messages',json=payload);assert provider[2].wait(4)
        try:assert select(client,second,'conversation','chat-task',expected_revision=1,request_id='owned-task-model-select-002').status_code==200
        finally:provider[3].set()
        response=pending.result(timeout=5);assert response.status_code==200,response.text
    old=response.json();snapshot=old['assistant_generation']['model_profile_snapshot']
    assert snapshot['profile_id']==first['id'] and snapshot['task_model_snapshot']['revision']==1
    assert client.post('/api/tasks/chat-task/messages',json=payload).json()==old and len(provider[1])==1
    later=client.post('/api/tasks/chat-task/messages',json={**payload,'request_id':'owned-task-model-chat-002'});assert later.status_code==200,later.text
    assert later.json()['assistant_generation']['model_profile_snapshot']['task_model_snapshot']['revision']==2
    assert [q['model'] for q in provider[1]]==[first['model'],second['model']]
    assert not client.app.state.store.all('traffic') and client.app.state.store.audit_integrity()['valid']

def test_task_model_concurrent_saves_and_audit_rollback(client,monkeypatch):
    task(client);profile=create(client,enabled=True).json()['profile']
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(lambda n:select(client,profile,request_id='owned-task-model-race-'+str(n)),range(2)))
    assert sorted(r.status_code for r in replies)==[200,409]
    store=client.app.state.store;service=client.app.state.task_models;actor=store.user(username='admin');before=service.get('owned-task-model','planner')
    def failed(*args,**kwargs):raise RuntimeError('owned task model audit failure')
    monkeypatch.setattr(store,'event',failed)
    data=TaskModelEdit(expected_revision=1,expected_archive_revision=0,profile_id=None,expected_profile_revision=None,request_id='owned-task-model-audit-001')
    with pytest.raises(RuntimeError,match='owned task model audit failure'):service.change('owned-task-model','planner',data,actor)
    assert service.get('owned-task-model','planner')==before and store.count('task_model_versions')==1 and store.count('task_model_operations')==1

def test_task_pin_capture_and_guard_reject_changed_review_or_role(client,monkeypatch):
    row=task(client);profile=create(client,enabled=True).json()['profile'];assert select(client,profile).status_code==200
    profiles=client.app.state.model_profiles;captured=profiles.capture('planner',row['id'])
    assert select(client,None,expected_revision=1,request_id='owned-task-model-select-002').status_code==200
    with pytest.raises(ProfileUnavailable):profiles.guard(captured)
    store=client.app.state.store;actor=store.user(username='admin');store.update_user(actor['id'],role='operator')
    with pytest.raises(ProfileUnavailable):profiles.capture('planner',row['id'])
    assert select(client,profile,expected_revision=2,request_id='owned-task-model-select-003').status_code==401
    assert not store.all('llm_calls') and not store.all('traffic')

def test_missing_archived_stale_and_malformed_task_model_selections_are_rejected(client):
    row=task(client);profile=create(client,enabled=True).json()['profile']
    assert select(client,profile,task_id='missing-task').status_code==404
    assert select(client,profile,expected_archive_revision=1).status_code==409
    assert select(client,profile,expected_revision=True).status_code==422
    assert select(client,profile,expected_profile_revision=None).status_code==422
    assert select(client,profile).status_code==200
    store=client.app.state.store;service=client.app.state.task_models;selection=service.get(row['id'],'planner')
    malformed={**selection,'revision':0};malformed['fingerprint']=service.fingerprint(malformed);store.put('task_model_selections',malformed)
    with pytest.raises(ProfileUnavailable):client.app.state.model_profiles.capture('planner',row['id'])
    store.put('task_model_selections',selection);store.put('tasks',{**row,'archived_at':1,'archive_revision':1})
    assert select(client,profile,expected_revision=1,request_id='owned-task-model-select-002').status_code==409
    assert not client.get('/api/tasks/'+row['id']+'/models').json()['items'][0]['configuration_available']
    with pytest.raises(ProfileUnavailable):client.app.state.model_profiles.capture('planner',row['id'])
    assert 'owned-model-secret' not in json.dumps(store.all('task_model_versions'))


@pytest.mark.parametrize('revision',[-1,True,9_007_199_254_740_992])
def test_corrupt_stored_task_archive_revision_is_unavailable_before_provider_use(client,revision):
    row=task(client);profile=create(client,enabled=True).json()['profile'];assert select(client,profile).status_code==200
    client.app.state.store.put('tasks',{**row,'archive_revision':revision})
    with pytest.raises(ProfileUnavailable):client.app.state.model_profiles.capture('planner',row['id'])
    assert not client.app.state.model_profiles.configured('planner',row['id'])
    assert not client.app.state.store.all('llm_calls') and not client.app.state.store.all('traffic')


def test_task_configuration_is_independent_and_follows_later_global_choice_only_when_cleared(client,monkeypatch):
    row=task(client);store=client.app.state.store;store.put('tasks',{**row,'id':'owned-other-task'})
    monkeypatch.setenv('AEGIS_LLM_CHAT_ENABLED','1')
    profile=create(client,enabled=True).json()['profile'];profiles=client.app.state.model_profiles
    assert not profiles.configured('conversation',row['id']) and not profiles.configured('conversation','owned-other-task')
    assert select(client,profile,'conversation').status_code==200
    current=client.get('/api/tasks/'+row['id']+'/models').json()
    assert current['conversation_enabled'] and next(s for s in current['items'] if s['purpose']=='conversation')['configuration_available']
    assert profiles.capture('conversation',row['id']).model==profile['model']
    assert not profiles.configured('conversation','owned-other-task')
    assert select(client,None,'conversation',expected_revision=1,request_id='owned-task-model-select-002').status_code==200
    assert not profiles.configured('conversation',row['id'])
    assert choose(client,profile,'conversation').status_code==200
    inherited=profiles.capture('conversation',row['id'])
    assert inherited.reference['task_model_snapshot']['revision']==2 and inherited.reference['task_model_snapshot']['profile_id'] is None
    assert profiles.capture('conversation','owned-other-task').reference['task_model_snapshot']['revision']==0
    monkeypatch.setenv('OWNED_MODEL_KEY','owned-rotated-task-key')
    with pytest.raises(ProfileUnavailable):profiles.guard(inherited)
    assert not store.all('llm_calls') and not store.all('traffic')


def test_task_model_history_pages_by_actual_task_and_purpose_and_rejects_synthetic_cap(client):
    row=task(client);profile=create(client,enabled=True).json()['profile']
    for revision in range(26):
        response=select(client,profile if revision%2==0 else None,expected_revision=revision,request_id='owned-task-model-page-'+str(revision))
        assert response.status_code==200,response.text
    assert select(client,profile,'conversation').status_code==200
    path='/api/tasks/'+row['id']+'/models/planner/history'
    first=client.get(path).json();second=client.get(path,params={'offset':25,'snapshot':first['snapshot']}).json()
    assert len(first['items'])==25 and first['total']==26 and first['has_more']
    assert len(second['items'])==1 and not second['has_more']
    assert len({r['id'] for r in first['items']+second['items']})==26
    assert all(r['purpose']=='planner' and r['task_id']==row['id'] for r in first['items']+second['items'])
    assert client.get(path,params={'limit':26}).status_code==422
    store=client.app.state.store;service=client.app.state.task_models;selection=service.get(row['id'],'planner')
    # Explicit synthetic current revision tests exhaustion, not174 additional saves.
    selection={**selection,'revision':200};selection['fingerprint']=service.fingerprint(selection);store.put('task_model_selections',selection)
    count=store.count('task_model_versions')
    assert select(client,profile,expected_revision=200,request_id='owned-task-model-overflow-001').status_code==409
    assert service.get(row['id'],'planner')==selection and store.count('task_model_versions')==count
    assert not store.all('llm_calls') and not store.all('traffic')


def test_standalone_profile_factory_honors_persisted_task_pin_without_app_binding(client,monkeypatch):
    from aegis.model_profiles import get_profiles
    row=task(client);profile=create(client,enabled=True).json()['profile'];assert select(client,profile).status_code==200
    store=client.app.state.store;monkeypatch.delattr(store,'model_profiles')
    standalone=get_profiles(store,True);choice=standalone.capture('planner',row['id'])
    assert choice is not None and choice.model==profile['model']
    assert choice.reference['task_model_snapshot']['revision']==1
    standalone.guard(choice)
    assert not store.all('llm_calls') and not store.all('traffic')
