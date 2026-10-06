"""Owned fixed-recipient catalog GETs, never target scans or chat POSTs."""
import json,threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from fastapi import HTTPException
from tests.test_model_profiles import client,create,change
from tests.test_postgres_transfer import postgres

@pytest.fixture
def provider():
    seen=[];entered=threading.Event();release=threading.Event();release.set()
    config={'status':200,'body':{'data':[{'id':'owned-first','secret_extra':'discarded'},{'id':'owned-second'}]},'type':'application/json','encoding':'identity'}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append({'path':self.path,'authorization':self.headers['Authorization']});entered.set();assert release.wait(8)
            body=config.get('raw',json.dumps(config['body']).encode())
            self.send_response(config['status']);self.send_header('Content-Type',config['type']);self.send_header('Content-Encoding',config['encoding']);self.send_header('Content-Length',str(config.get('length',len(body))));self.send_header('Location','https://unreviewed.invalid/');self.end_headers()
            try:self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError):pass
        def do_POST(self):pytest.fail('Catalog must never send chat POST')
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}/v1',seen,config,entered,release
    finally:release.set();server.shutdown();server.server_close();thread.join(3)

def query(client,profile,**changes):
    return client.post('/api/model-profiles/'+profile['id']+'/catalog',json={'expected_revision':profile['revision'],'request_id':'owned-catalog-query-001',**changes})

def setup(client,provider,monkeypatch):
    monkeypatch.setenv('OWNED_MODEL_BASE',provider[0]);return create(client,enabled=True).json()['profile']

def test_catalog_reads_actual_fixed_path_and_masks_provider_metadata_with_immutable_replay(client,provider,monkeypatch):
    profile=setup(client,provider,monkeypatch);response=query(client,profile);assert response.status_code==200,response.text
    record=response.json()['query'];assert record['status']=='completed' and record['models']==['owned-first','owned-second']
    assert provider[1]==[{'path':'/v1/models','authorization':'Bearer owned-model-secret'}]
    assert query(client,profile).json()=={'query':record,'replayed':True}
    revised=change(client,profile,model='new-owned-model').json()['profile']
    assert query(client,profile).json()['query']==record
    assert query(client,revised).status_code==409
    assert len(provider[1])==1
    store=client.app.state.store;raw=json.dumps(store.all('model_catalog_queries'))
    assert 'owned-model-secret' not in raw and 'discarded' not in raw and provider[0] not in raw
    assert not store.all('llm_calls') and not store.all('traffic') and store.audit_integrity()['valid']


def test_native_catalog_fences_owner_loss_and_restart_recovers_without_second_get(client,provider,monkeypatch,postgres,tmp_path):
    from aegis.postgres_store import PostgresStore
    from aegis.postgres_maintenance import PostgresLease
    from aegis.maintenance import WorkspaceBusy
    from tests.test_postgres_ownership import terminate_owner
    from fastapi.testclient import TestClient
    from aegis.app import create_app
    store=client.app.state.store
    if not isinstance(store,PostgresStore):pytest.skip('Native backend ownership case')
    profile=setup(client,provider,monkeypatch);provider[4].clear()
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(query,client,profile)
        try:
            assert provider[3].wait(4);terminate_owner(postgres,client.app.state.engine.owner)
            with pytest.raises(WorkspaceBusy):
                with PostgresLease(postgres['dsn'],store.schema):pass
        finally:provider[4].set()
        response=pending.result(timeout=5)
        assert response.status_code==503,response.text
    client.__exit__(None,None,None)
    with TestClient(create_app(tmp_path/'workspace',allow_private=True)) as restarted:
        assert restarted.post('/api/auth/login',json={'username':'admin','password':'aegis-test-password-only'}).status_code==200
        receipt=query(restarted,profile).json()
        assert receipt['replayed'] and receipt['query']['status']=='unknown'
        assert receipt['query']['result_code']=='process_receipt_unconfirmed' and not receipt['query']['models']
        assert restarted.app.state.store.audit_integrity()['valid']
        assert not restarted.app.state.store.all('traffic') and not restarted.app.state.store.all('llm_calls')
    assert len(provider[1])==1

@pytest.mark.parametrize('changes,code',[
    ({'status':302},'provider_status'),({'status':401},'provider_status'),
    ({'type':'text/html'},'response_content_type'),({'encoding':'gzip'},'response_encoding'),
    ({'length':1024*1024+1},'response_byte_budget'),({'raw':b'{"data":[],"data":[]}'},'response_shape'),
    ({'body':{'data':[{'id':'bad\nmodel'}]}},'response_shape'),
    ({'body':{'data':[{'id':'owned-model-secret'}]}},'response_shape'),
    ({'body':{'data':[{'id':'same'},{'id':'same'}]}},'response_shape'),
    ({'body':{'data':[{'id':str(n)} for n in range(257)]}},'response_shape'),
])
def test_catalog_rejects_redirects_response_budgets_and_secret_echoes_without_repeating(client,provider,monkeypatch,changes,code):
    profile=setup(client,provider,monkeypatch);provider[2].update(changes)
    response=query(client,profile);assert response.status_code==200,response.text
    record=response.json()['query'];assert record['status']=='failed' and record['result_code']==code and record['models']==[]
    assert query(client,profile).json()=={'query':record,'replayed':True} and len(provider[1])==1
    assert 'owned-model-secret' not in json.dumps(record)
    assert not client.app.state.store.all('traffic')

