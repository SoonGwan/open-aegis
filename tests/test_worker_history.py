import pytest
from tests.test_validation import client
from tests.test_worker_process import seed


def test_http_workspace_worker_history_auth_bounds_and_no_execution(client,monkeypatch):
    store=client.app.state.store;source,asset,_=seed(store,30)
    monkeypatch.setattr(store,'all',lambda *_:pytest.fail('Unbounded read'))
    before=store.audit_integrity()
    result=client.get('/api/worker-events').json()
    assert result['total']==90 and len(result['items'])==25 and not result['execution_authorized']
    assert 'Planner process secret' not in str(result)
    matched=client.get('/api/worker-events',params={'search':'progress 29'}).json()
    assert matched['total']==1 and matched['items'][0]['worker_provenance']['status']=='matched'
    assert matched['items'][0]['worker_source']['scope_url']==asset['url']
    assert client.get('/api/worker-events',params={'task_id':source['id'],'asset_id':asset['id']}).json()['total']==30
    for params in ({'limit':101},{'offset':-1},{'offset':10000001},{'snapshot':-1},{'search':'x'*201},{'task_id':''},{'asset_id':'x'*81}):
        assert client.get('/api/worker-events',params=params).status_code==422
    assert store.audit_integrity()==before and store.count('traffic')==0
    client.post('/api/auth/logout')
    assert client.get('/api/worker-events').status_code==401


def test_viewer_and_operator_can_search_but_cannot_write_worker_history(client):
    from tests.test_identity import add,login
    seed(client.app.state.store,1)
    for role in ('viewer','operator'):
        user=add(client,role)
        with login(client.app,user['username']) as read:
            assert read.get('/api/worker-events').json()['total']==3
            assert read.post('/api/worker-events').status_code==405
