"""Actual owned provider inference checks, no target traffic."""
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
    config={'status':200,'type':'application/json','encoding':'identity','body':{
        'choices':[{'message':{'role':'assistant','content':'AEGIS_OK'}}],
        'usage':{'prompt_tokens':5,'completion_tokens':3,'total_tokens':8},'discarded':'owned-model-secret'}}
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append({'path':self.path,'authorization':self.headers['Authorization'],
                         'body':json.loads(self.rfile.read(int(self.headers['Content-Length'])))})
            entered.set();assert release.wait(8)
            raw=config.get('raw',json.dumps(config['body']).encode())
            self.send_response(config['status']);self.send_header('Content-Type',config['type']);self.send_header('Content-Encoding',config['encoding'])
            self.send_header('Content-Length',str(config.get('length',len(raw))));self.send_header('Location','https://unreviewed.invalid/');self.end_headers()
            try:self.wfile.write(raw)
            except (BrokenPipeError,ConnectionResetError):pass
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}/v1',seen,config,entered,release
    finally:release.set();server.shutdown();server.server_close();thread.join(3)

def setup(client,provider,monkeypatch):
    monkeypatch.setenv('OWNED_MODEL_BASE',provider[0]);return create(client,enabled=True).json()['profile']

def check(client,profile,**changes):
    return client.post('/api/model-profiles/'+profile['id']+'/connection-test',json={
        'expected_revision':profile['revision'],'request_id':'owned-connection-check-001',**changes})

def test_actual_fixed_inference_preserves_immutable_replay_and_masks_response(client,provider,monkeypatch):
    profile=setup(client,provider,monkeypatch);response=check(client,profile);assert response.status_code==200,response.text
    record=response.json()['query'];assert record['status']=='completed' and record['result_code']=='inference_response_valid'
    assert record['tokens']=={'status':'reported','prompt_tokens':5,'completion_tokens':3,'total_tokens':8}
    assert provider[1]==[{'path':'/v1/chat/completions','authorization':'Bearer owned-model-secret','body':{
        'model':'owned-primary-model','messages':[{'role':'user','content':'Reply exactly AEGIS_OK.'}],'max_tokens':16,'stream':False}}]
    assert check(client,profile).json()=={'query':record,'replayed':True}
    revised=change(client,profile,model='owned-later-model').json()['profile']
    assert check(client,profile).json()['query']==record
    assert check(client,revised).status_code==409 and len(provider[1])==1
    store=client.app.state.store;raw=json.dumps(store.all('model_connection_checks'))
    assert 'owned-model-secret' not in raw and provider[0] not in raw and 'AEGIS_OK' not in raw
    assert not store.all('llm_calls') and not store.all('traffic') and store.audit_integrity()['valid']
    page=client.get('/api/model-profiles/'+profile['id']+'/connection-history').json()
    assert page['items']==[record] and page['total']==1

@pytest.mark.parametrize('update,code',[
    ({'status':302},'provider_status'),({'status':401},'provider_status'),
    ({'encoding':'gzip'},'response_encoding'),({'type':'text/plain'},'response_content_type'),
    ({'length':1024*1024+1},'response_byte_budget'),({'raw':b'{"choices":[],"choices":[]}'},'response_shape'),
    ({'body':{'choices':[{'message':{'role':'assistant','content':'unexpected answer'}}]}},'response_shape'),
])
def test_rejects_provider_redirect_encoding_budget_and_shape_without_retries(client,provider,monkeypatch,update,code):
    profile=setup(client,provider,monkeypatch);provider[2].update(update)
    response=check(client,profile);assert response.status_code==200,response.text
    record=response.json()['query'];assert record['status']=='failed' and record['result_code']==code
    assert check(client,profile).json()['query']==record and len(provider[1])==1

def test_stale_credentials_block_before_any_provider_request(client,provider,monkeypatch):
    profile=setup(client,provider,monkeypatch);monkeypatch.setenv('OWNED_MODEL_KEY','rotated-owned-model-key')
    assert check(client,profile).status_code==409
    assert provider[1]==[] and client.app.state.store.all('model_connection_checks')==[]

