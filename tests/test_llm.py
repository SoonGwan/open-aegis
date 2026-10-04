import pytest
from aegis.llm import completion
from aegis.llm import token_usage


@pytest.mark.parametrize('raw,status', [
    (None,'missing'), ({},'missing'), ({'provider_secret':'discard-me'},'missing'),
    ({'prompt_tokens':3},'partial'),
    ({'prompt_tokens':0,'completion_tokens':0,'total_tokens':0},'reported'),
    ({'prompt_tokens':3,'completion_tokens':2,'total_tokens':5},'reported'),
    ({'prompt_tokens':3,'completion_tokens':2,'total_tokens':6},'invalid'),
    ({'prompt_tokens':True},'invalid'), ({'prompt_tokens':-1},'invalid'),
    ({'prompt_tokens':'3'},'invalid'), ({'prompt_tokens':3.5},'invalid'),
    ({'prompt_tokens':9007199254740992},'invalid'), (['discard-me'],'invalid'),
])
def test_provider_usage_is_explicit_and_bounded(raw,status):
    result = token_usage(raw)
    assert result['status'] == status
    assert set(result) == {'status','prompt_tokens','completion_tokens','total_tokens'}
    if status == 'missing':
        assert result['total_tokens'] is None
    if status == 'partial':
        assert result['prompt_tokens'] == 3 and result['total_tokens'] is None
    assert 'discard-me' not in str(result)


@pytest.mark.parametrize('outcome', ['accepted','invalid_plan','request_failed'])
def test_planner_keeps_usage_even_when_plan_is_rejected(tmp_path,monkeypatch,outcome):
    import json
    from aegis.engine import Engine
    from aegis.store import Store
    monkeypatch.setenv('AEGIS_LLM_API_KEY','synthetic-provider-secret')
    monkeypatch.setenv('AEGIS_LLM_MODEL','synthetic-model')
    store=Store(tmp_path/'aegis.db')
    task={'id':'owned-plan','status':'pending','checks':['security_headers','cookie_policy'],
          'planner':'ai','goal':'Owned fixture','scope_snapshot':[]}
    store.put('tasks',task)
    def provider(*args,**kwargs):
        if outcome == 'request_failed':
            raise ValueError('synthetic-provider-secret')
        return {'choices':[{'message':{'content':json.dumps({'checks':
            ['cookie_policy','security_headers'] if outcome == 'accepted' else ['unapproved-tool']})}}],
            'usage':{'prompt_tokens':3,'completion_tokens':2,'total_tokens':5,
                     'secret':'synthetic-provider-secret','arbitrary_body':'discard-me'}}
    monkeypatch.setattr('aegis.engine.completion',provider)
    engine=Engine(store)
    try:
        plan=engine.plan(task)
        assert plan == (['cookie_policy','security_headers'] if outcome == 'accepted' else task['checks'])
        metadata=store.get('tasks',task['id'])['llm_usage']
        assert metadata['outcome'] == outcome
        assert metadata['tokens']['status'] == ('missing' if outcome == 'request_failed' else 'reported')
        events=store.events(task_id=task['id'])
        assert len(events) == 1 and events[0]['detail'] == metadata
        assert 'synthetic-provider-secret' not in json.dumps([metadata,events])
        assert 'discard-me' not in json.dumps([metadata,events])
    finally:
        engine.shutdown()


def test_usage_and_audit_commit_roll_back_together(tmp_path,monkeypatch):
    from aegis.store import Store
    store=Store(tmp_path/'aegis.db')
    store.put('tasks',{'id':'owned-plan','status':'pending'})
    def fail(*args):
        raise RuntimeError('owned audit failure')
    monkeypatch.setattr('aegis.store.append_event',fail)
    with pytest.raises(RuntimeError):
        store.record_planner_call('owned-plan', {'tokens':token_usage(None)},'fixture','info')
    assert 'llm_usage' not in store.get('tasks','owned-plan')
    assert not store.events(task_id='owned-plan')


def test_provider_credentials_never_follow_redirect():
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.error import HTTPError
    calls=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            calls.append(self.path)
            self.send_response(302)
            self.send_header('Location','/capture')
            self.end_headers()
        def do_GET(self):
            calls.append(self.path)
            self.send_response(200)
            self.end_headers()
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        with pytest.raises(HTTPError):
            completion(f'http://127.0.0.1:{server.server_port}/v1','fixture-key',{},allow_local=True)
        assert calls == ['/v1/chat/completions']
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_provider_plaintext_rejected_before_network():
    with pytest.raises(ValueError,match='HTTPS'):
        completion('http://provider.invalid/v1','fixture-key',{})


def test_provider_response_size_is_bounded():
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(200)
            self.send_header('Content-Length',str(1024*1024+1))
            self.end_headers()
            self.wfile.write(b'x'*(1024*1024+1))
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pytest.raises(ValueError,match='size budget'):
            completion(f'http://127.0.0.1:{server.server_port}/v1','fixture-key',{},allow_local=True)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
