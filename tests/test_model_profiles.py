"""Fixed provider recipients and call-time model identities never grant execution."""
import json,threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from tests.test_mcp_registry import configured_app
from tests.test_postgres_transfer import postgres
from tests.test_conversation import seed_proofs
from aegis.model_profiles import Profiles,ProfileEdit,ProfileUnavailable
from aegis.llm import completion

@pytest.fixture(params=['sqlite','postgres'])
def client(tmp_path,request,monkeypatch):
    for name in ('AEGIS_LLM_API_KEY','AEGIS_LLM_MODEL','AEGIS_LLM_BASE_URL'):monkeypatch.delenv(name,raising=False)
    monkeypatch.setenv('AEGIS_MODEL_DESTINATIONS',json.dumps([{'id':'owned','name':'Owned recipient','base_env':'OWNED_MODEL_BASE','key_env':'OWNED_MODEL_KEY','lab_http':True}]))
    monkeypatch.setenv('OWNED_MODEL_BASE','https://example.invalid/owned-sensitive-base')
    monkeypatch.setenv('OWNED_MODEL_KEY','owned-model-secret')
    with TestClient(configured_app(tmp_path,request.param,request,monkeypatch)) as client:
        assert client.post('/api/auth/setup',json={'password':'aegis-test-password-only'}).status_code==200
        client.app.state.event_planner.close()
        yield client


def create(client,**changes):
    return client.post('/api/model-profiles',json={'name':'Owned primary','model':'owned-primary-model','destination_id':'owned','request_id':'owned-model-create-001',**changes})


def choose(client,profile,purpose='planner',**changes):
    return client.put('/api/model-defaults/'+purpose,json={'expected_revision':0,'profile_id':profile['id'],
                     'expected_profile_revision':profile['revision'],'request_id':'owned-model-select-001',**changes})


def change(client,profile,**changes):
    return client.put('/api/model-profiles/'+profile['id'],json={'name':profile['name'],'model':profile['model'],
        'destination_id':profile['destination_id'],'enabled':profile['enabled'],'expected_revision':profile['revision'],
        'request_id':'owned-model-edit-002',**changes})


def test_profiles_disabled_by_default_mask_credentials_and_replay_original_versions(client):
    first=create(client);assert first.status_code==200;profile=first.json()['profile']
    assert not profile['enabled'] and profile['configuration_available'] and not profile['destination_review_current']
    assert choose(client,profile).status_code==409
    enabled=change(client,profile,enabled=True);assert enabled.status_code==200;current=enabled.json()['profile']
    assert current['revision']==2 and current['destination_review_current']
    assert create(client).json()['profile']['revision']==1 and create(client).json()['replayed']
    assert choose(client,current).status_code==200
    updated=change(client,current,model='owned-next-model',request_id='owned-model-edit-003');assert updated.status_code==200
    service=client.app.state.model_profiles
    assert not service.configured('planner')
    assert change(client,profile,enabled=True).json()['profile']['revision']==2
    assert choose(client,current).json()['selection']['profile_revision']==2
    assert not service.configured('planner')
    assert choose(client,updated.json()['profile'],expected_revision=1,request_id='owned-model-select-002').status_code==200
    assert service.capture('planner').model=='owned-next-model'
    store=client.app.state.store
    raw=json.dumps([store.all(k) for k in ('model_profiles','model_profile_versions','model_profile_operations','model_defaults','model_default_versions','model_default_operations')])
    assert 'owned-model-secret' not in raw and 'owned-sensitive-base' not in raw
    assert not store.all('traffic') and not store.all('llm_calls') and store.audit_integrity()['valid']


def test_recipient_rotation_blocks_calls_until_profile_and_selection_reviewed(client,monkeypatch):
    profile=create(client,enabled=True).json()['profile'];assert choose(client,profile).status_code==200
    before=client.app.state.model_profiles.capture('planner')
    monkeypatch.setenv('OWNED_MODEL_KEY','owned-rotated-model-secret')
    assert not client.app.state.model_profiles.configured('planner')
    with pytest.raises(ProfileUnavailable):client.app.state.model_profiles.guard(before)
    revised=change(client,profile).json()['profile']
    assert not client.app.state.model_profiles.configured('planner')
    assert choose(client,revised,expected_revision=1,request_id='owned-model-select-002').status_code==200
    assert client.app.state.model_profiles.capture('planner').key=='owned-rotated-model-secret'


