"""Actual owned native HTTP calls, reviewed profiles, immutable receipts and no target IO."""
import json,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from fastapi.testclient import TestClient
from tests.test_mcp_registry import configured_app
from tests.test_postgres_transfer import postgres
from tests.test_model_profiles import create,choose
from tests.test_task_model_creation import payload,submit
from tests.test_conversation import seed_proofs
from aegis.llm import completion
from aegis.model_profiles import ProfileUnavailable

@pytest.fixture
def peer():
    seen=[];settings={'status':200,'content_type':'application/json','encoding':'identity'}
    class Handler(BaseHTTPRequestHandler):
        def respond(self,body=None):
            seen.append({'method':self.command,'path':self.path,'authorization':self.headers.get('Authorization'),'api_key':self.headers.get('x-api-key'),'version':self.headers.get('anthropic-version'),'body':body})
            if self.command=='GET':answer={'data':[{'id':'owned-native-model'}],'has_more':False}
            else:
                text=body['messages'][-1]['content']
                if text=='Reply exactly AEGIS_OK.':content='AEGIS_OK'
                else:
                    data=json.loads(text)
                    if 'checks' in data:answer={'checks':list(reversed(data['checks']))}
                    elif 'tools' in data:
                        answer={'objectives':[{'id':'g1','title':'Owned native goal','rationale':'Owned proposed review',
                            'asset_ids':[row['id'] for row in data['assets']],'checks':['cookie_policy'],
                            'expected_evidence':'Owned cookie configuration evidence','missing_inputs':[]}],'worker_dependencies':{}}
                    else:answer={'blocks':[{'text':'Owned cited response','citations':list(data['sources'])[:1]}]}
                    content=json.dumps(answer)
                answer={'type':'message','role':'assistant','stop_reason':'end_turn','content':[{'type':'text','text':content}],
                        'usage':{'input_tokens':5,'output_tokens':3},'ignored':'owned-native-secret'}
            raw=settings.get('raw',json.dumps(settings.get('body',answer)).encode())
            self.send_response(settings['status']);self.send_header('Content-Type',settings['content_type']);self.send_header('Content-Encoding',settings['encoding']);self.send_header('Content-Length',str(settings.get('length',len(raw))))
            self.send_header('Location','https://unreviewed.invalid/');self.end_headers()
            try:self.wfile.write(raw)
            except (BrokenPipeError,ConnectionResetError):pass
        def do_POST(self):self.respond(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        def do_GET(self):self.respond()
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}/v1',seen,settings
    finally:server.shutdown();server.server_close();thread.join(3)

@pytest.fixture(params=['sqlite','postgres'])
def client(tmp_path,request,monkeypatch,peer):
    for name in ('AEGIS_LLM_API_KEY','AEGIS_LLM_MODEL','AEGIS_LLM_BASE_URL'):monkeypatch.delenv(name,raising=False)
    monkeypatch.setenv('AEGIS_MODEL_DESTINATIONS',json.dumps([{'id':'owned','name':'Owned native recipient','base_env':'OWNED_MODEL_BASE','key_env':'OWNED_MODEL_KEY','lab_http':True,'protocol':'anthropic'}]))
    monkeypatch.setenv('OWNED_MODEL_BASE',peer[0]);monkeypatch.setenv('OWNED_MODEL_KEY','owned-native-secret')
    with TestClient(configured_app(tmp_path,request.param,request,monkeypatch)) as client:
        assert client.post('/api/auth/setup',json={'password':'aegis-test-password-only'}).status_code==200
        client.app.state.event_planner.close();yield client


