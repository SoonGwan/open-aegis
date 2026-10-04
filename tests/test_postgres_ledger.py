"""Actual PostgreSQL attempt lifecycle and exact usage snapshots."""
import json
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from aegis import call_ledger,postgres_store
from aegis.costs import estimate
from aegis.llm import token_usage
from aegis.usage import usage_summary
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_store import stores,seed
from tests.test_usage_summary import call,message
from tests.test_costs import quote,record

PRICE={'status':'unconfigured','quote':None}


def observed(store,source='conversation',task='owned'):
    at=time.time()
    id=call_ledger.start(store,source,task,'owned-model','https://provider.invalid/v1?private=hidden',at,PRICE)
    tokens=token_usage({'prompt_tokens':3,'completion_tokens':2,'total_tokens':5})
    detail={'call_id':id,'model':'owned-model','started_at':at,'observed_at':time.time(),'outcome':'accepted','tokens':tokens,'cost':estimate(tokens,PRICE,at)}
    call_ledger.observe(store,id,detail)
    return id,detail


def test_native_attempt_success_replay_abandon_and_usage(stores):
    _,pg=stores
    id,detail=observed(pg)
    assert pg.get('llm_calls',id)['provider_origin']=='https://provider.invalid'
    question={'id':'q','role':'user','task_id':'owned','content':'private question'}
    reply={'id':'r','role':'assistant','task_id':'owned','content':'private reply','assistant_generation':detail}
    pg.put_message_exchange(question,reply);pg.put_message_exchange(question,reply)
    call_ledger.abandon(pg,id)
    assert pg.get('llm_calls',id)['state']=='committed'
    lost,lost_detail=observed(pg);call_ledger.abandon(pg,lost);call_ledger.abandon(pg,lost)
    row=usage_summary(pg,source='all',ledger='attempts')
    assert row['calls']==2 and row['attempt_states']['committed']==1 and row['attempt_states']['uncommitted']==1
    assert row['reported_tokens']['total_tokens']=='10'
    assert usage_summary(pg,source='all')['calls']==1
    assert pg.audit_integrity()['events']==6
    assert 'private question' not in json.dumps(row) and 'private reply' not in json.dumps(row)


def test_native_attempt_phase_audit_failures_roll_back(stores,monkeypatch):
    _,pg=stores;original=postgres_store.append_event
    def fail(db,values):
        original(db,values)
        raise RuntimeError('Owned phase audit failure')
    monkeypatch.setattr(postgres_store,'append_event',fail)
    with pytest.raises(RuntimeError):call_ledger.start(pg,'planner','owned','owned-model','https://owned.invalid',time.time(),PRICE)
    assert pg.count('llm_calls')==0 and pg.audit_integrity()['events']==0
    monkeypatch.setattr(postgres_store,'append_event',original)
    at=time.time();id=call_ledger.start(pg,'planner','owned','owned-model','https://owned.invalid',at,PRICE)
    before=pg.get('llm_calls',id)
    detail={'model':'owned-model','started_at':at,'observed_at':time.time(),'outcome':'accepted','tokens':token_usage(None),'cost':estimate(token_usage(None),PRICE,at)}
    monkeypatch.setattr(postgres_store,'append_event',fail)
    with pytest.raises(RuntimeError):call_ledger.observe(pg,id,detail)
    assert pg.get('llm_calls',id)==before
    with pytest.raises(RuntimeError):call_ledger.abandon(pg,id)
    assert pg.get('llm_calls',id)==before and pg.audit_integrity()['events']==1
    with pytest.raises(RuntimeError):call_ledger.recover(pg)
    assert pg.get('llm_calls',id)==before and pg.audit_integrity()['events']==1


def test_native_recovery_batches_preserve_observations_and_are_idempotent(stores,monkeypatch):
    _,pg=stores
    id,detail=observed(pg,'planner')
    template=pg.get('llm_calls',id)
    pg.put_many([('llm_calls',{**template,'id':'unfinished-'+str(i),'state':'started','tokens':token_usage(None)}) for i in range(205)])
    settled={**template,'id':'settled','state':'uncommitted'};pg.put('llm_calls',settled)
    original=postgres_store.append_event;seen=[]
    def fail_second_batch(db,values):
        seen.append(values)
        original(db,values)
        if len(seen)==101:raise RuntimeError('Owned second recovery batch failure')
    monkeypatch.setattr(postgres_store,'append_event',fail_second_batch)
    with pytest.raises(RuntimeError):call_ledger.recover(pg)
    assert pg.page('llm_calls',filters={'state':'interrupted'})['total']==100
    assert pg.audit_integrity()['events']==102
    monkeypatch.setattr(postgres_store,'append_event',original)
    call_ledger.recover(pg)
    assert pg.page('llm_calls',filters={'state':'interrupted'})['total']==206
    assert pg.get('llm_calls',id)['tokens']==detail['tokens'] and pg.get('llm_calls','settled')==settled
    before=pg.audit_integrity();call_ledger.recover(pg);assert pg.audit_integrity()==before
    assert usage_summary(pg,source='all',ledger='attempts')['attempt_states']['interrupted']==206


def test_concurrent_observers_only_one_transition_commits(stores,postgres):
    _,pg=stores;at=time.time()
    id=call_ledger.start(pg,'planner','owned','owned-model','https://owned.invalid',at,PRICE)
    detail={'model':'owned-model','started_at':at,'observed_at':time.time(),'outcome':'accepted','tokens':token_usage(None),'cost':estimate(token_usage(None),PRICE,at)}
    other=postgres_store.PostgresStore(postgres['dsn'],pg.schema)
    def observe(index):
        try:call_ledger.observe(pg if index==0 else other,id,detail);return 'observed'
        except RuntimeError:return 'rejected'
    with ThreadPoolExecutor(max_workers=2) as executor:results=list(executor.map(observe,range(2)))
    assert sorted(results)==['observed','rejected'] and pg.audit_integrity()['events']==2


