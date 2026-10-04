import pytest
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_store import stores
from tests.test_worker_process import seed
from aegis.worker_process import search_events
from aegis.mcp import Reader,PostgresReader,dispatch


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_workspace_pages_filters_snapshot_and_historical_source(stores,backend,monkeypatch):
    store=stores[backend=='postgres'];source,asset,_=seed(store,30)
    monkeypatch.setattr(store,'all',lambda *_:pytest.fail('Unbounded history'))
    before=store.audit_integrity()
    first=search_events(store,limit=7)
    assert first['total']==90 and len(first['items'])==7 and not first['execution_authorized']
    assert store.audit_integrity()==before
    source_page=search_events(store,task_id=source['id'],asset_id=asset['id'],search='OWNED PROGRESS',limit=7)
    assert source_page['total']==30 and all(r['worker_provenance']['status']=='matched' for r in source_page['items'])
    assert all(r['worker_source']['scope_url']==asset['url'] for r in source_page['items'])
    store.put('assets',{**asset,'url':'https://changed.invalid/','revision':9})
    store.event(source['id'],'New after snapshot',detail={'asset_id':asset['id'],'worker_id':source['id']+':'+asset['id']})
    second=search_events(store,limit=7,offset=7,snapshot=first['snapshot'])
    assert second['total']==90 and len(second['items'])==7
    assert {r['seq'] for r in first['items']}.isdisjoint(r['seq'] for r in second['items'])
    assert search_events(store,task_id=source['id'],search=asset['id'])['total']==31
    assert search_events(store,search="%' OR 1=1 --")['total']==0
    assert store.count('traffic')==0


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_missing_mismatched_and_legacy_worker_sources_are_unconfirmed(stores,backend):
    store=stores[backend=='postgres'];source,asset,_=seed(store,1)
    page=search_events(store)
    assert page['total']==3
    orphan=next(r for r in page['items'] if r['task_id']=='other-task')
    assert not orphan['worker_source']['available'] and orphan['worker_provenance']['status']=='unconfirmed'
    legacy=next(r for r in page['items'] if r['detail']['asset_id']=='other-asset')
    assert legacy['worker_source']['available'] and legacy['worker_provenance']['status']=='unconfirmed'
    for value in (True,1,{},[],None,'','x'*81):
        store.event(source['id'],'Invalid Worker asset',detail={'asset_id':value})
    assert search_events(store)['total']==3
    store.patch('tasks',source['id'],scope_snapshot=[{**asset,'id':'outside'}])
    assert all(not r['worker_source']['available'] for r in search_events(store)['items'])


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_workspace_event_and_source_reads_share_snapshot(stores,backend,monkeypatch):
    store=stores[backend=='postgres'];source,asset,_=seed(store,1)
    original=store.worker_event_page;changed=[]
    def page(**options):
        result=original(**options)
        if not changed:
            changed.append(True)
            store.patch('tasks',source['id'],scope_snapshot=[{**asset,'id':'outside'}])
        return result
    monkeypatch.setattr(store,'worker_event_page',page)
    old=search_events(store,search='Owned progress')
    assert old['items'][0]['worker_source']['available']
    assert old['items'][0]['worker_provenance']['status']=='matched'
    assert not search_events(store,search='Owned progress')['items'][0]['worker_source']['available']


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_readonly_mcp_workspace_search_parity_and_bounds(stores,backend):
    store=stores[backend=='postgres'];source,asset,_=seed(store,1)
    reader=PostgresReader(store._dsn,store.schema) if backend=='postgres' else Reader(store.path)
    before=store.audit_integrity()
    assert reader.call('search_worker_events',{})==search_events(store)
    assert reader.call('search_worker_events',{'task_id':source['id'],'asset_id':asset['id']})['total']==1
    assert store.audit_integrity()==before and store.count('traffic')==0
    for args in ({'limit':True},{'search':'x'*201},{'asset_id':None},{'sql':'SELECT 1'}):
        result=dispatch({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'search_worker_events','arguments':args}},reader)
        assert result['result']['isError']


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_corrupt_task_payload_id_cannot_redirect_search_source(stores,backend):
    import json
    store=stores[backend=='postgres'];source,asset,_=seed(store,1)
    corrupted={**source,'id':'foreign-task'}
    if backend=='sqlite':
        with store.connect() as db:db.execute("UPDATE records SET data=? WHERE kind='tasks' AND id=?",(json.dumps(corrupted),source['id']))
    else:
        with store.transaction(write=True) as db:db.execute("UPDATE records SET data=%s WHERE kind='tasks' AND id=%s",(json.dumps(corrupted),source['id']))
    result=search_events(store,search='Owned progress')['items'][0]
    assert result['worker_source']['task_id']==source['id']
    assert not result['worker_source']['available'] and result['worker_provenance']['status']=='unconfirmed'
