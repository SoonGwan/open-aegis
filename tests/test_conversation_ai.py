import json
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from tests.test_validation import client
from tests.test_conversation import seed_proofs


@pytest.fixture
def ai(client,monkeypatch):
    seed_proofs(client.app.state.store)
    monkeypatch.setenv('AEGIS_LLM_CHAT_ENABLED','1')
    monkeypatch.setenv('AEGIS_LLM_MODEL','owned-ai-model')
    monkeypatch.setenv('AEGIS_LLM_API_KEY','owned-secret-must-not-persist')
    calls=[]
    def provider(base,key,payload,**kwargs):
        assert key=='owned-secret-must-not-persist'
        calls.append(payload)
        return {'choices':[{'message':{'content':json.dumps({'blocks':[
            {'text':'관찰 기록에서 CSP 부재를 확인했습니다.','citations':['증거 1','발견 1']}]})}}],
            'usage':{'prompt_tokens':12,'completion_tokens':8,'total_tokens':20,'secret':key}}
    monkeypatch.setattr('aegis.conversation_ai.completion',provider)
    return calls,provider


PATH='/api/tasks/chat-task/messages'
PAYLOAD={'content':'기록 요약','mode':'ai','request_id':'owned-ai-request-0001'}


def test_ai_citations_usage_audit_atomicity_and_retry(client,ai):
    calls,_=ai
    response=client.post(PATH,json=PAYLOAD)
    assert response.status_code==200
    reply=response.json()
    assert reply['provenance']['mode']=='recorded_ai'
    assert '[증거 1, 발견 1]' in reply['content'] and 'AI 초안' in reply['content']
    assert reply['assistant_generation']['outcome']=='accepted'
    assert reply['assistant_generation']['tokens']['total_tokens']==20
    events=client.app.state.store.events(task_id='chat-task')
    assert len(events)==1 and events[0]['detail']==reply['assistant_generation']
    assert 'owned-secret-must-not-persist' not in json.dumps([reply,events])
    client.app.state.store.patch('evidence','owned-proof',observation={'changed':True})
    assert client.post(PATH,json=PAYLOAD).json()==reply and len(calls)==1
    usage=client.get('/api/llm/usage?source=conversation').json()
    assert usage['calls']==1 and usage['reported_tokens']['total_tokens']=='20'
    assert client.post(PATH,json={**PAYLOAD,'mode':'rules'}).status_code==409
    assert client.get(PATH+'/page').json()['total']==2
    assert client.get('/api/settings').json()['llm_chat_configured'] is True
    prompt=json.loads(calls[0]['messages'][1]['content'])
    assert set(prompt['sources'])=={'작업','발견 1','증거 1'}
    assert 'owned-fingerprint' not in json.dumps(prompt)


@pytest.mark.parametrize('answer',[
    {'blocks':[{'text':'bad','citations':['foreign-task']}]},
    {'blocks':[{'text':'owned-secret-must-not-persist','citations':['작업']}]},
    {'blocks':[{'text':'bad','citations':[]}]},
    {'blocks':[{'text':'bad','citations':['작업'],'execute':'command'}]},
    {'blocks':[{'text':'x'*1501,'citations':['작업']}]},
    {'blocks':[]}, {'blocks':True}, {'blocks':[{'text':' ','citations':['작업']}]},
    {'blocks':[{'text':'bad','citations':[{}]}]}, {'blocks':[],'actions':['run']},
])
def test_rejected_drafts_fall_back_without_persisting_provider_text(client,ai,monkeypatch,answer):
    monkeypatch.setattr('aegis.conversation_ai.completion',lambda *a,**k:{
        'choices':[{'message':{'content':json.dumps(answer)}}],
        'usage':{'prompt_tokens':3,'completion_tokens':2,'total_tokens':5}})
    reply=client.post(PATH,json=PAYLOAD).json()
    assert reply['provenance']['mode']=='recorded_rules'
    assert reply['assistant_generation']['outcome']=='invalid_answer'
    assert reply['assistant_generation']['tokens']['status']=='reported'
    assert '규칙 기반 요약으로 복구' in reply['content']
    assert 'foreign-task' not in json.dumps(reply)
    assert 'owned-secret-must-not-persist' not in json.dumps(reply)


def test_failure_and_missing_configuration_are_explicit(client,ai,monkeypatch):
    def fail(*a,**k): raise ValueError('owned-secret-must-not-persist')
    monkeypatch.setattr('aegis.conversation_ai.completion',fail)
    reply=client.post(PATH,json=PAYLOAD).json()
    assert reply['assistant_generation']['outcome']=='request_failed'
    assert reply['assistant_generation']['tokens']['total_tokens'] is None
    assert 'owned-secret-must-not-persist' not in json.dumps(reply)
    monkeypatch.delenv('AEGIS_LLM_CHAT_ENABLED')
    assert client.post(PATH,json=PAYLOAD).json()==reply
    assert client.post(PATH,json={**PAYLOAD,'request_id':'new-owned-request-0001'}).status_code==409
    assert client.post(PATH,json={'content':'no id','mode':'ai'}).status_code==422