@pytest.mark.parametrize('source',['planner','conversation','all'])
@pytest.mark.parametrize('ledger',['persisted','attempts'])
def test_usage_sources_windows_invalid_values_and_cost_parity(stores,monkeypatch,source,ledger):
    at=time.time();monkeypatch.setattr('aegis.usage.time.time',lambda:at+1)
    rows=[('tasks',call('plan',outcome='invalid_plan',at=at)),('messages',message('chat',outcome='invalid_answer',at=at)),
          ('messages',message('bad',prompt=True,at=at)),('tasks',call('wrong-total',total=8,at=at)),
          ('tasks',call('partial','partial',completion=None,total=None,at=at)),('tasks',call('missing','missing',prompt=None,completion=None,total=None,at=at)),
          ('messages',message('old',at=at-10*86400)),('messages',message('future',at=at+86400)),('tasks',call('bad-time',at='untrusted')),
          ('tasks',record('large',quote(input_per_million='1000000'),prompt=9007199254740991,completion=0)),
          ('tasks',record('tiny',quote(input_per_million='0.000000001'),prompt=1,completion=0))]
    for kind,item in list(rows):
        metadata=item.get('llm_usage',item.get('assistant_generation'))
        rows.append(('llm_calls',{'id':'attempt-'+item['id'],'source':'planner' if kind=='tasks' else 'conversation','state':'uncommitted','started_at':metadata['observed_at'],**metadata}))
    seed(stores,rows);sqlite,pg=stores
    monkeypatch.setattr(pg,'all',lambda *args:pytest.fail('Full record materialization'))
    for days in (None,7,30):assert usage_summary(pg,days,source=source,ledger=ledger)==usage_summary(sqlite,days,source=source,ledger=ledger)


def test_native_exact_token_totals_above_int64_and_float_range(stores,monkeypatch):
    at=time.time();monkeypatch.setattr('aegis.usage.time.time',lambda:at+1)
    maximum=9007199254740991
    seed(stores,[('messages',message(str(i),prompt=maximum,completion=0,total=maximum,at=at)) for i in range(2100)])
    sqlite,pg=stores
    result=usage_summary(pg,source='all')
    assert result==usage_summary(sqlite,source='all') and result['reported_tokens']['total_tokens']==str(maximum*2100)


def test_native_usage_cost_and_tokens_share_snapshot_during_write(stores,monkeypatch):
    at=time.time();monkeypatch.setattr('aegis.usage.time.time',lambda:at+1)
    seed(stores,[('tasks',record('first',quote())),('tasks',record('second',quote()))])
    sqlite,pg=stores;expected=usage_summary(sqlite,source='all')
    from aegis.costs import CostSummary
    original=CostSummary.step;changed=[]
    def concurrent_write(self,metadata):
        if not changed:
            changed.append(True)
            pg.patch('tasks','second',llm_usage=record('second',quote(),prompt=100,completion=0)['llm_usage'])
        return original(self,metadata)
    monkeypatch.setattr(CostSummary,'step',concurrent_write)
    assert usage_summary(pg,source='all')==expected and changed
    assert pg.get('tasks','second')['llm_usage']['tokens']['total_tokens']==100
    after=usage_summary(pg,source='all')
    assert after['reported_tokens']['total_tokens']=='105'
    assert expected['costs']['totals']==[{'currency':'USD','amount':'0.0000175','calls':2}]
    assert after['costs']['totals']==[{'currency':'USD','amount':'0.00013375','calls':2}]


def test_actual_local_provider_draft_has_durable_start_and_native_commit(stores,monkeypatch):
    import threading
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from aegis.conversation_ai import draft
    _,pg=stores;seen=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert payload['model']=='owned-native-model' and self.path=='/v1/chat/completions'
            assert pg.page('llm_calls',filters={'state':'started'})['total']==1
            seen.append(payload)
            body=json.dumps({'choices':[{'message':{'content':json.dumps({'blocks':[{'text':'합성 기록 초안','citations':['T1']}]})}}],
                             'usage':{'prompt_tokens':3,'completion_tokens':2,'total_tokens':5}}).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    monkeypatch.setenv('AEGIS_LLM_MODEL','owned-native-model');monkeypatch.setenv('AEGIS_LLM_API_KEY','owned-native-test-key')
    monkeypatch.setenv('AEGIS_LLM_BASE_URL',f'http://127.0.0.1:{server.server_port}/v1')
    monkeypatch.setenv('AEGIS_LLM_PRICES','[]')
    summary={'content':'합성 요약','provenance':{'citations':[{'label':'T1','title':'소유한 합성 작업','snapshot':{'id':'owned'}}]}}
    owner=pg.acquire_runtime()
    try:
        reply=draft(summary,'합성 질문',store=pg,task_id='owned',actor_id=None,allow_local=True)
        assert reply['assistant_generation']['outcome']=='accepted' and len(seen)==1
        id=reply['assistant_generation']['call_id'];assert pg.get('llm_calls',id)['state']=='observed'
        reply.update(id='r',role='assistant',task_id='owned')
        pg.put_message_exchange({'id':'q','role':'user','task_id':'owned','content':'합성 질문'},reply)
        assert pg.get('llm_calls',id)['state']=='committed' and pg.audit_integrity()['events']==3
        assert usage_summary(pg,source='all',ledger='attempts')['reported_tokens']['total_tokens']=='5'
        assert usage_summary(pg,source='all')['reported_tokens']['total_tokens']=='5'
        assert 'owned-native-test-key' not in json.dumps(pg.all('llm_calls'))
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
        owner.close()