@pytest.mark.parametrize('changes',[
    {'request_id':'short'},{'enabled':1},{'name':' '},{'model':'\nunsafe'},
    {'model':'x'*161},{'destination_id':'unknown'},{'endpoint':'https://unreviewed.invalid'},
])
def test_invalid_profile_body_does_not_create_configuration(client,changes):
    result=create(client,**changes);assert result.status_code in (404,422)
    store=client.app.state.store
    for kind in ('model_profiles','model_profile_versions','model_profile_operations'):assert store.count(kind)==0
    assert not store.all('llm_calls')


def test_profile_audit_failure_rolls_back_and_fresh_role_blocks_default_and_call(client,monkeypatch):
    profile=create(client,enabled=True).json()['profile'];assert choose(client,profile).status_code==200
    store=client.app.state.store;actor=store.user(username='admin');before=store.get('model_profiles',profile['id'])
    service=client.app.state.model_profiles
    def failed(*args,**kwargs):raise RuntimeError('owned model audit failure')
    monkeypatch.setattr(store,'event',failed)
    data=ProfileEdit(name='Changed',model=profile['model'],destination_id='owned',enabled=True,expected_revision=1,request_id='owned-model-edit-002')
    with pytest.raises(RuntimeError):service.change(profile['id'],data,actor)
    assert store.get('model_profiles',profile['id'])==before and store.count('model_profile_versions')==1
    monkeypatch.undo();store.update_user(actor['id'],role='operator')
    assert not service.configured('planner')
    assert change(client,profile).status_code==401
    assert choose(client,profile,expected_revision=1,request_id='owned-model-select-002').status_code==401
    with pytest.raises(HTTPException) as caught:service.change(profile['id'],data,actor)
    assert caught.value.status_code==403


