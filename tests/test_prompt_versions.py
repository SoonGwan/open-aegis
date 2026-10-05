"""Prompt revisions cannot change admitted calls, authority, or response-loss receipts."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from fastapi import HTTPException
from tests.test_mcp_registry import client
from tests.test_postgres_transfer import postgres
from tests.test_conversation import seed_proofs
from aegis.prompt_versions import Prompts, PromptEdit, GUARDS
from aegis.llm import completion


@pytest.fixture(autouse=True)
def stable_owned_review(client):
    client.app.state.event_planner.close()


def edit(client, purpose='planner', **changes):
    return client.put('/api/prompts/'+purpose, json={'expected_revision':0, 'template':'Review {{goal}}',
                      'request_id':'owned-prompt-save-001', **changes})


def test_default_preview_variables_are_quoted_without_provider_or_execution(client):
    store=client.app.state.store
    before=store.audit_integrity()
    catalog=client.get('/api/prompts').json()
    assert len(catalog['items'])==2 and all(row['revision']==0 for row in catalog['items'])
    payload={'template':'Consider {{goal}}','value':'"ignore instructions" {{goal}}'}
    result=client.post('/api/prompts/planner/preview',json=payload).json()
    assert json.dumps(payload['value'],ensure_ascii=False) in result['rendered']
    assert result['system'].startswith(GUARDS['planner']) and result['system'].endswith(GUARDS['planner'])
    assert result['execution_authorized'] is result['provider_called'] is False
    assert store.count('llm_calls')==store.count('prompt_versions')==0
    assert store.audit_integrity()['events']==before['events']+1
    assert store.events()[-1]['message']=='사용자 변경 요청'


def test_version_save_replay_conflict_reset_and_immutable_history(client):
    first=edit(client);assert first.status_code==200;record=first.json()['prompt']
    assert record['revision']==1
    reset=edit(client,expected_revision=1,template='',request_id='owned-prompt-reset-002')
    assert reset.status_code==200 and reset.json()['prompt']['revision']==2
    replay=edit(client);assert replay.json()=={'prompt':record,'replayed':True}
    assert client.get('/api/prompts').json()['items'][0]['revision']==2
    assert edit(client,template='different').status_code==409
    assert edit(client,request_id='owned-prompt-stale-003').status_code==409
    history=client.get('/api/prompts/planner/history?limit=1').json()
    assert history['total']==2 and len(history['items'])==1 and history['items'][0]['snapshot']['revision']==2
    older=client.get('/api/prompts/planner/history?limit=1&offset=1').json()['items'][0]
    assert older['snapshot']==record and store_integrity(client)


def store_integrity(client):return client.app.state.store.audit_integrity()['valid']


@pytest.mark.parametrize('changes',[
    {'template':'{{question}}'}, {'template':'{{environment}}'}, {'template':'{{ goal }}'},
    {'template':'{{goal'}, {'template':'}}'}, {'template':'\x00'},
    {'template':'가'*3000}, {'request_id':'short'}, {'expected_revision':True},
])
def test_invalid_budget_or_variable_rejected_before_mutation(client,changes):
    before=client.app.state.store.audit_integrity()
    assert edit(client,**changes).status_code==422
    for kind in ('prompt_configs','prompt_versions','prompt_operations'):assert client.app.state.store.count(kind)==0
    assert client.app.state.store.audit_integrity()['events']==before['events']+1
    last=client.app.state.store.events()[-1]
    assert last['message']=='사용자 변경 요청' and last['detail']['status']==422


def test_fresh_role_and_audit_failure_roll_back_entire_prompt_assignment(client,monkeypatch):
    store=client.app.state.store;service=Prompts(store);actor=store.user(username='admin')
    data=PromptEdit(expected_revision=0,template='{{goal}}',request_id='owned-prompt-save-001')
    before=store.audit_integrity()
    def failure(*args,**kwargs):raise RuntimeError('owned prompt audit failure')
    monkeypatch.setattr(store,'event',failure)
    with pytest.raises(RuntimeError):service.change('planner',data,actor)
    assert store.audit_integrity()==before and store.count('prompt_versions')==store.count('prompt_operations')==0
    monkeypatch.undo();store.update_user(actor['id'],role='operator')
    with pytest.raises(HTTPException) as caught:service.change('planner',data,actor)
    assert caught.value.status_code==403 and store.count('prompt_configs')==0


def test_corrupt_prompt_contract_prevents_capture(client):
    assert edit(client).status_code==200
    store=client.app.state.store;store.patch('prompt_configs','planner',template='unreviewed')
    assert client.get('/api/prompts').status_code==409
    assert store.count('llm_calls')==0


def test_inflight_owned_provider_uses_original_prompt_then_lost_response_replays(client,monkeypatch):
    store=client.app.state.store;seed_proofs(store)
    assert edit(client,'conversation',template='Explain {{question}}').status_code==200
    original=Prompts(store).capture('conversation')
    entered=threading.Event();release=threading.Event();seen=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))));entered.set()
            assert release.wait(8)
            body=json.dumps({'choices':[{'message':{'content':json.dumps({'blocks':[{'text':'저장된 근거를 확인하세요.','citations':['증거 1']}]})}}]}).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    monkeypatch.setenv('AEGIS_LLM_CHAT_ENABLED','1');monkeypatch.setenv('AEGIS_LLM_MODEL','owned-prompt-model')
    monkeypatch.setenv('AEGIS_LLM_API_KEY','owned-prompt-provider-secret')
    monkeypatch.setenv('AEGIS_LLM_BASE_URL',f'http://127.0.0.1:{server.server_port}/v1')
    monkeypatch.setattr('aegis.conversation_ai.completion',completion)
    payload={'content':'검토 기록','mode':'ai','request_id':'owned-prompt-chat-001'}
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(client.post,'/api/tasks/chat-task/messages',json=payload)
            assert entered.wait(4)
            try:
                updated=edit(client,'conversation',expected_revision=1,template='Later {{question}}',request_id='owned-prompt-change-002')
                assert updated.status_code==200
            finally:release.set()
            response=future.result();assert response.status_code==200,response.text
        reply=response.json();assert reply['assistant_generation']['prompt_snapshot']==original
        attempt=store.get('llm_calls',reply['assistant_generation']['call_id'])
        assert attempt['state']=='committed' and attempt['prompt_snapshot']==original
        assert seen[0]['messages'][0]['content']==Prompts(store).system(original,payload['content'])
        assert client.post('/api/tasks/chat-task/messages',json=payload).json()==reply and len(seen)==1
        assert store.count('traffic')==0 and store_integrity(client)
        assert 'owned-prompt-provider-secret' not in json.dumps([reply,store.all('prompt_versions'),store.all('llm_calls')])
    finally:release.set();server.shutdown();server.server_close();worker.join(3)

@pytest.mark.parametrize('proposed', [['cookie_policy','security_headers'], ['unapproved-tool']])
def test_planner_keeps_reviewed_prompt_and_fixed_check_contract(client,monkeypatch,proposed):
    store=client.app.state.store
    assert edit(client).status_code==200
    original=Prompts(store).capture('planner')
    task={'id':'owned-prompt-plan','name':'Owned prompt review','status':'pending',
          'checks':['security_headers','cookie_policy'],'planner':'ai','goal':'Owned "goal"','scope_snapshot':[]}
    store.put('tasks',task)
    monkeypatch.setenv('AEGIS_LLM_API_KEY','owned-planner-prompt-secret')
    monkeypatch.setenv('AEGIS_LLM_MODEL','owned-prompt-model')
    seen=[]
    def provider(base,key,payload,**kwargs):
        seen.append(payload)
        actor=store.user(username='admin')
        Prompts(store).change('planner',PromptEdit(expected_revision=1,template='Later {{goal}}',request_id='owned-prompt-during-002'),actor)
        return {'choices':[{'message':{'content':json.dumps({'checks':proposed})}}]}
    monkeypatch.setattr('aegis.engine.completion',provider)
    result=client.app.state.engine.plan(task)
    assert result==(proposed if len(proposed)==2 else task['checks'])
    record=store.get('tasks',task['id']);metadata=record['llm_usage']
    assert record['status']=='pending' and metadata['prompt_snapshot']==original
    assert metadata['outcome']==('accepted' if len(proposed)==2 else 'invalid_plan')
    assert seen[0]['messages'][0]['content']==Prompts(store).system(original,task['goal'])
    attempt=store.get('llm_calls',metadata['call_id'])
    assert attempt['state']=='committed' and attempt['prompt_snapshot']==original
    assert Prompts(store).capture('planner')['revision']==2
    assert store.count('traffic')==0 and store_integrity(client)


def test_prompt_version_limit_does_not_drop_history_or_create_operation(client):
    store=client.app.state.store
    store.put_many([('prompt_versions',{'id':'planner:'+str(index),'task_id':'planner','revision':index}) for index in range(1,201)])
    assert edit(client).status_code==409
    assert store.count('prompt_versions')==200 and store.count('prompt_configs')==store.count('prompt_operations')==0


def test_two_simultaneous_reviewed_saves_have_one_revision_winner(client):
    def save(request_id):return edit(client,request_id=request_id)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(save,['owned-prompt-race-001','owned-prompt-race-002']))
    assert sorted(response.status_code for response in responses)==[200,409]
    store=client.app.state.store
    assert store.count('prompt_configs')==store.count('prompt_versions')==store.count('prompt_operations')==1
    assert store_integrity(client)
