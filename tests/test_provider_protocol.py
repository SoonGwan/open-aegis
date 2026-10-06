"""Native wire selection is explicit; reported usage never acquires an invented total."""
import copy,json,subprocess,sys
from pathlib import Path
import aegis
import pytest
from aegis.provider_protocol import inference_request,inference_response,catalog_request,catalog_response
from aegis.llm import token_usage
from aegis.model_profiles import Destinations

PAYLOAD={'model':'owned-native-model','temperature':0,'messages':[{'role':'system','content':'Owned instructions'},{'role':'user','content':'Owned goal'}]}
REPLY={'type':'message','role':'assistant','stop_reason':'end_turn','content':[{'type':'text','text':'AEGIS_OK'}],'usage':{'input_tokens':5,'output_tokens':3}}


def test_maintenance_store_import_does_not_require_application_dependencies(tmp_path):
    package_root=Path(aegis.__file__).resolve().parent.parent
    result=subprocess.run([sys.executable,'-I','-S','-c',
        'import sys;sys.path.insert(0,sys.argv[1]);'
        'from aegis.store import Store;from aegis.llm import token_usage;'
        'assert token_usage(None)["status"]=="missing";'
        'store=Store(sys.argv[2]);store.put("notes",{"id":"owned-import","title":"fixture"});'
        'assert store.get("notes","owned-import")["title"]=="fixture"',
        str(package_root),str(tmp_path/'aegis.db')],cwd=tmp_path,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr


def test_native_wire_is_text_only_and_explicitly_bounded():
    original=copy.deepcopy(PAYLOAD);suffix,headers,body=inference_request('anthropic','owned-protocol-key',PAYLOAD)
    assert suffix=='/messages' and headers=={'x-api-key':'owned-protocol-key','anthropic-version':'2023-06-01'}
    assert body=={'model':'owned-native-model','system':'Owned instructions','messages':[{'role':'user','content':'Owned goal'}],'max_tokens':4096,'stream':False}
    assert PAYLOAD==original
    short={**PAYLOAD,'max_tokens':16,'stream':False}
    assert inference_request('anthropic','owned-protocol-key',short)[2]['max_tokens']==16
    assert catalog_request('anthropic','owned-protocol-key')[0]=='/models?limit=256'


def test_default_wire_and_response_are_not_reinterpreted():
    assert inference_request('openai','owned-protocol-key',PAYLOAD)==('/chat/completions',{'Authorization':'Bearer owned-protocol-key'},PAYLOAD)
    assert inference_response('openai',REPLY) is REPLY
    assert catalog_request('openai','owned-protocol-key')[0]=='/models'
    assert catalog_response('openai',{'data':[]})=={'data':[]}

@pytest.mark.parametrize('patch',[
    {'max_tokens':True},{'max_tokens':0},{'max_tokens':4097},{'max_tokens':'16'},
    {'stream':True},{'stream':'false'},{'tools':[]},{'messages':[]},{'messages':[{'role':'tool','content':'ignored'}]},
    {'messages':[{'role':'user','content':[{'type':'text','text':'ignored'}]}]},
    {'messages':[{'role':'system','content':'only system'}]},
    {'messages':[{'role':'user','content':'goal','tool_calls':[]}]},
])
def test_native_rejects_unsupported_actions_before_transport(patch):
    with pytest.raises(ValueError):inference_request('anthropic','owned-protocol-key',{**PAYLOAD,**patch})

@pytest.mark.parametrize('patch',[
    {'role':'user'},{'type':'error'},{'stop_reason':'tool_use'},{'stop_reason':'max_tokens'},
    {'stop_details':{'type':'refusal'}},{'content':[]},
    {'content':[{'type':'tool_use','name':'command','input':{}}]},
    {'content':[{'type':'text','text':'allowed'},{'type':'thinking','thinking':'ignored'}]},
    {'content':[{'type':'text','text':42}]},
])
def test_native_rejects_refusal_tools_and_nonfinal_text(patch):
    with pytest.raises(ValueError):inference_response('anthropic',{**REPLY,**patch})

@pytest.mark.parametrize('usage,status,prompt,output',[
    (None,'missing',None,None),({'input_tokens':5,'output_tokens':3},'partial',5,3),
    ({'input_tokens':False,'output_tokens':3},'invalid',None,3),
    ({'input_tokens':9007199254740992,'output_tokens':3},'invalid',None,3),
    ({'input_tokens':5},'partial',5,None),('invalid','invalid',None,None),
    ({'input_tokens':5,'output_tokens':3,'total_tokens':8,'cache_read_input_tokens':7},'partial',5,3),
])
def test_native_usage_preserves_reported_counters_without_total_or_cache_price(usage,status,prompt,output):
    body=inference_response('anthropic',{**REPLY,'usage':usage})
    assert token_usage(body['usage'])=={'status':status,'prompt_tokens':prompt,'completion_tokens':output,'total_tokens':None}

@pytest.mark.parametrize('has_more',[True,None,0,'false'])
def test_native_catalog_never_labels_an_incomplete_page_complete(has_more):
    with pytest.raises(ValueError):catalog_response('anthropic',{'data':[],'has_more':has_more})
    assert catalog_response('anthropic',{'data':[],'has_more':False})['data']==[]


def test_protocol_configuration_is_declared_not_inferred(monkeypatch):
    definition={'id':'native','name':'Owned native','base_env':'OWNED_NATIVE_BASE','key_env':'OWNED_NATIVE_KEY','protocol':'anthropic'}
    monkeypatch.setenv('AEGIS_MODEL_DESTINATIONS',json.dumps([definition]))
    assert Destinations().items['native'].protocol=='anthropic'
    monkeypatch.setenv('AEGIS_MODEL_DESTINATIONS',json.dumps([{**definition,'protocol':'guess-from-model'}]))
    with pytest.raises(RuntimeError):Destinations()
    monkeypatch.setenv('AEGIS_MODEL_DESTINATIONS',json.dumps([{k:v for k,v in definition.items() if k!='protocol'}]))
    assert Destinations().items['native'].protocol=='openai'


def test_default_review_binding_survives_explicit_default_but_native_requires_new_review(monkeypatch):
    definition={'id':'native','name':'Owned recipient','base_env':'OWNED_NATIVE_BASE','key_env':'OWNED_NATIVE_KEY'}
    monkeypatch.setenv('OWNED_NATIVE_BASE','https://example.invalid/v1');monkeypatch.setenv('OWNED_NATIVE_KEY','owned-protocol-key')
    monkeypatch.setenv('AEGIS_MODEL_DESTINATIONS',json.dumps([definition]));baseline=Destinations().prepare('native','owned-model')
    monkeypatch.setenv('AEGIS_MODEL_DESTINATIONS',json.dumps([{**definition,'protocol':'openai'}]));assert Destinations().prepare('native','owned-model')==baseline
    monkeypatch.setenv('AEGIS_MODEL_DESTINATIONS',json.dumps([{**definition,'protocol':'anthropic'}]));native=Destinations().prepare('native','owned-model')
    assert native[:3]==baseline[:3] and native[3]!=baseline[3] and len(native)==4