def test_ai_pair_and_usage_roll_back_when_audit_fails(client,ai,monkeypatch):
    def fail(*a): raise RuntimeError('owned audit failure')
    monkeypatch.setattr('aegis.store.append_event',fail)
    with pytest.raises(RuntimeError,match='owned audit failure'):
        client.post(PATH,json=PAYLOAD)
    assert client.app.state.store.page('messages',filters={'task_id':'chat-task'})['total']==0
    assert client.get('/api/llm/usage?source=all').json()['calls']==0


def test_ai_admission_and_same_request_retry_make_one_provider_call(client,ai,monkeypatch):
    calls,provider=ai
    entered=threading.Event(); release=threading.Event()
    def held(*a,**k):
        entered.set()
        assert release.wait(5)
        return provider(*a,**k)
    monkeypatch.setattr('aegis.conversation_ai.completion',held)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first=pool.submit(client.post,PATH,json=PAYLOAD)
        assert entered.wait(3)
        try:
            rejected=client.post(PATH,json=PAYLOAD)
            assert rejected.status_code==429 and rejected.headers['Retry-After']=='2'
        finally:
            release.set()
        reply=first.result().json()
    assert client.post(PATH,json=PAYLOAD).json()==reply and len(calls)==1


def test_revoked_session_during_provider_call_cannot_commit_reply(client,ai,monkeypatch):
    _,provider=ai
    def revoked(*a,**k):
        client.app.state.store.logout(client.cookies.get('aegis_session'))
        return provider(*a,**k)
    monkeypatch.setattr('aegis.conversation_ai.completion',revoked)
    assert client.post(PATH,json=PAYLOAD).status_code==401
    assert client.app.state.store.page('messages',filters={'task_id':'chat-task'})['total']==0


def test_real_lab_provider_post(client,ai,monkeypatch):
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from aegis.llm import completion
    seen=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            seen.append((self.path,self.headers['Authorization'],payload))
            output={'choices':[{'message':{'content':json.dumps({'blocks':[
                {'text':'저장된 관찰을 검토하세요.','citations':['증거 1']}]})}}]}
            body=json.dumps(output).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(body)))
            self.end_headers();self.wfile.write(body)
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    monkeypatch.setenv('AEGIS_LLM_BASE_URL',f'http://127.0.0.1:{server.server_port}/v1')
    monkeypatch.setattr('aegis.conversation_ai.completion',completion)
    try:
        reply=client.post(PATH,json=PAYLOAD).json()
        assert reply['assistant_generation']['outcome']=='accepted'
        assert reply['assistant_generation']['tokens']['status']=='missing'
        assert seen[0][0]=='/v1/chat/completions'
        assert seen[0][1]=='Bearer owned-secret-must-not-persist'
        assert client.app.state.store.count('traffic')==0
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)


def test_context_limit_and_role_downgrade_prevent_call_or_commit(client,ai,monkeypatch):
    calls,provider=ai
    store=client.app.state.store
    store.patch('findings','cited-finding',remediation='긴'*30000)
    assert client.post(PATH,json={**PAYLOAD,'content':'조치'}).status_code==413
    assert not calls
    def downgraded(*a,**k):
        user=store.session_user(client.cookies.get('aegis_session'))
        store.update_user(user['id'],role='viewer')
        return provider(*a,**k)
    monkeypatch.setattr('aegis.conversation_ai.completion',downgraded)
    # Update revokes all sessions before the final write reauthentication.
    assert client.post(PATH,json=PAYLOAD).status_code==401
    assert store.page('messages',filters={'task_id':'chat-task'})['total']==0


def test_rules_request_racing_ai_mode_gets_conflict_without_overwriting(client,ai,monkeypatch):
    _,provider=ai
    def raced(*a,**k):
        assert client.post(PATH,json={**PAYLOAD,'mode':'rules'}).status_code==200
        return provider(*a,**k)
    monkeypatch.setattr('aegis.conversation_ai.completion',raced)
    assert client.post(PATH,json=PAYLOAD).status_code==409
    messages=client.app.state.store.page('messages',filters={'task_id':'chat-task'})
    assert messages['total']==2
    assert next(m for m in messages['items'] if m['role']=='assistant')['provenance']['mode']=='recorded_rules'