@pytest.fixture
def provider():
    seen=[];entered=threading.Event();release=threading.Event();release.set()
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            seen.append({'model':request['model'],'authorization':self.headers['Authorization'],'request':request})
            entered.set();assert release.wait(8)
            content={'blocks':[{'text':'보존된 근거를 확인하세요.','citations':['증거 1']}]} if 'sources' in json.loads(request['messages'][1]['content']) else {'checks':['cookie_policy','security_headers']}
            body=json.dumps({'choices':[{'message':{'content':json.dumps(content)}}],'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15}}).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}/v1',seen,entered,release
    finally:release.set();server.shutdown();server.server_close();thread.join(3)


def test_selected_profile_drives_real_planner_model_key_snapshot_and_settings(client,provider,monkeypatch):
    base,seen,_,_=provider;monkeypatch.setenv('OWNED_MODEL_BASE',base)
    profile=create(client,enabled=True).json()['profile'];assert choose(client,profile).status_code==200
    store=client.app.state.store;task={'id':'owned-model-plan','name':'Owned model plan','status':'pending','planner':'ai','checks':['security_headers','cookie_policy'],'goal':'Owned checks','scope_snapshot':[]};store.put('tasks',task)
    monkeypatch.setattr('aegis.engine.completion',completion)
    assert client.app.state.engine.plan(task)==['cookie_policy','security_headers']
    metadata=store.get('tasks',task['id'])['llm_usage'];snapshot=metadata['model_profile_snapshot']
    assert snapshot['profile_id']==profile['id'] and snapshot['profile_revision']==1 and snapshot['selection_revision']==1
    call=store.get('llm_calls',metadata['call_id']);assert call['state']=='committed' and call['model_profile_snapshot']==snapshot
    assert seen[0]['model']=='owned-primary-model' and seen[0]['authorization']=='Bearer owned-model-secret'
    settings=client.get('/api/settings').json();assert settings['llm_configured'] and settings['llm_model']=='owned-primary-model'
    assert 'owned-model-secret' not in json.dumps([metadata,store.all('model_profiles'),store.all('llm_calls')])
    assert store.count('traffic')==0 and store.audit_integrity()['valid']


def test_inflight_conversation_keeps_old_default_and_new_calls_choose_new_profile(client,provider,monkeypatch):
    base,seen,entered,release=provider;monkeypatch.setenv('OWNED_MODEL_BASE',base);monkeypatch.setenv('AEGIS_LLM_CHAT_ENABLED','1')
    first=create(client,enabled=True).json()['profile']
    second=create(client,name='Owned second',model='owned-second-model',enabled=True,request_id='owned-model-create-002').json()['profile']
    assert choose(client,first,'conversation').status_code==200
    store=client.app.state.store;seed_proofs(store);monkeypatch.setattr('aegis.conversation_ai.completion',completion)
    payload={'content':'저장 근거','mode':'ai','request_id':'owned-model-chat-001'};release.clear()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(client.post,'/api/tasks/chat-task/messages',json=payload)
        assert entered.wait(4)
        try:assert choose(client,second,'conversation',expected_revision=1,request_id='owned-model-select-002').status_code==200
        finally:release.set()
        reply=future.result();assert reply.status_code==200,reply.text
    snapshot=reply.json()['assistant_generation']['model_profile_snapshot'];assert snapshot['profile_id']==first['id']
    assert client.post('/api/tasks/chat-task/messages',json=payload).json()==reply.json() and len(seen)==1
    later=client.post('/api/tasks/chat-task/messages',json={**payload,'request_id':'owned-model-chat-002'});assert later.status_code==200,later.text
    assert later.json()['assistant_generation']['model_profile_snapshot']['profile_id']==second['id']
    assert [row['model'] for row in seen]==['owned-primary-model','owned-second-model']
    assert store.count('traffic')==0 and store.audit_integrity()['valid']

@pytest.mark.parametrize('target', ['profile','selection'])
def test_modified_profile_or_default_fingerprint_blocks_new_calls(client,target):
    profile=create(client,enabled=True).json()['profile'];assert choose(client,profile).status_code==200
    store=client.app.state.store
    if target=='profile':store.patch('model_profiles',profile['id'],model='unreviewed-model')
    else:store.patch('model_defaults','planner',profile_fingerprint='unreviewed-selection')
    assert not client.app.state.model_profiles.configured('planner')
    task={'id':'owned-model-blocked','status':'pending','planner':'ai','checks':['security_headers'],
          'goal':'Owned checks','scope_snapshot':[]};store.put('tasks',task)
    assert client.app.state.engine.plan(task)==task['checks']
    assert not store.all('llm_calls') and not store.all('traffic')


def test_default_changed_after_capture_is_rejected_before_provider_post(client,monkeypatch):
    from aegis.model_profiles import DefaultEdit
    first=create(client,enabled=True).json()['profile'];assert choose(client,first).status_code==200
    second=create(client,name='Owned second',model='owned-second-model',enabled=True,request_id='owned-model-create-002').json()['profile']
    store=client.app.state.store;service=client.app.state.model_profiles;capture=service.capture;changed=False
    actor=store.user(username='admin')
    def capturing(purpose):
        nonlocal changed
        choice=capture(purpose)
        if not changed:
            changed=True
            service.choose(purpose,DefaultEdit(expected_revision=1,profile_id=second['id'],expected_profile_revision=1,request_id='owned-model-select-002'),actor)
        return choice
    monkeypatch.setattr(service,'capture',capturing)
    def forbidden(*args,**kwargs):pytest.fail('Changed configuration must not issue a provider POST')
    monkeypatch.setattr('aegis.engine.completion',forbidden)
    task={'id':'owned-model-changed','status':'pending','planner':'ai','checks':['security_headers'],'goal':'Owned checks','scope_snapshot':[]};store.put('tasks',task)
    assert client.app.state.engine.plan(task)==task['checks']
    metadata=store.get('tasks',task['id'])['llm_usage']
    assert metadata['outcome']=='request_failed' and metadata['model_profile_snapshot']['profile_id']==first['id']
    assert metadata['tokens']['status']=='missing' and not store.all('traffic')


def test_final_result_profile_cannot_differ_from_observed_call_snapshot(client,monkeypatch):
    from aegis import call_ledger
    profile=create(client,enabled=True).json()['profile'];assert choose(client,profile).status_code==200
    store=client.app.state.store
    task={'id':'owned-model-metadata','status':'pending','planner':'ai','checks':['security_headers'],'goal':'Owned checks','scope_snapshot':[]};store.put('tasks',task)
    monkeypatch.setattr('aegis.engine.completion',lambda *args,**kwargs:{'choices':[{'message':{'content':'{"checks":["security_headers"]}'}}]})
    observed=call_ledger.observe
    def changed_after_observation(store,call_id,detail):
        observed(store,call_id,detail)
        detail['model_profile_snapshot']={**detail['model_profile_snapshot'],'profile_id':'different-profile'}
    monkeypatch.setattr(call_ledger,'observe',changed_after_observation)
    with pytest.raises(RuntimeError,match='Committed result does not match provider attempt'):
        client.app.state.engine.plan(task)
    assert 'llm_usage' not in store.get('tasks',task['id'])
    call=store.all('llm_calls')[0]
    assert call['state']=='uncommitted' and call['model_profile_snapshot']['profile_id']==profile['id']
    assert store.audit_integrity()['valid'] and not store.all('traffic')


def test_guard_checks_physical_credentials_even_when_reference_is_unchanged(client):
    from dataclasses import replace
    profile=create(client,enabled=True).json()['profile'];assert choose(client,profile).status_code==200
    service=client.app.state.model_profiles;original=service.capture('planner')
    for fields in ({'base':'https://unreviewed.invalid/v1'},{'key':'unreviewed-key'},{'model':'unreviewed-model'},{'local':True}):
        with pytest.raises(ProfileUnavailable):service.guard(replace(original,**fields))
    service.guard(original)
    assert not client.app.state.store.all('llm_calls')


@pytest.mark.parametrize('changes',[{'revision':0},{'profile_id':None},{'profile_revision':'1'},{'profile_id':'missing-profile'}])
def test_malformed_persisted_selection_is_unavailable_without_provider_calls(client,changes):
    profile=create(client,enabled=True).json()['profile'];assert choose(client,profile).status_code==200
    service=client.app.state.model_profiles;store=client.app.state.store
    record={**store.get('model_defaults','planner'),**changes}
    record['fingerprint']=service.selection_fingerprint(record)
    store.put('model_defaults',record)
    assert not service.configured('planner')
    with pytest.raises(ProfileUnavailable):service.capture('planner')
    assert not store.all('llm_calls') and not store.all('traffic')


def test_concurrent_profile_and_default_saves_admit_only_one_reviewed_revision(client):
    profile=create(client,enabled=True).json()['profile']
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(lambda n:change(client,profile,model='owned-race-'+str(n),request_id='owned-race-profile-'+str(n)),range(2)))
    assert sorted(r.status_code for r in replies)==[200,409]
    current=next(r.json()['profile'] for r in replies if r.status_code==200)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(lambda n:choose(client,current,request_id='owned-race-default-'+str(n)),range(2)))
    assert sorted(r.status_code for r in replies)==[200,409]
    store=client.app.state.store
    assert store.count('model_profile_versions')==2 and store.count('model_default_versions')==1
    assert client.app.state.model_profiles.capture('planner').model==current['model']
    assert not store.all('llm_calls') and store.audit_integrity()['valid']


