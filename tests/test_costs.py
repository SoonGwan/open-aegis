import json
import time
import pytest
from aegis.costs import price_snapshot, estimate
from aegis.llm import token_usage
from aegis.store import Store
from aegis.usage import usage_summary
from tests.test_validation import client
from tests.test_conversation_ai import ai, PATH, PAYLOAD


def quote(**changes):
    return {'model':'owned-ai-model', 'provider':'https://api.openai.com/v1',
        'currency':'USD', 'input_per_million':'1.25', 'output_per_million':'2.5',
        'source_url':'https://prices-fixture.invalid/synthetic-only', 'as_of':'2026-01-01',
        'basis':'flat_text_tokens', **changes}


def configure(monkeypatch, **changes):
    row=quote(**changes)
    monkeypatch.setenv('AEGIS_LLM_PRICES',json.dumps([row]))
    return row


def test_exact_cost_and_call_time_price_snapshot(monkeypatch):
    row=configure(monkeypatch)
    at=time.time()
    snapshot=price_snapshot(row['model'],row['provider'],at)
    configure(monkeypatch,input_per_million='999')
    cost=estimate(token_usage({'prompt_tokens':3,'completion_tokens':2,'total_tokens':5}),snapshot,at)
    assert cost=={'status':'estimated','quote':row,'amount':'0.00000875'}
    zero=estimate(token_usage({'prompt_tokens':0,'completion_tokens':0,'total_tokens':0}),snapshot,at)
    assert zero['amount']=='0'
    assert estimate(token_usage(None),snapshot,at)['amount'] is None


@pytest.mark.parametrize('changes',[
    {'input_per_million':1.25}, {'input_per_million':'NaN'}, {'input_per_million':'-1'},
    {'input_per_million':'1e2'}, {'input_per_million':'0.0000000001'},
    {'output_per_million':'1000001'}, {'currency':'XYZ'}, {'currency':{}},
    {'source_url':'https://prices.invalid/?api_key=DO-NOT-PERSIST'},
    {'source_url':'https://user:DO-NOT-PERSIST@prices.invalid/'},
    {'as_of':'9999-01-01'}, {'as_of':'2026-02-31'}, {'basis':'unreviewed-tier'},
    {'provider':'https://api.openai.com/v1/'}, {'unexpected':'DO-NOT-PERSIST'},
])
def test_bad_price_configuration_does_not_become_zero_or_leak(monkeypatch,changes):
    configure(monkeypatch,**changes)
    result=price_snapshot('owned-ai-model','https://api.openai.com/v1',time.time())
    assert result=={'status':'invalid_configuration','quote':None}
    assert 'DO-NOT-PERSIST' not in json.dumps(result)


def test_unconfigured_unpriced_and_duplicate_identity_are_distinct(monkeypatch):
    monkeypatch.setenv('AEGIS_LLM_PRICES','[]')
    assert price_snapshot('owned','https://other.invalid/',time.time())['status']=='unconfigured'
    row=configure(monkeypatch)
    assert price_snapshot(row['model'],'https://other.invalid/',time.time())['status']=='model_unpriced'
    monkeypatch.setenv('AEGIS_LLM_PRICES',json.dumps([row,row]))
    assert price_snapshot(row['model'],row['provider'],time.time())['status']=='invalid_configuration'
    monkeypatch.setenv('AEGIS_LLM_PRICES','[{"model":"a","model":"b"}]')
    assert price_snapshot('b',row['provider'],time.time())['status']=='invalid_configuration'
    monkeypatch.setenv('AEGIS_LLM_PRICES','['*1200+']'*1200)
    assert price_snapshot('b',row['provider'],time.time())['status']=='invalid_configuration'


def record(id, row, *, prompt=3, completion=2, status='reported'):
    at=time.time()
    tokens=token_usage({'prompt_tokens':prompt,'completion_tokens':completion,'total_tokens':prompt+completion})
    if status=='missing': tokens=token_usage(None)
    return {'id':id,'llm_usage':{'model':row['model'],'observed_at':at,'outcome':'accepted',
        'tokens':tokens,'cost':estimate(tokens,{'status':'quoted','quote':row},at)}}


def test_cost_aggregate_revalidates_and_keeps_currencies_separate(tmp_path):
    store=Store(tmp_path/'aegis.db')
    good=record('good',quote())
    changed=record('changed',quote());changed['llm_usage']['cost']['amount']='0'
    wrong=record('wrong-model',quote());wrong['llm_usage']['model']='other'
    mislabeled=record('mislabeled',quote())
    mislabeled['llm_usage']['cost'].update(status='usage_unavailable',amount=None)
    store.put_many([('tasks',row) for row in [good,record('krw',quote(currency='KRW')),
        record('missing',quote(),status='missing'),changed,wrong,mislabeled,
        {'id':'historic','llm_usage':{'observed_at':time.time(),'tokens':token_usage(None)}}]])
    result=usage_summary(store,source='all')['costs']
    assert result['states']['estimated']==2 and result['states']['invalid_record']==3
    assert result['states']['unrecorded']==1 and result['states']['usage_unavailable']==1
    assert result['totals']==[{'currency':'KRW','amount':'0.00000875','calls':1},
                              {'currency':'USD','amount':'0.00000875','calls':1}]


def test_cost_totals_do_not_round_large_plus_tiny_values(tmp_path):
    store=Store(tmp_path/'aegis.db')
    large=record('large',quote(input_per_million='1000000'),prompt=9007199254740991,completion=0)
    tiny=record('tiny',quote(input_per_million='0.000000001'),prompt=1,completion=0)
    store.put_many([('tasks',large),('tasks',tiny)])
    assert usage_summary(store)['costs']['totals'][0]['amount']=='9007199254740991.000000000000001'


def test_real_exchange_cost_retry_uses_original_quote_and_audit(client,ai,monkeypatch):
    row=configure(monkeypatch)
    reply=client.post(PATH,json=PAYLOAD).json()
    assert reply['assistant_generation']['cost']['amount']=='0.000035'
    configure(monkeypatch,input_per_million='100')
    assert client.post(PATH,json=PAYLOAD).json()==reply
    summary=client.get('/api/llm/usage?source=conversation').json()
    assert summary['costs']['totals']==[{'currency':'USD','amount':'0.000035','calls':1}]
    assert client.app.state.store.events(task_id='chat-task')[0]['detail']['cost']['quote']==row


def test_planner_price_is_captured_before_provider_response(tmp_path,monkeypatch):
    from aegis.engine import Engine
    configure(monkeypatch)
    monkeypatch.setenv('AEGIS_LLM_API_KEY','owned-key')
    monkeypatch.setenv('AEGIS_LLM_MODEL','owned-ai-model')
    def provider(*args,**kwargs):
        configure(monkeypatch,input_per_million='100')
        return {'choices':[{'message':{'content':'{"checks":["security_headers"]}'}}],
            'usage':{'prompt_tokens':3,'completion_tokens':2,'total_tokens':5}}
    monkeypatch.setattr('aegis.engine.completion',provider)
    store=Store(tmp_path/'aegis.db')
    task={'id':'owned','checks':['security_headers'],'planner':'ai','goal':'Owned','scope_snapshot':[]}
    store.put('tasks',task)
    engine=Engine(store)
    try:
        engine.plan(task)
        metadata=store.get('tasks','owned')['llm_usage']
        assert metadata['cost']['amount']=='0.00000875'
        assert metadata['cost']==store.events(task_id='owned')[-1]['detail']['cost']
        assert metadata['started_at']<=metadata['observed_at']
    finally:
        engine.shutdown()
