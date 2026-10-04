import time

import pytest
from fastapi.testclient import TestClient
from aegis.store import Store
from aegis.usage import planner_summary
from tests.test_validation import client
from tests.test_identity import add, login


def call(id, status='reported', *, prompt=3, completion=2, total=5, outcome='accepted', at=None):
    return {'id':id,'llm_usage':{'model':'owned-model','observed_at':at or time.time(),
        'outcome':outcome,'tokens':{'status':status,'prompt_tokens':prompt,
                                  'completion_tokens':completion,'total_tokens':total}}}


def test_missing_and_empty_usage_never_looks_like_reported_zero(tmp_path):
    store=Store(tmp_path/'aegis.db')
    empty=planner_summary(store)
    assert empty['calls']==0 and empty['reported_tokens']['total_tokens'] is None
    store.put('tasks',call('missing','missing',prompt=None,completion=None,total=None,outcome='request_failed'))
    result=planner_summary(store)
    assert result['calls']==1 and result['usage_states']['missing']==1
    assert result['reported_tokens']['total_tokens'] is None
    store.put('tasks',call('zero',prompt=0,completion=0,total=0))
    result=planner_summary(store)
    assert result['usage_states']['reported']==1 and result['reported_tokens']['total_tokens']=='0'


def test_only_consistent_reported_usage_is_summed(tmp_path,monkeypatch):
    store=Store(tmp_path/'aegis.db')
    store.put_many([('tasks',row) for row in [call('accepted'),call('rejected',outcome='invalid_plan'),
        call('partial','partial',completion=None,total=None),call('missing','missing',prompt=None,completion=None,total=None),
        call('inconsistent',total=8),call('boolean',prompt=True,total=3),call('unknown','untrusted')]])
    monkeypatch.setattr(store,'all',lambda *args:pytest.fail('Materialized full records'))
    result=planner_summary(store)
    assert result['calls']==7
    assert result['usage_states']=={'reported':2,'partial':1,'missing':1,'invalid':3}
    assert result['reported_tokens']=={'prompt_tokens':'6','completion_tokens':'4','total_tokens':'10'}
    assert result['outcomes']['invalid_plan']==1


def test_exact_sums_exceed_sqlite_and_javascript_integer_ranges(tmp_path):
    store=Store(tmp_path/'aegis.db')
    maximum=9007199254740991
    store.put_many([('tasks',call(str(i),prompt=maximum,completion=0,total=maximum)) for i in range(2100)])
    result=planner_summary(store)
    assert result['reported_tokens']['total_tokens']==str(maximum*2100)
    assert result['usage_states']['reported']==2100


def test_window_excludes_old_future_and_unrecorded_tasks(tmp_path):
    store=Store(tmp_path/'aegis.db')
    now=time.time()
    store.put_many([('tasks',row) for row in [call('now',at=now),call('old',at=now-10*86400),
        call('future',at=now+86400),{'id':'rules-only'}]])
    assert planner_summary(store,7)['calls']==1
    assert planner_summary(store,30)['calls']==2
    assert planner_summary(store)['calls']==2


def test_summary_is_authenticated_readonly_and_does_not_expose_records(client):
    store=client.app.state.store
    row=call('private-task')
    row['llm_usage']['model']='DO-NOT-EXPOSE-MODEL'
    row['secret']='DO-NOT-EXPOSE-PAYLOAD'
    store.put('tasks',row)
    before=store.audit_integrity()
    response=client.get('/api/llm/usage')
    assert response.status_code==200 and response.json()['calls']==1
    assert 'DO-NOT-EXPOSE' not in response.text
    assert store.audit_integrity()==before
    with TestClient(client.app) as anonymous:
        assert anonymous.get('/api/llm/usage').status_code==401
    for role in ('operator','viewer'):
        add(client,role)
        with login(client.app,role) as other:
            assert other.get('/api/llm/usage').status_code==200
    assert client.get('/api/llm/usage?days=7').status_code==200
    assert client.get('/api/llm/usage?days=30').status_code==200
    assert client.get('/api/llm/usage?days=-1').status_code==422
    assert client.get('/api/llm/usage?days=365').status_code==422
