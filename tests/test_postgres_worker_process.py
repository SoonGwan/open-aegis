"""Native PostgreSQL parity, read-only process snapshots and owned execution."""
import pytest
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_store import stores
from tests.test_postgres_engine import plan,wait_task
from tests.test_validation import lab
from tests.test_worker_process import seed
from aegis.worker_process import get_process,collection
from aegis.engine import Engine
from aegis.runtime import ExecutionPolicy
from aegis.coverage import planned_slots


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_process_snapshot_pages_and_task_asset_isolation(stores,backend,monkeypatch):
    store=stores[backend=='postgres'];source,asset,observations=seed(store,30)
    before=store.audit_integrity()
    first=get_process(store,source['id'],asset['id'])
    assert first['events']['total']==first['observations']['total']==30
    for kind in ('events','observations'):
        second=collection(store,source['id'],asset['id'],kind,offset=25,snapshot=first[kind]['snapshot'])
        assert len(second['items'])==5 and 'secret' not in str(second)
    assert collection(store,source['id'],asset['id'],'events',search='progress 29')['total']==1
    assert store.audit_integrity()==before
    original=store.event_page;changed=[]
    def events(*args,**kwargs):
        result=original(*args,**kwargs)
        if not changed:
            changed.append(True)
            store.patch('tasks',source['id'],approved_at=None,status='failed')
            store.patch('observations',observations[-1]['id'],worker_id='altered')
        return result
    monkeypatch.setattr(store,'event_page',events)
    old=get_process(store,source['id'],asset['id'])
    assert old['task_status']=='completed' and all(r['provenance']['status']=='matched' for r in old['observations']['items'])
    new=get_process(store,source['id'],asset['id'])
    assert new['task_status']=='failed' and all(r['provenance']['status']=='unconfirmed' for r in new['observations']['items'])
    assert store.count('traffic')==0


def test_native_readonly_mcp_and_owned_worker_process(stores,lab):
    from aegis.mcp import PostgresReader
    _,store=stores;url,handler=lab
    asset={'id':'owned','name':'Owned lab','url':url,'revision':1,'archived_at':None}
    task=plan('owned-process',asset,checks=['endpoint_inventory','security_headers'])
    store.put_many([('assets',asset),('tasks',task),*[('coverage',r) for r in planned_slots(task)]])
    engine=Engine(store,allow_private=True,policy=ExecutionPolicy(target_rps=20,request_retries=0))
    try:
        engine.start(task['id']);assert wait_task(store,task['id'])['status']=='completed'
        reader=PostgresReader(store._dsn,store.schema);before=store.audit_integrity()
        args={'id':task['id'],'asset_id':asset['id']}
        process=reader.call('get_worker',args)
        assert all(r['status']=='completed' for r in process['coverage'])
        assert all(r['worker_provenance']['status']=='matched' for r in process['events']['items'])
        assert reader.call('list_worker_observations',args)['items'][0]['provenance']['status']=='matched'
        assert reader.call('list_worker_events',{**args,'search':'Worker 종료'})['total']==1
        assert store.audit_integrity()==before and handler.requests==['/']
    finally:engine.shutdown()


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_worker_event_filter_requires_string_asset_identity(stores,backend):
    store=stores[backend=='postgres'];source,asset,_=seed(store,1)
    scope={**asset,'id':'true'}
    store.patch('tasks',source['id'],scope_snapshot=[scope])
    store.event(source['id'],'Boolean should not match',detail={'asset_id':True})
    store.event(source['id'],'String identity',detail={'asset_id':'true','worker_id':source['id']+':true'})
    result=collection(store,source['id'],'true','events')
    assert result['total']==1 and result['items'][0]['message']=='String identity'


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_corrupt_payload_task_id_never_redirects_process(stores,backend):
    import json
    from aegis.worker_process import WorkerMissing
    store=stores[backend=='postgres'];source,asset,_=seed(store,1)
    altered={**source,'id':'other-task'}
    if backend=='sqlite':
        with store.connect() as db:db.execute("UPDATE records SET data=? WHERE kind='tasks' AND id=?",(json.dumps(altered),source['id']))
    else:
        with store.transaction(write=True) as db:db.execute("UPDATE records SET data=%s WHERE kind='tasks' AND id=%s",(json.dumps(altered),source['id']))
    with pytest.raises(WorkerMissing):get_process(store,source['id'],asset['id'])
