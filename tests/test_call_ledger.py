import time
import pytest
from fastapi.testclient import TestClient
from aegis import call_ledger
from aegis.store import Store
from aegis.llm import token_usage
from aegis.costs import estimate
from aegis.usage import usage_summary
from tests.test_validation import client
from tests.test_conversation_ai import ai, PATH, PAYLOAD
from tests.test_identity import add, login


def test_revoked_session_retains_attempt_usage_without_saving_answer(client,ai,monkeypatch):
    _,provider=ai
    def revoke(*args,**kwargs):
        client.app.state.store.logout(client.cookies.get('aegis_session'))
        return provider(*args,**kwargs)
    monkeypatch.setattr('aegis.conversation_ai.completion',revoke)
    assert client.post(PATH,json=PAYLOAD).status_code==401
    store=client.app.state.store
    assert store.page('messages',filters={'task_id':'chat-task'})['total']==0
    assert usage_summary(store,source='all')['calls']==0
    summary=usage_summary(store,source='all',ledger='attempts')
    assert summary['calls']==1 and summary['attempt_states']['uncommitted']==1
    assert summary['reported_tokens']['total_tokens']=='20'
    assert store.audit_integrity()['valid'] is True


def test_final_audit_failure_keeps_observation_and_atomic_pair_rollback(client,ai,monkeypatch):
    import aegis.store
    original=aegis.store.append_event
    def fail_final(db,entry):
        if entry[3]=='AI 대화 호출 결과':
            raise RuntimeError('Owned final audit failure')
        return original(db,entry)
    monkeypatch.setattr('aegis.store.append_event',fail_final)
    with pytest.raises(RuntimeError,match='final audit'):
        client.post(PATH,json=PAYLOAD)
    store=client.app.state.store
    assert store.page('messages',filters={'task_id':'chat-task'})['total']==0
    row=store.page('llm_calls')['items'][0]
    assert row['state']=='uncommitted' and row['tokens']['total_tokens']==20
    assert store.audit_integrity()['valid'] is True


def test_success_retry_is_one_attempt_and_same_request_failed_retry_is_new_attempt(client,ai,monkeypatch):
    calls,_=ai
    store=client.app.state.store
    original=store.put_message_exchange
    monkeypatch.setattr(store,'put_message_exchange',lambda *a: (_ for _ in ()).throw(RuntimeError('Owned write failure')))
    with pytest.raises(RuntimeError): client.post(PATH,json=PAYLOAD)
    monkeypatch.setattr(store,'put_message_exchange',original)
    reply=client.post(PATH,json=PAYLOAD).json()
    assert client.post(PATH,json=PAYLOAD).json()==reply
    assert len(calls)==2
    summary=client.get('/api/llm/usage?source=all&ledger=attempts').json()
    assert summary['calls']==2 and summary['reported_tokens']['total_tokens']=='40'
    assert summary['attempt_states']['committed']==1 and summary['attempt_states']['uncommitted']==1
    assert client.get('/api/llm/usage?source=all').json()['calls']==1


def test_start_audit_failure_prevents_provider_call(client,ai,monkeypatch):
    calls,_=ai
    monkeypatch.setattr('aegis.call_ledger.append_event',lambda *a: (_ for _ in ()).throw(RuntimeError('Owned start failure')))
    with pytest.raises(RuntimeError): client.post(PATH,json=PAYLOAD)
    assert not calls and client.app.state.store.count('llm_calls')==0


def test_recovery_preserves_observed_usage_and_is_idempotent(tmp_path):
    store=Store(tmp_path/'aegis.db')
    at=time.time();price={'status':'unconfigured','quote':None}
    first=call_ledger.start(store,'planner','owned','owned-model','https://provider.invalid/v1',at,price)
    second=call_ledger.start(store,'planner','owned','owned-model','https://provider.invalid/v1',at,price)
    tokens=token_usage({'prompt_tokens':3,'completion_tokens':2,'total_tokens':5})
    detail={'call_id':second,'model':'owned-model','started_at':at,'observed_at':time.time(),
            'outcome':'accepted','tokens':tokens,'cost':estimate(tokens,price,at)}
    call_ledger.observe(store,second,detail)
    call_ledger.recover(store)
    assert store.get('llm_calls',first)['state']=='interrupted'
    assert store.get('llm_calls',second)['tokens']==tokens
    summary=usage_summary(store,source='all',ledger='attempts')
    assert summary['calls']==2 and summary['attempt_states']['interrupted']==2
    assert summary['reported_tokens']['total_tokens']=='5' and summary['usage_states']['missing']==1
    before=store.audit_integrity()
    call_ledger.recover(store)
    assert store.audit_integrity()==before


def test_ledger_page_auth_filters_watermark_and_private_content_absent(client,ai):
    reply=client.post(PATH,json=PAYLOAD).json()
    response=client.get('/api/llm/calls?source=conversation&state=committed&task_id=chat-task')
    row=response.json()['items'][0]
    assert row['id']==reply['assistant_generation']['call_id'] and row['record_id']==reply['id']
    assert 'owned-secret-must-not-persist' not in response.text and PAYLOAD['content'] not in response.text
    snapshot=response.json()['snapshot']
    client.post(PATH,json={**PAYLOAD,'request_id':'owned-second-request-0001'})
    assert client.get('/api/llm/calls',params={'snapshot':snapshot}).json()['total']==1
    assert client.get('/api/llm/calls?search='+row['id']).json()['total']==1
    assert client.get('/api/llm/calls?source=planner').json()['total']==0
    assert client.get('/api/llm/calls?state=unknown').status_code==422
    assert client.get('/api/llm/usage?ledger=unknown').status_code==422
    with TestClient(client.app) as anonymous:
        assert anonymous.get('/api/llm/calls').status_code==401
    for role in ('operator','viewer'):
        add(client,role)
        with login(client.app,role) as other:
            assert other.get('/api/llm/calls').json()['total']==2
