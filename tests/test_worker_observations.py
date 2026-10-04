"""Worker link history retains each approved task's source metadata."""
from tests.test_validation import client, lab, register, task, finish


def test_repeated_owned_tasks_preserve_both_workers_link_history(client,lab):
    url,handler=lab
    asset=register(client,url)
    tasks=[]
    for _ in range(2):
        plan=task(client,asset,['endpoint_inventory']);tasks.append(plan)
        assert client.post('/api/tasks/'+plan['id']+'/approve').status_code==200
        assert finish(client,plan['id'])['task']['status']=='completed'
    store=client.app.state.store
    first=store.page('observations',filters={'task_id':tasks[0]['id']})
    second=store.page('observations',filters={'task_id':tasks[1]['id']})
    assert first['total']==second['total']==1
    assert first['items'][0]['id']!=second['items'][0]['id']
    assert first['items'][0]['url']==second['items'][0]['url']==url+'api/account'
    assert handler.requests==['/','/']


def populate(store,count=30):
    from aegis.tool_contracts import contracts_for
    from aegis.worker_observations import record_link
    asset={'id':'source-asset','url':'https://owned.example.invalid/app/','name':'Owned source','revision':1}
    source={'id':'source-task','name':'Source worker task','approved_at':1.,'scope_snapshot':[asset],
            'checks':['endpoint_inventory'],'tool_contracts':contracts_for(['endpoint_inventory'])}
    store.put_many([('assets',asset),('tasks',source)])
    records=[record_link(store,source,asset,'endpoint_inventory',asset['url']+str(i)) for i in range(count)]
    return source,asset,records


def test_task_page_source_checks_history_search_snapshot_and_no_requests(client):
    source,asset,records=populate(client.app.state.store)
    url='/api/tasks/'+source['id']+'/observations'
    first=client.get(url).json()
    assert first['total']==30 and len(first['items'])==25 and first['has_more']
    assert all(row['provenance']['status']=='matched' and row['verified'] is False for row in first['items'])
    client.app.state.store.patch('assets',asset['id'],url='https://changed.example.invalid/',revision=2)
    second=client.get(url,params={'offset':25,'snapshot':first['snapshot']}).json()
    assert len(second['items'])==5 and all(row['provenance']['status']=='matched' for row in second['items'])
    assert set(r['id'] for r in first['items']).isdisjoint(r['id'] for r in second['items'])
    assert client.get(url,params={'search':'Source worker task'}).json()['total']==30
    assert client.app.state.store.count('traffic')==0
    assert client.get('/api/tasks/missing/observations').status_code==404
    for query in ('limit=101','offset=-1','snapshot=-1','search='+'x'*201):
        assert client.get(url+'?'+query).status_code==422


def test_legacy_and_altered_metadata_are_unconfirmed_and_cross_task_is_excluded(client):
    store=client.app.state.store;source,asset,records=populate(store,1)
    record=records[0]
    store.put('observations',{'id':'legacy','task_id':source['id'],'asset_id':asset['id'],'url':asset['url']})
    store.put('observations',{**record,'id':'foreign','task_id':'other'})
    url='/api/tasks/'+source['id']+'/observations'
    rows=client.get(url).json()['items']
    assert len(rows)==2 and rows[0]['provenance']['status']=='unconfirmed'
    assert rows[1]['provenance']['status']=='matched'
    for change in ({'package_sha256':'f'*64},{'scope_revision':True},{'worker_id':'other'},
                   {'url':'https://outside.example.invalid/'},{'verified':True},{'check':'security_headers'}):
        store.put('observations',{**record,**change})
        assert all(row['provenance']['status']=='unconfirmed' for row in client.get(url).json()['items'])
    store.put('observations',record)
    store.patch('tasks',source['id'],approved_at=None)
    assert all(row['provenance']['status']=='unconfirmed' for row in client.get(url).json()['items'])


def test_snapshot_source_does_not_mix_later_task_update(client,monkeypatch):
    store=client.app.state.store;source,_,_=populate(store,1)
    original=store.page;changed=[]
    def page(*args,**kwargs):
        result=original(*args,**kwargs)
        if args[0]=='observations' and not changed:
            changed.append(True);store.patch('tasks',source['id'],approved_at=None)
        return result
    monkeypatch.setattr(store,'page',page)
    url='/api/tasks/'+source['id']+'/observations'
    assert client.get(url).json()['items'][0]['provenance']['status']=='matched'
    assert client.get(url).json()['items'][0]['provenance']['status']=='unconfirmed'


def test_task_observation_viewer_and_anonymous_permissions(client):
    from tests.test_identity import add,login
    source,_,_=populate(client.app.state.store,1)
    url='/api/tasks/'+source['id']+'/observations'
    viewer=add(client,'viewer')
    with login(client.app,viewer['username']) as read:
        assert read.get(url).json()['items'][0]['provenance']['status']=='matched'
    client.post('/api/auth/logout')
    assert client.get(url).status_code==401


def test_actual_readonly_mcp_task_observations_with_source_and_bounds(tmp_path):
    from aegis.store import Store
    from aegis.mcp import Reader
    store=Store(tmp_path/'source.db');source,_,records=populate(store,30)
    reader=Reader(store.path)
    before=store.audit_integrity()
    result=reader.call('list_task_observations',{'id':source['id'],'search':'Owned source'})
    assert result['total']==30 and len(result['items'])==25
    assert all(row['provenance']['status']=='matched' for row in result['items'])
    assert reader.call('list_task_observations',{'id':source['id'],'offset':25,'snapshot':result['snapshot']})['total']==30
    import pytest
    for args in ({'id':'missing'},{'id':source['id'],'limit':101},{'id':source['id'],'url':'https://must-not-fetch.invalid/'}):
        with pytest.raises(ValueError):reader.call('list_task_observations',args)
    assert store.audit_integrity()==before and store.count('traffic')==0