@pytest.mark.parametrize('usage,expected',[
    (None,'missing'),({'prompt_tokens':5},'partial'),({'prompt_tokens':True},'invalid'),
    ({'prompt_tokens':5,'completion_tokens':3,'total_tokens':9},'invalid'),
])
def test_connection_success_does_not_invent_or_validate_invalid_usage(client,provider,monkeypatch,usage,expected):
    profile=setup(client,provider,monkeypatch);provider[2]['body']['usage']=usage
    record=check(client,profile).json()['query']
    assert record['status']=='completed' and record['tokens']['status']==expected
    assert record['cost']['amount'] is None and len(provider[1])==1

def test_pricing_is_captured_before_dns_and_stores_no_quote_urls(client,provider,monkeypatch):
    import aegis.model_connection as module
    profile=setup(client,provider,monkeypatch)
    quote={'model':profile['model'],'provider':provider[0],'currency':'USD','input_per_million':'1',
           'output_per_million':'2','source_url':'https://owned-prices.invalid/source','as_of':'2020-01-01','basis':'flat_text_tokens'}
    monkeypatch.setenv('AEGIS_LLM_PRICES',json.dumps([quote]));original=module.resolve
    def changed(*args,**kwargs):
        address=original(*args,**kwargs);monkeypatch.setenv('AEGIS_LLM_PRICES',json.dumps([{**quote,'input_per_million':'999'}]));return address
    monkeypatch.setattr(module,'resolve',changed)
    record=check(client,profile).json()['query']
    assert record['cost']=={'status':'estimated','amount':'0.000011','currency':'USD'}
    assert record['pricing']['input_per_million']=='1'
    raw=json.dumps(record);assert provider[0] not in raw and quote['source_url'] not in raw and 'owned-model-secret' not in raw
    assert client.app.state.store.audit_integrity()['valid']


@pytest.mark.parametrize('mutation',['credential','profile','role'])
def test_connection_rechecks_review_after_dns_before_any_post(client,provider,monkeypatch,mutation):
    import aegis.model_connection as module
    profile=setup(client,provider,monkeypatch);original=module.resolve
    def changed(*args,**kwargs):
        address=original(*args,**kwargs)
        if mutation=='credential':monkeypatch.setenv('OWNED_MODEL_KEY','owned-rotated-key')
        elif mutation=='profile':assert change(client,profile,model='owned-revised-model').status_code==200
        else:
            store=client.app.state.store;actor=store.user(username='admin');store.update_user(actor['id'],role='operator')
        return address
    monkeypatch.setattr(module,'resolve',changed)
    response=check(client,profile);assert response.status_code==200,response.text
    assert response.json()['query']['status']=='blocked' and response.json()['query']['result_code']=='profile_review_changed'
    assert not provider[1] and client.app.state.store.audit_integrity()['valid']


@pytest.mark.parametrize('phase',['start','finish'])
def test_connection_audit_failure_rolls_back_and_never_redispatches_uncertain_attempt(client,provider,monkeypatch,phase):
    from aegis.model_connection import ConnectionInput
    profile=setup(client,provider,monkeypatch);store=client.app.state.store;actor=store.user(username='admin')
    original=store.event;calls=[]
    def fail(*args,**kwargs):
        calls.append(args)
        if len(calls)==(1 if phase=='start' else 2):raise RuntimeError('owned connection audit failure')
        return original(*args,**kwargs)
    monkeypatch.setattr(store,'event',fail)
    data=ConnectionInput(expected_revision=profile['revision'],request_id='owned-connection-check-001')
    with pytest.raises(RuntimeError,match='owned connection audit failure'):
        client.app.state.model_connection.read(profile['id'],data,actor)
    monkeypatch.setattr(store,'event',original)
    assert store.count('model_connection_checks')==(0 if phase=='start' else 1)
    assert len(provider[1])==(0 if phase=='start' else 1)
    if phase=='finish':
        assert check(client,profile).json()['query']['status']=='started' and len(provider[1])==1
        assert client.app.state.model_connection.recover()
        record=check(client,profile).json()['query']
        assert record['status']=='unknown' and record['result_code']=='process_receipt_unconfirmed' and record['tokens']['status']=='missing'
        assert not client.app.state.model_connection.recover() and len(provider[1])==1
    assert store.audit_integrity()['valid'] and not store.all('traffic') and not store.all('llm_calls')