@pytest.mark.parametrize('base,key',[
    ('http://example.invalid/v1','owned-key'),('https://user:pass@example.invalid/v1','owned-key'),
    ('https://example.invalid/v1?redirect=1','owned-key'),('https://example.invalid:0/v1','owned-key'),
    ('https://example.invalid:65536/v1','owned-key'),('https://example.invalid/v1','bad\nkey'),
])
def test_unreviewable_recipient_never_enables_a_profile(client,monkeypatch,base,key):
    monkeypatch.setenv('OWNED_MODEL_BASE',base);monkeypatch.setenv('OWNED_MODEL_KEY',key)
    assert create(client,enabled=True).status_code==409
    store=client.app.state.store
    assert store.count('model_profiles')==store.count('model_profile_versions')==0
    assert not store.all('llm_calls') and not store.all('traffic')


def test_profile_catalog_limit_and_exhausted_versions_never_mutate(client):
    from aegis.model_profiles import DefaultEdit
    for n in range(25):
        assert create(client,name='Owned catalog '+str(n),request_id='owned-catalog-create-'+str(n)).status_code==200
    store=client.app.state.store;service=client.app.state.model_profiles
    assert create(client,name='Owned overflow',request_id='owned-catalog-overflow').status_code==409
    assert store.count('model_profiles')==store.count('model_profile_versions')==25
    profile=store.all('model_profiles')[0]
    # Explicit boundary fixtures exercise rejection without fabricating200 saves.
    profile['revision']=200;profile['fingerprint']=service.fingerprint(profile);store.put('model_profiles',profile)
    assert change(client,profile).status_code==409
    default={'id':'planner','purpose':'planner','revision':200,'profile_id':None,'profile_revision':None,'profile_fingerprint':None}
    store.put('model_defaults',default)
    actor=store.user(username='admin')
    with pytest.raises(HTTPException) as caught:
        service.choose('planner',DefaultEdit(expected_revision=200,profile_id=None,request_id='owned-default-cap-001'),actor)
    assert caught.value.status_code==409
    assert store.get('model_defaults','planner')==default and store.count('model_default_versions')==0
    assert store.count('model_profile_versions')==25 and not store.all('llm_calls')
