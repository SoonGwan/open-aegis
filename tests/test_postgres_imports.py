"""Native reviewed imports: atomic batches, stale scope and source read fencing."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

import pytest
from fastapi import HTTPException
from aegis import scopesentry as imports,postgres_transfer as transfer
from aegis.maintenance import WorkspaceBusy
from aegis.postgres_maintenance import PostgresLease
from aegis.postgres_store import PostgresStore
from aegis.scopesentry_remote import Sources,PageInput
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_store import stores
from tests.test_scopesentry import row


def preview(store,rows,actor='actor',source='owned'):
    return imports.preview(store,imports.PreviewInput(source_key=source,export='\n'.join(json.dumps(r) for r in rows)),actor)


def apply(store,plan,selected=None,actor='actor',authorized=True):
    return imports.apply(store,plan['id'],imports.ApplyInput(selected=selected or [r['external_id'] for r in plan['rows'] if r['status']=='ready'],authorized=authorized),actor)


def code(expected,operation):
    with pytest.raises(HTTPException) as error:operation()
    assert error.value.status_code==expected


def test_native_import_preview_selection_privacy_history_and_local_scope(stores,monkeypatch):
    results=[]
    for store in stores:
        counter=iter(range(100))
        with monkeypatch.context() as patch:
            patch.setattr(imports,'now',lambda:100)
            patch.setattr(imports,'identifier',lambda:'owned-'+str(next(counter)))
            plan=preview(store,[row(1,body='secret-body',rawheaders='secret-header'),row(2),row(3,type='tcp')])
            assert store.count('assets')==store.count('tasks')==0
            assert 'secret-' not in json.dumps(store.get('import_previews',plan['id']))
            assert all('expected_source' not in r for r in plan['rows'])
            first=apply(store,plan);assert first['created']==1 and first['linked']==2
            asset_id=first['items'][0]['asset_id'];asset=store.get('assets',asset_id)
            store.patch('assets',asset_id,owner='local',tags=['local'])
            old=store.get('assets',asset_id)
            store.put('tasks',{'id':'pending','status':'pending','scope_snapshot':[old]})
            pending=store.get('tasks','pending')
            repeated=preview(store,[row(1,title='discard',tags=['discard'])])
            assert repeated['rows'][0]['action']=='seen' and apply(store,repeated)['seen']==1
            assert store.get('assets',asset_id)==old
            changed=preview(store,[row(1,url='https://changed.invalid/')])
            assert changed['rows'][0]['source_changed']
            updated=apply(store,changed);assert updated['created']==updated['source_changed']==1
            assert updated['items'][0]['asset_id']!=asset_id
            assert store.get('assets',asset_id)==old and store.get('tasks','pending')==pending
            assert store.count('asset_source_history')==1
            apply(store,preview(store,[row(1,url='https://changed.invalid/')],source='second'))
            assert store.count('assets')==2 and store.count('asset_sources')==3
            assert apply(store,changed)==updated and store.audit_integrity()['valid']
            assert asset['revision']==1 and asset['authorization_rules']==[]
            results.append((plan,first,updated,store.page('asset_sources')['items'],store.page('asset_source_history')['items']))
    assert results[0]==results[1]


def test_native_import_actor_selection_expiry_and_retry_contract(stores):
    for store in stores:
        plan=preview(store,[row(1),row(2)])
        code(422,lambda:apply(store,plan,authorized=False))
        code(403,lambda:apply(store,plan,actor='other'))
        code(422,lambda:apply(store,plan,['unknown']))
        code(422,lambda:apply(store,plan,[row()['_id']]*2))
        code(404,lambda:imports.apply(store,'missing',imports.ApplyInput(selected=[row()['_id']],authorized=True),'actor'))
        assert store.count('assets')==0
        result=apply(store,plan,[row()['_id']]);assert apply(store,plan,[row()['_id']])==result
        code(409,lambda:apply(store,plan,[row(2)['_id']]))
        store.patch('import_previews',plan['id'],expires_at=1)
        code(410,lambda:apply(store,plan,[row()['_id']]))


@pytest.mark.parametrize('change',['asset','source','archived','missing-link','duplicate-url'])
def test_native_import_stale_batch_or_blocked_scope(stores,change):
    for store in stores:
        initial=apply(store,preview(store,[row()]))
        id=initial['items'][0]['asset_id']
        plan=preview(store,[row(),row(2,url='https://never-created.invalid/')])
        if change=='asset':store.patch('assets',id,name='edited',revision=2)
        elif change=='source':apply(store,preview(store,[row(url='https://changed.invalid/')]))
        elif change=='archived':store.patch('assets',id,archived_at=123)
        elif change=='missing-link':
            link=store.get('asset_sources',imports.source_id('owned',row()['_id']))
            store.put('asset_sources',{**link,'asset_id':'missing'})
        else:store.put('assets',{**store.get('assets',id),'id':'duplicate'})
        before=store.count('assets');code(409,lambda:apply(store,plan))
        assert store.count('assets')==before and store.get('import_previews',plan['id'])['applied_at'] is None
        if change in ('archived','missing-link'):
            blocked=preview(store,[row()]);assert blocked['rows'][0]['status']=='blocked'
            code(422,lambda:apply(store,blocked,[row()['_id']]))


def test_native_import_two_instances_idempotence_and_competing_review(stores):
    sqlite,pg=stores
    for store,other in ((sqlite,type(sqlite)(sqlite.path)),(pg,PostgresStore(pg._dsn,pg.schema))):
        plan=preview(store,[row()]);barrier=threading.Barrier(2)
        def run(target):barrier.wait(timeout=5);return apply(target,plan)
        with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(run,[store,other]))
        assert result[0]==result[1] and store.count('assets')==store.count('asset_sources')==1
        assert store.audit_integrity()['events']==1
        plans=[preview(store,[row(2,url='https://compete.invalid/')]),preview(other,[row(2,url='https://compete.invalid/')])]
        barrier=threading.Barrier(2)
        def compete(pair):
            target,plan=pair;barrier.wait(timeout=5)
            try:return apply(target,plan)
            except HTTPException as error:return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(compete,zip((store,other),plans)))
        assert sum(isinstance(r,dict) for r in results)==1 and results.count(409)==1
        assert store.count('assets')==2 and store.count('asset_sources')==2 and store.audit_integrity()['events']==2


def test_native_import_audit_failure_rolls_back_history_links_assets_and_result(stores):
    import psycopg
    _,pg=stores;apply(pg,preview(pg,[row()]))
    plan=preview(pg,[row(url='https://changed.invalid/'),row(2,url='https://second.invalid/')])
    with pg.transaction() as db:before=transfer.postgres_manifest(db)
    with pg.transaction(write=True) as db:
        db.execute("CREATE FUNCTION reject_import() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'owned import audit failure'; END $$")
        db.execute('CREATE TRIGGER reject_import BEFORE INSERT ON event_hashes FOR EACH ROW EXECUTE FUNCTION reject_import()')
    with pytest.raises(psycopg.errors.RaiseException,match='owned import audit failure'):apply(pg,plan)
    with pg.transaction() as db:assert transfer.postgres_manifest(db)==before
    assert pg.get('import_previews',plan['id'])['applied_at'] is None
    with pg.transaction(write=True) as db:db.execute('DROP TRIGGER reject_import ON event_hashes');db.execute('DROP FUNCTION reject_import()')
    result=apply(pg,plan)
    assert result['created']==2 and result['source_changed']==1 and pg.count('asset_source_history')==1
    assert pg.audit_integrity()['valid']


def test_native_preview_limit_is_atomic_and_expiry_cleanup(stores):
    _,pg=stores;other=PostgresStore(pg._dsn,pg.schema)
    pg.put_many([('import_previews',{'id':str(i),'expires_at':99999999999}) for i in range(49)])
    barrier=threading.Barrier(2)
    def create(target):
        barrier.wait(timeout=5)
        try:return preview(target,[row()])
        except HTTPException as error:return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(create,[pg,other]))
    assert results.count(429)==1 and pg.count('import_previews')==50
    pg.patch('import_previews','0',expires_at=1)
    assert preview(pg,[row()])['rows'][0]['status']=='ready'
    assert pg.count('import_previews')==50 and pg.get('import_previews','0') is None


@pytest.fixture
def owned_source(monkeypatch):
    state={'calls':[],'rows':[dict(id=f'{i:024x}',type='http',url=f'https://owned.invalid/{i}',body='private-marker') for i in range(1,52)],'entered':threading.Event(),'release':threading.Event(),'hold':False}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            query=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state['calls'].append((self.path,self.headers.get('Authorization'),query));state['entered'].set()
            if state['hold']:assert state['release'].wait(5)
            start=(query['pageIndex']-1)*query['pageSize']
            raw=json.dumps({'code':200,'data':{'list':state['rows'][start:start+query['pageSize']]}}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    monkeypatch.setenv('OWNED_NATIVE_SENTRY_TOKEN','owned-source-secret')
    config=[dict(id='owned',url=f'http://127.0.0.1:{server.server_port}',token_env='OWNED_NATIVE_SENTRY_TOKEN',allow_private=True,lab_http=True,project='owned')]
    try:yield state,config
    finally:state['release'].set();server.shutdown();server.server_close();thread.join(2)


def test_native_remote_resume_cache_privacy_and_atomic_parent_rollback(stores,owned_source):
    import psycopg
    _,pg=stores;state,config=owned_source;owner=pg.acquire_runtime();sources=Sources(pg,threading.Event(),config)
    try:
        first=sources.collect(PageInput(connection_id='owned'),'actor')
        assert len(first['rows'])==50 and first['remote']['has_more']
        with pg.transaction(write=True) as db:
            db.execute("CREATE FUNCTION reject_preview() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.kind='import_previews' THEN RAISE EXCEPTION 'owned preview rollback'; END IF; RETURN NEW; END $$")
            db.execute('CREATE TRIGGER reject_preview BEFORE INSERT ON records FOR EACH ROW EXECUTE FUNCTION reject_preview()')
        with pytest.raises(psycopg.errors.RaiseException,match='owned preview rollback'):
            sources.collect(PageInput(connection_id='owned',previous_preview_id=first['id']),'actor')
        assert pg.count('import_previews')==1 and pg.get('import_previews',first['id'])['remote']['next_preview_id'] is None
        with pg.transaction(write=True) as db:db.execute('DROP TRIGGER reject_preview ON records');db.execute('DROP FUNCTION reject_preview()')
        second=sources.collect(PageInput(connection_id='owned',previous_preview_id=first['id']),'actor')
        assert len(second['rows'])==1 and not second['remote']['has_more']
        assert sources.collect(PageInput(connection_id='owned',previous_preview_id=first['id']),'actor')==second
        assert [call[2]['pageIndex'] for call in state['calls']]==[1,1,2,1,2]
        assert all(call[0]=='/api/assets/asset' and call[1]=='Bearer owned-source-secret' for call in state['calls'])
        assert pg.count('assets')==pg.count('tasks')==0
        raw=json.dumps(pg.get('import_previews',first['id']))
        assert 'owned-source-secret' not in raw and 'private-marker' not in raw
        assert 'contract' not in json.dumps(first)
        applied=apply(pg,first);assert applied['created']==50 and pg.count('tasks')==0
    finally:owner.close()


def test_native_remote_and_manual_import_refuse_after_owner_loss(stores,postgres,owned_source):
    _,pg=stores;state,config=owned_source;sources=Sources(pg,threading.Event(),config)
    with pytest.raises(WorkspaceBusy):sources.collect(PageInput(connection_id='owned'),'actor')
    assert state['calls']==[]
    plan=preview(pg,[row()]);owner=pg.acquire_runtime();state['hold']=True;replacement=None
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending=pool.submit(sources.collect,PageInput(connection_id='owned'),'actor');assert state['entered'].wait(5)
            try:
                with transfer.connect(postgres['dsn']) as db:assert db.execute('SELECT pg_terminate_backend(%s) AS killed',(owner.pid,)).fetchone()['killed']
                with pytest.raises(WorkspaceBusy):PostgresLease(postgres['dsn'],pg.schema)
            finally:state['release'].set()
            with pytest.raises(WorkspaceBusy):pending.result(timeout=5)
        replacement=PostgresLease(postgres['dsn'],pg.schema)
        with pytest.raises(WorkspaceBusy):sources.collect(PageInput(connection_id='owned'),'actor')
        with pytest.raises(WorkspaceBusy):apply(pg,plan)
        with pytest.raises(WorkspaceBusy):preview(pg,[row(2)])
        fresh=PostgresStore(pg._dsn,pg.schema)
        assert fresh.count('import_previews')==1 and fresh.count('assets')==0 and len(state['calls'])==1
    finally:
        state['release'].set()
        if replacement:replacement.close()
        owner.close()