def test_native_connection_fences_owner_loss_and_restart_recovers_without_second_post(client,provider,monkeypatch,postgres,tmp_path):
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
        pending=pool.submit(check,client,profile)
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
        receipt=check(restarted,profile).json()
        assert receipt['replayed'] and receipt['query']['status']=='unknown'
        assert receipt['query']['result_code']=='process_receipt_unconfirmed' and receipt['query']['tokens']['status']=='missing'
        assert restarted.app.state.store.audit_integrity()['valid']
        assert not restarted.app.state.store.all('traffic') and not restarted.app.state.store.all('llm_calls')
    assert len(provider[1])==1



def test_active_uuid_replays_without_a_second_post_and_other_requests_are_bounded(client,provider,monkeypatch):
    profile=setup(client,provider,monkeypatch);provider[4].clear()
    with ThreadPoolExecutor(max_workers=1) as pool:
        first=pool.submit(check,client,profile);assert provider[3].wait(4)
        duplicate=check(client,profile);assert duplicate.status_code==200 and duplicate.json()['replayed'] and duplicate.json()['query']['status']=='started'
        assert check(client,profile,request_id='owned-connection-check-002').status_code==429
        provider[4].set();result=first.result(timeout=5)
    assert result.json()['query']['status']=='completed' and len(provider[1])==1
    assert check(client,profile).json()['query']==result.json()['query']



@pytest.mark.parametrize('stop_kind',['connection','server'])
def test_stopping_a_pending_connection_waits_for_owned_request_and_records_uncertainty(client,provider,monkeypatch,stop_kind):
    profile=setup(client,provider,monkeypatch);provider[4].clear()
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(check,client,profile);assert provider[3].wait(4)
        if stop_kind=='server':client.app.state.shutdown_requested.set()
        else:
            client.app.state.model_connection.close()
            assert not client.app.state.shutdown_requested.is_set()
        result=pending.result(timeout=4)
    assert result.status_code==200,result.text
    assert result.json()['query']['status']=='unknown' and result.json()['query']['result_code']=='request_stopped'
    assert len(provider[1])==1 and not client.app.state.store.all('traffic')
    provider[4].set()



def test_connection_request_validation_and_stale_profile_or_role_never_dispatch(client,provider,monkeypatch):
    profile=setup(client,provider,monkeypatch)
    assert check(client,profile,request_id='short').status_code==422
    assert check(client,profile,expected_revision=True).status_code==422
    assert check(client,profile,expected_revision=0).status_code==409
    store=client.app.state.store;actor=store.user(username='admin');store.update_user(actor['id'],role='operator')
    assert check(client,profile).status_code==401
    from aegis.model_connection import ConnectionInput
    with pytest.raises(HTTPException) as caught:client.app.state.model_connection.read(profile['id'],ConnectionInput(expected_revision=1,request_id='owned-connection-check-001'),actor)
    assert caught.value.status_code==403 and not provider[1] and store.count('model_connection_checks')==0




def test_connection_sql_history_pages_and_explicit_synthetic_exhaustion_boundary(client,provider,monkeypatch):
    profile=setup(client,provider,monkeypatch)
    for n in range(26):
        response=check(client,profile,request_id='owned-connection-page-'+str(n));assert response.status_code==200,response.text
        assert response.json()['query']['status']=='completed'
    path='/api/model-profiles/'+profile['id']+'/connection-history'
    first=client.get(path).json();assert len(first['items'])==25 and first['total']==26 and first['has_more']
    second=client.get(path,params={'offset':25,'snapshot':first['snapshot']}).json()
    assert len(second['items'])==1 and not second['has_more']
    assert len({row['id'] for row in first['items']+second['items']})==26
    assert client.get(path,params={'limit':26}).status_code==422
    store=client.app.state.store;sample=first['items'][0]
    # Synthetic rows exercise the 200-record rejection boundary, not174 real POSTs.
    store.put_many([('model_connection_checks',{**sample,'id':'synthetic-boundary-'+str(n)}) for n in range(174)])
    before=store.count('model_connection_checks');assert before==200
    assert check(client,profile,request_id='owned-connection-overflow-001').status_code==409
    assert store.count('model_connection_checks')==before and len(provider[1])==26
    assert not store.all('traffic') and not store.all('llm_calls')
