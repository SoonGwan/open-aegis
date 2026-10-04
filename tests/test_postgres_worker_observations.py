"""Native source snapshots and actual owned Worker history."""
import pytest
from aegis.worker_observations import task_page
from aegis.engine import Engine
from aegis.runtime import ExecutionPolicy
from aegis.coverage import planned_slots
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_store import stores
from tests.test_postgres_engine import plan,wait_task
from tests.test_validation import lab
from tests.test_worker_observations import populate


def test_native_repeated_owned_execution_keeps_both_sources(stores,lab):
    _,pg=stores;url,handler=lab
    asset={'id':'owned','name':'Owned lab','url':url,'revision':1,'archived_at':None}
    tasks=[plan(id,asset,checks=['endpoint_inventory']) for id in ('first','second')]
    pg.put_many([('assets',asset),*[('tasks',task) for task in tasks],
                 *[('coverage',row) for task in tasks for row in planned_slots(task)]])
    engine=Engine(pg,allow_private=True,policy=ExecutionPolicy(target_rps=20,request_retries=0))
    try:
        for task in tasks:
            engine.start(task['id']);assert wait_task(pg,task['id'])['status']=='completed'
        pages=[task_page(pg,task['id']) for task in tasks]
        assert all(page['total']==1 and page['items'][0]['provenance']['status']=='matched' for page in pages)
        assert pages[0]['items'][0]['id']!=pages[1]['items'][0]['id']
        assert handler.requests==['/','/']
    finally:engine.shutdown()


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_both_backends_paged_snapshot_and_historical_scope(stores,backend,monkeypatch):
    store=stores[backend=='postgres'];source,asset,records=populate(store,60)
    first=task_page(store,source['id']);assert first['total']==60 and len(first['items'])==25
    store.patch('assets',asset['id'],revision=2,url='https://changed.example.invalid/')
    second=task_page(store,source['id'],offset=25,snapshot=first['snapshot'])
    assert all(row['provenance']['status']=='matched' for row in second['items'])
    original=store.page;changed=[]
    def page(*args,**kwargs):
        result=original(*args,**kwargs)
        if not changed:
            changed.append(True);store.patch('tasks',source['id'],approved_at=None)
        return result
    monkeypatch.setattr(store,'page',page)
    assert task_page(store,source['id'])['items'][0]['provenance']['status']=='matched'
    assert task_page(store,source['id'])['items'][0]['provenance']['status']=='unconfirmed'
    assert store.count('traffic')==0


def test_native_readonly_mcp_observation_page(stores):
    from aegis.mcp import PostgresReader
    _,pg=stores;source,_,_=populate(pg,30)
    reader=PostgresReader(pg._dsn,pg.schema)
    before=pg.audit_integrity()
    result=reader.call('list_task_observations',{'id':source['id']})
    assert result['total']==30 and len(result['items'])==25
    assert all(row['provenance']['status']=='matched' for row in result['items'])
    assert pg.audit_integrity()==before and pg.count('traffic')==0
