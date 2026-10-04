"""Process reads preserve task/asset boundaries, incomplete evidence and one snapshot."""
import pytest
from tests.test_validation import client, lab, register, task, finish
from tests.test_worker_observations import populate
from aegis.coverage import planned_slots
from aegis.worker_process import get_process, collection


def seed(store, count=30):
    source, asset, observations = populate(store, count)
    other = {**asset, 'id': 'other-asset', 'name': 'Other worker'}
    source.update(created_at=1., status='completed', scope_snapshot=[asset, other])
    store.put('tasks', source)
    store.put_many([('coverage', {**row, 'status': 'completed'}) for row in planned_slots(source)])
    for i in range(count):
        store.event(source['id'], f'Owned progress {i}', detail={'asset_id': asset['id'], 'worker_id': source['id']+':'+asset['id']})
        store.event(source['id'], 'Other worker secret', detail={'asset_id': other['id']})
        store.event('other-task', 'Other task secret', detail={'asset_id': asset['id']})
    store.event(source['id'], 'Planner process secret')
    return source, asset, observations


def test_http_worker_process_pages_scope_and_no_execution(client, monkeypatch):
    store=client.app.state.store;source,asset,observations=seed(store)
    monkeypatch.setattr(store,'all',lambda *_:pytest.fail('Unbounded history read'))
    before=store.audit_integrity()
    path=f"/api/tasks/{source['id']}/workers"
    assert client.get(path).json()['total']==2
    result=client.get(path+'/'+asset['id']).json()
    assert result['worker']['id']==source['id']+':'+asset['id']
    assert result['coverage'][0]['status']=='completed'
    assert result['events']['total']==result['observations']['total']==30
    assert len(result['events']['items'])==len(result['observations']['items'])==25
    assert all(e['worker_provenance']['status']=='matched' for e in result['events']['items'])
    assert 'secret' not in str(result)
    assert not result['execution_authorized']
    for kind in ('events','observations'):
        first=result[kind]
        second=client.get(path+'/'+asset['id']+'/'+kind,params={'offset':25,'snapshot':first['snapshot']}).json()
        assert len(second['items'])==5
        assert set(x.get('id',x.get('seq')) for x in first['items']).isdisjoint(x.get('id',x.get('seq')) for x in second['items'])
    assert client.get(path+'/'+asset['id']+'/events',params={'search':'progress 29'}).json()['total']==1
    assert client.get(path+'/'+asset['id']+'/observations',params={'search':'/29'}).json()['total']==1
    assert store.audit_integrity()==before and store.count('traffic')==0
    for suffix in ('/missing','/missing/events','/missing/observations'):
        assert client.get(path+suffix).status_code==404
    assert client.get('/api/tasks/missing/workers').status_code==404
    for q in ('limit=101','offset=-1','snapshot=-1','search='+'a'*201):
        assert client.get(path+'/'+asset['id']+'/events?'+q).status_code==422


def test_missing_legacy_corrupt_coverage_and_worker_metadata_are_not_success(client):
    store=client.app.state.store;source,asset,_=seed(store,1)
    store.event(source['id'],'Legacy worker',detail={'asset_id':asset['id']})
    row_id=f"{source['id']}:{asset['id']}:endpoint_inventory"
    store.put('coverage',{'id':row_id,'task_id':source['id'],'asset_id':asset['id'],
                          'check':'endpoint_inventory','asset_revision':2,'status':'completed'})
    result=get_process(store,source['id'],asset['id'])
    assert result['coverage'][0]['status']=='not_recorded'
    assert result['events']['items'][0]['worker_provenance']['status']=='unconfirmed'
    store.patch('coverage',row_id,asset_revision=True)
    assert get_process(store,source['id'],asset['id'])['coverage'][0]['status']=='not_recorded'
    with store.connect() as db:db.execute("DELETE FROM records WHERE kind='coverage' AND id=?",(row_id,))
    assert get_process(store,source['id'],asset['id'])['coverage'][0]['status']=='not_recorded'
    assert store.get('coverage',row_id) is None
    store.patch('tasks',source['id'],status='pending')
    assert get_process(store,source['id'],asset['id'])['coverage'][0]['status']=='not_started'
    store.patch('tasks',source['id'],scope_snapshot=[asset,asset])
    assert client.get(f"/api/tasks/{source['id']}/workers").status_code==404


def test_one_snapshot_excludes_concurrent_source_and_observation_updates(client,monkeypatch):
    store=client.app.state.store;source,asset,observations=seed(store,1)
    original=store.event_page;changed=[]
    def events(*args,**kwargs):
        result=original(*args,**kwargs)
        if not changed:
            changed.append(True)
            store.patch('tasks',source['id'],approved_at=None,status='failed')
            store.patch('observations',observations[0]['id'],worker_id='altered')
        return result
    monkeypatch.setattr(store,'event_page',events)
    first=get_process(store,source['id'],asset['id'])
    assert first['task_status']=='completed' and first['observations']['items'][0]['provenance']['status']=='matched'
    second=get_process(store,source['id'],asset['id'])
    assert second['task_status']=='failed' and second['observations']['items'][0]['provenance']['status']=='unconfirmed'


def test_owned_execution_records_worker_process_for_readers(client,lab):
    url,handler=lab;asset=register(client,url)
    pending=task(client,asset,['endpoint_inventory','security_headers'])
    assert client.post('/api/tasks/'+pending['id']+'/approve').status_code==200
    assert finish(client,pending['id'])['task']['status']=='completed'
    result=client.get(f"/api/tasks/{pending['id']}/workers/{asset['id']}").json()
    assert all(row['status']=='completed' for row in result['coverage'])
    assert result['observations']['total']==1
    assert all(row['worker_provenance']['status']=='matched' for row in result['events']['items'])
    assert any(row['message'].startswith('Worker 종료') for row in result['events']['items'])
    assert handler.requests==['/']


def test_viewer_anonymous_and_readonly_mcp_permissions(client,tmp_path):
    from tests.test_identity import add,login
    from aegis.mcp import Reader,dispatch
    store=client.app.state.store;source,asset,_=seed(store,1)
    path=f"/api/tasks/{source['id']}/workers/{asset['id']}"
    viewer=add(client,'viewer')
    with login(client.app,viewer['username']) as read:
        assert read.get(path).status_code==200
        assert read.post(path).status_code==405
    reader=Reader(store.path);before=store.audit_integrity()
    args={'id':source['id'],'asset_id':asset['id']}
    assert reader.call('get_worker',args)['coverage'][0]['status']=='completed'
    for name in ('list_worker_events','list_worker_observations'):
        assert reader.call(name,args)['total']==1
        for bad in ({**args,'limit':True},{**args,'limit':101},{**args,'command':'run'},{**args,'asset_id':'outside'}):
            assert dispatch({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':bad}},reader)['result']['isError']
    assert store.audit_integrity()==before and store.count('traffic')==0
    client.post('/api/auth/logout')
    assert client.get(path).status_code==401


def test_corrupt_task_payload_identity_cannot_redirect_worker_history(client):
    import json
    store=client.app.state.store;source,asset,_=seed(store,1)
    altered={**source,'id':'other-task'}
    with store.connect() as db:
        db.execute("UPDATE records SET data=? WHERE kind='tasks' AND id=?",(json.dumps(altered),source['id']))
    result=client.get(f"/api/tasks/{source['id']}/workers/{asset['id']}")
    assert result.status_code==404
    assert 'secret' not in result.text