def test_native_selected_first_planner_and_conversation_preserve_protocol_and_partial_usage(client,peer,monkeypatch):
    profile=create(client,enabled=True,model='owned-native-model').json()['profile']
    created=submit(client,payload(client,profile));assert created.status_code==200,created.text
    task=created.json()['task'];store=client.app.state.store
    monkeypatch.setattr('aegis.engine.completion',completion)
    assert client.app.state.engine.plan(task)==['cookie_policy','security_headers']
    metadata=store.get('tasks',task['id'])['llm_usage'];assert metadata['outcome']=='accepted'
    snapshot=metadata['model_profile_snapshot'];assert snapshot['provider_protocol']=='anthropic' and snapshot['task_model_snapshot']['revision']==1
    assert metadata['tokens']=={'status':'partial','prompt_tokens':5,'completion_tokens':3,'total_tokens':None} and metadata['cost']['amount'] is None
    seed_proofs(store);assert choose(client,profile,'conversation').status_code==200
    monkeypatch.setenv('AEGIS_LLM_CHAT_ENABLED','1');monkeypatch.setattr('aegis.conversation_ai.completion',completion)
    body={'content':'저장 근거','mode':'ai','request_id':'owned-native-chat-001'}
    response=client.post('/api/tasks/chat-task/messages',json=body);assert response.status_code==200,response.text
    assert response.json()['assistant_generation']['outcome']=='accepted'
    assert response.json()['assistant_generation']['model_profile_snapshot']['provider_protocol']=='anthropic'
    assert client.post('/api/tasks/chat-task/messages',json=body).json()==response.json()
    assert len(peer[1])==2 and all(row['path']=='/v1/messages' and row['authorization'] is None and row['api_key']=='owned-native-secret' and row['version']=='2023-06-01' for row in peer[1])
    assert all(row['body']['max_tokens']==4096 and 'system' in row['body'] and 'temperature' not in row['body'] for row in peer[1])
    assert 'owned-native-secret' not in json.dumps([store.all('llm_calls'),metadata,response.json()])
    assert store.get('tasks',task['id'])['status']=='pending' and not store.all('traffic') and store.audit_integrity()['valid']


def test_native_explicit_connection_and_complete_catalog_replay_without_extra_http(client,peer):
    profile=create(client,enabled=True,model='owned-native-model').json()['profile'];base='/api/model-profiles/'+profile['id']
    request={'expected_revision':1,'request_id':'owned-native-check-001'}
    connection=client.post(base+'/connection-test',json=request);assert connection.status_code==200,connection.text
    record=connection.json()['query'];assert record['status']=='completed' and record['tokens']['status']=='partial'
    assert record['profile_snapshot']['provider_protocol']=='anthropic' and record['cost']['amount'] is None
    assert client.post(base+'/connection-test',json=request).json()['query']==record
    catalog=client.post(base+'/catalog',json={**request,'request_id':'owned-native-catalog-001'});assert catalog.status_code==200,catalog.text
    listing=catalog.json()['query'];assert listing['status']=='completed' and listing['models']==['owned-native-model']
    assert client.post(base+'/catalog',json={**request,'request_id':'owned-native-catalog-001'}).json()['query']==listing
    assert [row['path'] for row in peer[1]]==['/v1/messages','/v1/models?limit=256'] and peer[1][0]['body']['max_tokens']==16
    assert all(row['authorization'] is None and row['api_key']=='owned-native-secret' for row in peer[1])
    store=client.app.state.store;assert not store.all('llm_calls') and not store.all('traffic') and store.audit_integrity()['valid']
    assert 'owned-native-secret' not in json.dumps([record,listing])

@pytest.mark.parametrize('configuration,expected',[
    ({'status':302},'provider_status'),({'encoding':'gzip'},'response_encoding'),
    ({'content_type':'text/plain'},'response_content_type'),({'length':1024*1024+1},'response_byte_budget'),
    ({'body':{'type':'message','role':'assistant','stop_reason':'tool_use','content':[{'type':'tool_use','name':'command'}]}},'response_shape'),
    ({'raw':b'{"type":"message","type":"error"}'},'response_shape'),
])
def test_native_connection_refuses_bad_responses_and_never_follows_or_retries(client,peer,configuration,expected):
    profile=create(client,enabled=True,model='owned-native-model').json()['profile'];peer[2].update(configuration)
    response=client.post('/api/model-profiles/'+profile['id']+'/connection-test',json={'expected_revision':1,'request_id':'owned-native-reject-001'})
    assert response.status_code==200,response.text
    assert response.json()['query']['status']=='failed' and response.json()['query']['result_code']==expected
    assert len(peer[1])==1 and not client.app.state.store.all('traffic')


