"""Explicit fixed-message inference checks; no task or target input is sent."""
import hashlib,json
from urllib.parse import urlsplit
from .provider_checks import ProviderCheck,CheckInput as ConnectionInput,CheckError
from .model_profiles import ProfileUnavailable
from .remote_mcp import _decode
from .network import PinnedHTTP,PinnedHTTPS,resolve
from .runtime import RequestGuard
from .llm import token_usage
from .provider_protocol import inference_request,inference_response
from .costs import price_snapshot,estimate

KIND='model_connection_checks'
MAX_BYTES=1024*1024
MARKER='AEGIS_OK'

class ConnectionCheck(ProviderCheck):
    kind=KIND
    identity='aegis-model-connection-v1'
    label='제공자 모델 연결 시험'
    success_code='inference_response_valid'

    def initial(self):return {'tokens':token_usage(None),'cost':{'status':'usage_unavailable','amount':None,'currency':None}}

    def context(self,prepared,record):
        snapshot=price_snapshot(record['profile_snapshot']['model'],prepared[0],record['created_at'])
        quote=snapshot.get('quote')
        return {'pricing':{'status':snapshot['status'],**({key:quote[key] for key in
                  ('currency','input_per_million','output_per_million','as_of','basis')} if quote else {})}}

    def result(self,value,record):
        tokens=value if isinstance(value,dict) else token_usage(None)
        pricing=record.get('pricing',{'status':'unconfigured'})
        quote=None
        if pricing['status']=='quoted':
            quote={key:pricing[key] for key in ('currency','input_per_million','output_per_million','as_of','basis')}
            quote.update(model=record['profile_snapshot']['model'],provider='https://pricing.invalid',source_url='https://pricing.invalid')
        cost=estimate(tokens,{'status':pricing['status'],'quote':quote},record['created_at'])
        return {'tokens':tokens,'cost':{'status':cost['status'],'amount':cost['amount'],'currency':quote['currency'] if quote else None}}

    def fetch(self,record,prepared,control):
        base,key,local,_=prepared;parsed=urlsplit(base)
        port=parsed.port or (443 if parsed.scheme=='https' else 80)
        address=resolve(parsed.hostname,port,allow_private=local,control=control,timeout=control.timeout(4))[0]
        connection=(PinnedHTTPS if parsed.scheme=='https' else PinnedHTTP)(parsed.hostname,port,address,timeout=control.timeout(8))
        try:
            with self.store.read_transaction() as db:
                profile,current,_=self.profile(record['profile_id'],record['profile_revision'],record['actor'],db)
                if current!=prepared or profile['fingerprint']!=record['profile_fingerprint']:raise ProfileUnavailable('Model profile changed')
            payload={'model':record['profile_snapshot']['model'],'messages':[{'role':'user','content':'Reply exactly '+MARKER+'.'}],
                     'max_tokens':16,'stream':False}
            protocol=record['profile_snapshot'].get('provider_protocol','openai')
            suffix,authentication,payload=inference_request(protocol,key,payload)
            with RequestGuard(connection,control,8) as guard:
                connection.request('POST',parsed.path.rstrip('/')+suffix,body=json.dumps(payload).encode(),
                                   headers={**authentication,'Content-Type':'application/json','Accept':'application/json','Accept-Encoding':'identity'})
                guard.sock=connection.sock;response=connection.getresponse()
                if response.status!=200:raise CheckError('provider_status',response.status)
                if response.getheader('Content-Encoding','identity').lower()!='identity':raise CheckError('response_encoding',200)
                if response.getheader('Content-Type','').split(';')[0].strip().lower()!='application/json':raise CheckError('response_content_type',200)
                if response.length is not None and response.length>MAX_BYTES:raise CheckError('response_byte_budget',200)
                raw=response.read(MAX_BYTES+1)
                if len(raw)>MAX_BYTES:raise CheckError('response_byte_budget',200)
            control.check()
            try:
                body=inference_response(protocol,_decode(raw));choices=body['choices']
                if not isinstance(choices,list) or len(choices)!=1:raise ValueError()
                message=choices[0]['message'];content=message['content']
                if (message.get('role')!='assistant' or not isinstance(content,str) or len(content)>128
                        or content.strip()!=MARKER or message.get('tool_calls') or message.get('function_call')):raise ValueError()
                return token_usage(body.get('usage')),hashlib.sha256(raw).hexdigest()
            except (ValueError,TypeError,KeyError,AttributeError):raise CheckError('response_shape',200) from None
        finally:connection.close()
