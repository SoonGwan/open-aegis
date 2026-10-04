"""Native graph provenance, payload bounds and one-snapshot parity."""
import json
import pytest
from aegis.graph import build_graph,GraphNotFound
from aegis.postgres_store import PostgresStore
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_store import stores
from tests.test_graph import seed,evidence,finding


def both(stores,operation):
    for store in stores:operation(store)


def test_native_graph_proof_relationships_duplicates_and_foreign_rows(stores):
    def records(store):
        seed(store);evidence(store,'good');evidence(store,'other-task',task='old')
        evidence(store,'other-asset',asset='b');evidence(store,'other-check',check='cookie_policy')
        evidence(store,'other-fingerprint',fingerprint='wrong')
        store.put('evidence',{'id':'broken','observation':{'secret':'must-not-return'}})
        finding(store,'f',['good','good','other-task','other-asset','other-check','other-fingerprint','missing','broken'],confidence=.75)
        finding(store,'shared',['good'],confidence='high')
        finding(store,'foreign',['good'],asset_id='b')
        store.put('observations',{'id':'link','asset_id':'a','task_id':'t','url':'https://a.test/path','created_at':1.5})
        store.put('observations',{'id':'foreign-link','asset_id':'b','task_id':'t','url':'https://b.test/path'})
    both(stores,records);sqlite,pg=stores
    expected=build_graph(sqlite,'a','t');actual=build_graph(pg,'a','t')
    assert actual==expected and actual['omitted']['invalid_evidence']==5
    assert type(next(node for node in actual['nodes'] if node['id']=='finding:f')['data']['confidence']) is float
    assert sum(node['id']=='evidence:good' for node in actual['nodes'])==1
    assert 'must-not-return' not in json.dumps(actual)


def test_native_graph_filters_pages_and_large_reference_bounds(stores,monkeypatch):
    def records(store):
        seed(store)
        store.put_many([('evidence',{'id':f'e-{i}-{n}','asset_id':'a','task_id':'t','check':'security_headers','fingerprint':'fp','created_at':1,'observation':{'proof':'owned'}}) for i in range(55) for n in range(5)])
        for i in range(55):finding(store,'f-'+str(i),[f'e-{i}-{n}' for n in range(5)],severity='high' if i%2 else 'low',status='open' if i%2 else 'accepted')
        store.put_many([('observations',{'id':'link-'+str(i),'asset_id':'a','task_id':'t','url':'https://a.test/'+str(i)}) for i in range(15)])
    both(stores,records);sqlite,pg=stores
    monkeypatch.setattr(pg,'all',lambda *_:pytest.fail('Unbounded graph materialization'))
    first=build_graph(pg,'a','t',limit=25);assert first==build_graph(sqlite,'a','t',limit=25)
    assert first['omitted']['evidence']==75 and first['omitted']['endpoints']==5 and len(first['nodes'])<=93
    assert len(json.dumps(first).encode())<100000
    for store in stores:finding(store,'new',[])
    second=build_graph(pg,'a','t',limit=25,offset=25,snapshot=first['findings']['snapshot'])
    assert second==build_graph(sqlite,'a','t',limit=25,offset=25,snapshot=first['findings']['snapshot'])
    assert second['findings']['total']==55
    assert build_graph(pg,'a','t',check='security_headers',severity='high',status='open')==build_graph(sqlite,'a','t',check='security_headers',severity='high',status='open')
    both(stores,lambda store:finding(store,'large',['missing-'+str(i) for i in range(10000)]))
    large=build_graph(pg,'a','t',limit=1,check='security_headers')
    assert large==build_graph(sqlite,'a','t',limit=1,check='security_headers') and large['omitted']['invalid_evidence']==10000
    assert len(json.dumps(large).encode())<6000


def test_native_graph_empty_latest_stale_foreign_scope_and_bad_coverage(stores):
    both(stores,seed);sqlite,pg=stores
    for store in stores:
        store.put('assets',{'id':'new','name':'New'})
        store.patch('assets','a',revision=2,archived_at=123)
        store.put('coverage',{'id':'t:a:security_headers','asset_id':'a','task_id':'foreign','check':'cookie_policy','status':'completed','reason':'must-not-return'})
    for asset,task in [('new',None),('a',None),('a','t')]:assert build_graph(pg,asset,task)==build_graph(sqlite,asset,task)
    assert 'must-not-return' not in json.dumps(build_graph(pg,'a','t'))
    for asset,task in [('missing',None),('b','t'),('a','missing')]:
        with pytest.raises(GraphNotFound):build_graph(pg,asset,task)
    with pytest.raises(ValueError):build_graph(pg,'a',snapshot=-1)


def test_native_graph_same_snapshot_during_foreign_proof_edit(stores,postgres,monkeypatch):
    both(stores,lambda store:(seed(store),evidence(store,'good'),finding(store,'f',['good'])))
    sqlite,pg=stores;expected=build_graph(sqlite,'a','t')
    original=pg.get;changed=[];owner=pg.acquire_runtime()
    def get(kind,id,**options):
        row=original(kind,id,**options)
        if kind=='assets' and not changed:
            changed.append(True);pg.patch('evidence','good',asset_id='b',observation={'secret':'later-foreign'})
        return row
    monkeypatch.setattr(pg,'get',get)
    try:
        assert build_graph(pg,'a','t')==expected and changed
        next_graph=build_graph(pg,'a','t');assert next_graph['omitted']['invalid_evidence']==1
        assert 'later-foreign' not in json.dumps(next_graph)
    finally:owner.close()


def test_single_asset_graph_does_not_read_other_assets_coverage(stores,monkeypatch):
    both(stores,seed)
    for store in stores:
        task=store.get('tasks','t')
        extra=[{'id':'foreign-'+str(i),'revision':1} for i in range(500)]
        store.patch('tasks','t',asset_ids=task['asset_ids']+[row['id'] for row in extra],scope_snapshot=task['scope_snapshot']+extra)
        original=store.get;coverage=[]
        def guarded(kind,id,**options):
            if kind=='coverage':
                assert id.startswith('t:a:'),'Graph read foreign asset coverage'
                coverage.append(id)
            return original(kind,id,**options)
        with monkeypatch.context() as patch:
            patch.setattr(store,'get',guarded)
            result=build_graph(store,'a','t')
        assert len(coverage)==2 and len(result['nodes'])==4