def test_native_incomplete_catalog_is_explicit_failure(client,peer):
    profile=create(client,enabled=True,model='owned-native-model').json()['profile'];peer[2]['body']={'data':[{'id':'owned-native-model'}],'has_more':True}
    response=client.post('/api/model-profiles/'+profile['id']+'/catalog',json={'expected_revision':1,'request_id':'owned-native-incomplete-001'})
    assert response.status_code==200,response.text
    query=response.json()['query'];assert query['status']=='failed' and query['result_code']=='catalog_incomplete' and query['models']==[]
    assert len(peer[1])==1


def test_protocol_change_invalidates_review_before_any_provider_request(client,peer):
    profile=create(client,enabled=True,model='owned-native-model').json()['profile'];assert choose(client,profile).status_code==200
    profiles=client.app.state.model_profiles;choice=profiles.capture('planner')
    profiles.destinations.items['owned'].protocol='openai'
    with pytest.raises(ProfileUnavailable):profiles.guard(choice)
    response=client.post('/api/model-profiles/'+profile['id']+'/connection-test',json={'expected_revision':1,'request_id':'owned-native-change-001'})
    assert response.status_code==409 and peer[1]==[]


def test_native_goal_draft_uses_reviewed_source_task_pin_without_environment_default_key(client,peer,monkeypatch):
    profile=create(client,enabled=True,model='owned-native-model').json()['profile']
    created=submit(client,payload(client,profile));assert created.status_code==200,created.text
    task=created.json()['task'];monkeypatch.setattr('aegis.goal_planner.completion',completion)
    body={'request_id':'d'*32,'mode':'ai','goal':'Owned reviewed cookie configuration goal'}
    path='/api/tasks/'+task['id']+'/goal-plans'
    response=client.post(path,json=body);assert response.status_code==200,response.text
    draft=response.json();assert draft['mode']=='ai' and draft['llm_usage']['outcome']=='accepted'
    reference=draft['llm_usage']['model_profile_snapshot']
    assert reference['provider_protocol']=='anthropic' and reference['task_model_snapshot']['revision']==1
    assert client.post(path,json=body).json()==draft and len(peer[1])==1
    assert peer[1][0]['path']=='/v1/messages' and peer[1][0]['authorization'] is None
    assert not client.app.state.store.all('traffic') and client.app.state.store.get('tasks',task['id'])['status']=='pending'


def test_native_goal_stale_profile_is_rejected_before_draft_and_dispatch(client,peer,monkeypatch):
    profile=create(client,enabled=True,model='owned-native-model').json()['profile']
    task=submit(client,payload(client,profile)).json()['task']
    monkeypatch.setenv('OWNED_MODEL_KEY','owned-native-changed-secret')
    response=client.post('/api/tasks/'+task['id']+'/goal-plans',json={'request_id':'e'*32,'mode':'ai','goal':'Owned goal'})
    assert response.status_code==409 and peer[1]==[]
    assert not client.app.state.store.all('goal_plans') and not client.app.state.store.all('llm_calls')


def test_native_goal_changed_binding_after_capture_has_safe_fallback_and_no_dispatch(client,peer,monkeypatch):
    from aegis import call_ledger
    profile=create(client,enabled=True,model='owned-native-model').json()['profile']
    task=submit(client,payload(client,profile)).json()['task']
    original=call_ledger.start
    def change_after_admission(*args,**kwargs):
        result=original(*args,**kwargs);monkeypatch.setenv('OWNED_MODEL_KEY','owned-native-changed-secret');return result
    monkeypatch.setattr(call_ledger,'start',change_after_admission)
    response=client.post('/api/tasks/'+task['id']+'/goal-plans',json={'request_id':'f'*32,'mode':'ai','goal':'Owned goal'})
    assert response.status_code==200,response.text
    draft=response.json();assert draft['mode']=='rules_fallback' and draft['llm_usage']['outcome']=='request_failed'
    assert draft['llm_usage']['model_profile_snapshot']['provider_protocol']=='anthropic'
    assert peer[1]==[] and not client.app.state.store.all('traffic') and client.app.state.store.audit_integrity()['valid']