def test_active_uuid_replays_without_a_second_get_and_other_requests_are_bounded(client,provider,monkeypatch):
    profile=setup(client,provider,monkeypatch);provider[4].clear()
    with ThreadPoolExecutor(max_workers=1) as pool:
        first=pool.submit(query,client,profile);assert provider[3].wait(4)
        duplicate=query(client,profile);assert duplicate.status_code==200 and duplicate.json()['replayed'] and duplicate.json()['query']['status']=='started'
        assert query(client,profile,request_id='owned-catalog-query-002').status_code==429
        provider[4].set();result=first.result(timeout=5)
    assert result.json()['query']['status']=='completed' and len(provider[1])==1
    assert query(client,profile).json()['query']==result.json()['query']

def test_catalog_request_validation_and_stale_profile_or_role_never_dispatch(client,provider,monkeypatch):
    profile=setup(client,provider,monkeypatch)
    assert query(client,profile,request_id='short').status_code==422
    assert query(client,profile,expected_revision=True).status_code==422
    assert query(client,profile,expected_revision=0).status_code==409
    store=client.app.state.store;actor=store.user(username='admin');store.update_user(actor['id'],role='operator')
    assert query(client,profile).status_code==401
    from aegis.model_catalog import CatalogInput
    with pytest.raises(HTTPException) as caught:client.app.state.model_catalog.read(profile['id'],CatalogInput(expected_revision=1,request_id='owned-catalog-query-001'),actor)
    assert caught.value.status_code==403 and not provider[1] and store.count('model_catalog_queries')==0


def test_stopping_a_pending_catalog_waits_for_owned_request_and_records_uncertainty(client,provider,monkeypatch):
    profile=setup(client,provider,monkeypatch);provider[4].clear()
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(query,client,profile);assert provider[3].wait(4)
        client.app.state.model_catalog.close()
        result=pending.result(timeout=4)
    assert result.status_code==200,result.text
    assert result.json()['query']['status']=='unknown' and result.json()['query']['result_code']=='request_stopped'
    assert len(provider[1])==1 and not client.app.state.store.all('traffic')
    provider[4].set()


@pytest.mark.parametrize('mutation',['credential','profile','role'])
def test_catalog_rechecks_review_after_dns_before_any_get(client,provider,monkeypatch,mutation):
    import aegis.model_catalog as module
    profile=setup(client,provider,monkeypatch);original=module.resolve
    def changed(*args,**kwargs):
        address=original(*args,**kwargs)
        if mutation=='credential':monkeypatch.setenv('OWNED_MODEL_KEY','owned-rotated-key')
        elif mutation=='profile':assert change(client,profile,model='owned-revised-model').status_code==200
        else:
            store=client.app.state.store;actor=store.user(username='admin');store.update_user(actor['id'],role='operator')
        return address
    monkeypatch.setattr(module,'resolve',changed)
    response=query(client,profile);assert response.status_code==200,response.text
    assert response.json()['query']['status']=='blocked' and response.json()['query']['result_code']=='profile_review_changed'
    assert not provider[1] and client.app.state.store.audit_integrity()['valid']


@pytest.mark.parametrize('phase',['start','finish'])
def test_catalog_audit_failure_rolls_back_and_never_redispatches_uncertain_attempt(client,provider,monkeypatch,phase):
    from aegis.model_catalog import CatalogInput
    profile=setup(client,provider,monkeypatch);store=client.app.state.store;actor=store.user(username='admin')
    original=store.event;calls=[]
    def fail(*args,**kwargs):
        calls.append(args)
        if len(calls)==(1 if phase=='start' else 2):raise RuntimeError('owned catalog audit failure')
        return original(*args,**kwargs)
    monkeypatch.setattr(store,'event',fail)
    data=CatalogInput(expected_revision=profile['revision'],request_id='owned-catalog-query-001')
    with pytest.raises(RuntimeError,match='owned catalog audit failure'):
        client.app.state.model_catalog.read(profile['id'],data,actor)
    monkeypatch.setattr(store,'event',original)
    assert store.count('model_catalog_queries')==(0 if phase=='start' else 1)
    assert len(provider[1])==(0 if phase=='start' else 1)
    if phase=='finish':
        assert query(client,profile).json()['query']['status']=='started' and len(provider[1])==1
        assert client.app.state.model_catalog.recover()
        record=query(client,profile).json()['query']
        assert record['status']=='unknown' and record['result_code']=='process_receipt_unconfirmed' and not record['models']
        assert not client.app.state.model_catalog.recover() and len(provider[1])==1
    assert store.audit_integrity()['valid'] and not store.all('traffic') and not store.all('llm_calls')


def test_catalog_committed_receipt_survives_actual_app_restart_without_get(client,provider,monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from aegis.app import create_app
    profile=setup(client,provider,monkeypatch);record=query(client,profile).json()['query']
    assert record['profile_snapshot']['model']==profile['model']
    client.__exit__(None,None,None)
    with TestClient(create_app(tmp_path/'workspace',allow_private=True)) as restarted:
        assert restarted.post('/api/auth/login',json={'username':'admin','password':'aegis-test-password-only'}).status_code==200
        assert query(restarted,profile).json()=={'query':record,'replayed':True}
        history=restarted.get('/api/model-profiles/'+profile['id']+'/catalog-history').json()
        assert history['items']==[record] and history['total']==1
        assert restarted.app.state.store.audit_integrity()['valid']
    assert len(provider[1])==1
