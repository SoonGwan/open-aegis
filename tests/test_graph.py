"""Edges must follow stored provenance; unrelated records and paging must stay isolated."""
import json
import pytest
from aegis.graph import build_graph, GraphNotFound
from aegis.store import Store
from tests.test_validation import client, lab, register, task, finish


def seed(store):
    asset = {'id':'a','name':'Asset A','url':'https://a.test/','revision':1,'owner':'Team'}
    other = {'id':'b','name':'Asset B','url':'https://b.test/','revision':1}
    plan = {'id':'t','name':'Plan A','status':'completed','created_at':1,'approved_at':1,
            'asset_ids':['a'],'scope_snapshot':[asset],'checks':['security_headers','endpoint_inventory']}
    store.put_many([('assets',asset),('assets',other),('tasks',plan)])
    return asset, plan


def evidence(store, id, *, asset='a', task='t', check='security_headers', fingerprint='fp'):
    store.put('evidence',{'id':id,'asset_id':asset,'task_id':task,'check':check,'fingerprint':fingerprint,
                          'observation':{'proof':id},'created_at':1})


def finding(store, id, refs, **extra):
    store.put('findings',{'id':id,'title':'Finding '+id,'asset_id':'a','check':'security_headers',
                          'task_ids':['t'],'severity':'low','status':'open','fingerprint':'fp','evidence_ids':refs,**extra})


def test_edges_follow_asset_task_check_finding_proof_and_do_not_cross_scope(tmp_path):
    store = Store(tmp_path/'graph.db')
    seed(store)
    evidence(store,'good')
    evidence(store,'other-asset',asset='b')
    evidence(store,'other-task',task='old')
    evidence(store,'other-check',check='cookie_policy')
    evidence(store,'other-fingerprint',fingerprint='wrong')
    finding(store,'f',['good','other-asset','other-task','other-check','other-fingerprint','missing'])
    finding(store,'unrelated',['good'],asset_id='b')
    store.put('observations',{'id':'link','asset_id':'a','task_id':'t','url':'https://a.test/link'})
    store.put('observations',{'id':'foreign','asset_id':'b','task_id':'t','url':'https://b.test/link'})
    graph = build_graph(store,'a','t')
    ids = {node['id'] for node in graph['nodes']}
    assert 'evidence:good' in ids and 'finding:f' in ids and 'endpoint:link' in ids
    assert not ids & {'asset:b','finding:unrelated','evidence:other-asset','evidence:other-task','evidence:other-check','evidence:other-fingerprint','endpoint:foreign'}
    assert graph['omitted']['invalid_evidence'] == 4
    by_id = {node['id']:node for node in graph['nodes']}
    for edge in graph['edges']:
        assert edge['source'] in ids and edge['target'] in ids
        if edge['relation']=='evidence':
            assert by_id[edge['source']]['record_id']=='f' and by_id[edge['target']]['record_id']=='good'
        if edge['relation']=='finding':
            assert by_id[edge['source']]['data']['check']==by_id[edge['target']]['data']['check']
    proof_finding = by_id['finding:f']
    assert proof_finding['data']['evidence_count']==1 and proof_finding['data']['history_reference_count']==6
    assert len(ids)==len(graph['nodes'])


def test_graph_filters_pages_and_discloses_proof_limits(tmp_path, monkeypatch):
    store = Store(tmp_path/'large.db')
    seed(store)
    for index in range(55):
        refs=[f'e-{index}-{n}' for n in range(5)]
        for ref in refs:evidence(store,ref)
        finding(store,f'f-{index}',refs,severity='high' if index%2 else 'low',status='open' if index%2 else 'accepted')
    for index in range(15):
        store.put('observations',{'id':str(index),'asset_id':'a','task_id':'t','url':f'https://a.test/{index}'})
    monkeypatch.setattr(store,'all',lambda *_:pytest.fail('Unbounded graph read'))
    first=build_graph(store,'a','t',limit=25)
    assert first['findings']['total']==55 and first['findings']['has_more']
    assert first['omitted']['evidence']==75 and first['omitted']['endpoints']==5
    assert len(first['nodes'])<=93 and len(json.dumps(first).encode())<100_000
    finding(store,'new',[])
    second=build_graph(store,'a','t',limit=25,offset=25,snapshot=first['findings']['snapshot'])
    assert second['findings']['total']==55
    assert not {node['id'] for node in first['nodes'] if node['kind']=='finding'} & {node['id'] for node in second['nodes'] if node['kind']=='finding'}
    filtered=build_graph(store,'a','t',check='security_headers',severity='high',status='open')
    assert filtered['findings']['total']==27
    assert all(node['data']['severity']=='high' for node in filtered['nodes'] if node['kind']=='finding')
    assert not any(node['kind']=='endpoint' for node in filtered['nodes'])


def test_graph_handles_empty_asset_plan_missing_records_and_stale_scope(tmp_path):
    store=Store(tmp_path/'empty.db')
    store.put('assets',{'id':'new','name':'New'})
    empty=build_graph(store,'new')
    assert len(empty['nodes'])==1 and not empty['edges'] and empty['task'] is None
    seed(store)
    store.patch('assets','a',revision=2)
    stale=build_graph(store,'a','t')
    assert all(node['data']['stale'] for node in stale['nodes'] if node['kind']=='check')
    assert all(node['data']['status']=='not_recorded' for node in stale['nodes'] if node['kind']=='check')
    store.patch('assets','a',archived_at=123)
    archived=build_graph(store,'a','t')
    assert archived['asset']['archived_at']==123 and archived['nodes'][0]['data']['archived_at']==123
    with pytest.raises(GraphNotFound):build_graph(store,'missing')
    with pytest.raises(GraphNotFound):build_graph(store,'b','t')
    with pytest.raises(GraphNotFound):build_graph(store,'a','missing')


def test_shared_proof_node_is_unique_and_broken_metadata_never_creates_proof_edge(tmp_path):
    store=Store(tmp_path/'references.db')
    seed(store)
    evidence(store,'shared')
    finding(store,'first',['shared','shared'])
    finding(store,'second',['shared'])
    store.put('evidence',{'id':'no-metadata','observation':{'secret':'do-not-return'}})
    finding(store,'broken',['no-metadata'])
    graph=build_graph(store,'a','t')
    assert sum(node['id']=='evidence:shared' for node in graph['nodes'])==1
    assert sum(edge['target']=='evidence:shared' for edge in graph['edges'])==2
    assert graph['omitted']['invalid_evidence']==1
    assert 'do-not-return' not in json.dumps(graph)


def test_api_graph_is_readonly_and_validates_filters(client, lab):
    url, handler=lab
    asset=register(client,url)
    plan=task(client,asset,['security_headers','endpoint_inventory'])
    pending=client.get('/api/graph',params={'asset_id':asset['id'],'task_id':plan['id']})
    assert pending.status_code==200
    assert {node['data']['status'] for node in pending.json()['nodes'] if node['kind']=='check'}=={'not_started'}
    assert handler.requests==[]
    client.post('/api/tasks/'+plan['id']+'/approve')
    finish(client,plan['id'])
    before=list(handler.requests)
    graph=client.get('/api/graph',params={'asset_id':asset['id'],'task_id':plan['id']}).json()
    assert any(edge['relation']=='evidence' for edge in graph['edges'])
    assert handler.requests==before
    for extra in ({'limit':26},{'offset':-1},{'check':'run_shell'},{'severity':'invalid'},{'status':'invalid'}):
        assert client.get('/api/graph',params={'asset_id':asset['id'],**extra}).status_code==422
    assert client.get('/api/graph?asset_id=missing').status_code==404
    client.post('/api/auth/logout')
    assert client.get('/api/graph',params={'asset_id':asset['id']}).status_code==401


def test_large_evidence_reference_history_is_counted_without_returning_all_ids(tmp_path):
    store=Store(tmp_path/'history.db')
    seed(store)
    evidence(store,'valid')
    finding(store,'large',['valid']+[f'missing-{index}' for index in range(10_000)])
    graph=build_graph(store,'a','t')
    assert graph['omitted']['invalid_evidence']==10_000
    assert len(json.dumps(graph).encode())<6000
    selected=next(node for node in graph['nodes'] if node['kind']=='finding')
    assert selected['data']['history_reference_count']==10_001
    assert 'evidence_ids' not in selected['data']


def test_coverage_tuple_mismatch_is_unknown_and_never_becomes_foreign_check(tmp_path):
    store=Store(tmp_path/'scope.db')
    seed(store)
    store.put('coverage',{'id':'t:a:security_headers','asset_id':'a','task_id':'foreign',
                          'check':'cookie_policy','status':'completed','reason':'FOREIGN-ROW-MUST-NOT-APPEAR'})
    graph=build_graph(store,'a','t')
    checks=[node for node in graph['nodes'] if node['kind']=='check']
    assert {node['data']['check'] for node in checks}=={'security_headers','endpoint_inventory'}
    assert 'FOREIGN-ROW-MUST-NOT-APPEAR' not in json.dumps(graph)
    assert next(node for node in checks if node['data']['check']=='security_headers')['data']['status']=='not_recorded'
    from aegis.coverage import latest_summary
    with store.connect() as db:
        summary=latest_summary(db)
    assert summary['completed']==0 and summary['counts']['not_recorded']==2
