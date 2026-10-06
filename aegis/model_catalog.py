"""Explicit bounded provider model catalog reads."""
import hashlib
from urllib.parse import urlsplit
from .model_profiles import ProfileUnavailable
from .remote_mcp import _decode
from .network import PinnedHTTP,PinnedHTTPS,resolve
from .runtime import RequestGuard
from .provider_protocol import catalog_request,catalog_response
from .provider_checks import ProviderCheck,CheckInput as CatalogInput,CheckError as CatalogError,CheckControl as CatalogControl
KIND='model_catalog_queries'
MAX_BYTES=1024*1024
MAX_MODELS=256

class Catalog(ProviderCheck):
    kind=KIND
    identity='aegis-model-catalog-v1'
    label='제공자 모델 목록 조회'
    success_code='catalog_response_valid'

    def initial(self):return {'models':[],'model_count':0}
    def result(self,value,record):return {'models':value,'model_count':len(value)}

    def fetch(self,record,prepared,control):
        base,key,local,_=prepared;parsed=urlsplit(base)
        port=parsed.port or (443 if parsed.scheme=='https' else 80)
        address=resolve(parsed.hostname,port,allow_private=local,control=control,timeout=control.timeout(4))[0]
        connection=(PinnedHTTPS if parsed.scheme=='https' else PinnedHTTP)(parsed.hostname,port,address,timeout=control.timeout(8))
        try:
            with self.store.read_transaction() as db:
                profile,current,_=self.profile(record['profile_id'],record['profile_revision'],record['actor'],db)
                if current!=prepared or profile['fingerprint']!=record['profile_fingerprint']:raise ProfileUnavailable('Model profile changed')
            protocol=record['profile_snapshot'].get('provider_protocol','openai')
            suffix,authentication=catalog_request(protocol,key)
            with RequestGuard(connection,control,8) as guard:
                connection.request('GET',parsed.path.rstrip('/')+suffix,headers={**authentication,'Accept':'application/json','Accept-Encoding':'identity'})
                guard.sock=connection.sock;response=connection.getresponse()
                if response.status!=200:raise CatalogError('provider_status',response.status)
                if response.getheader('Content-Encoding','identity').lower()!='identity':raise CatalogError('response_encoding',200)
                if response.getheader('Content-Type','').split(';')[0].strip().lower()!='application/json':raise CatalogError('response_content_type',200)
                if response.length is not None and response.length>MAX_BYTES:raise CatalogError('response_byte_budget',200)
                raw=response.read(MAX_BYTES+1)
                if len(raw)>MAX_BYTES:raise CatalogError('response_byte_budget',200)
            control.check()
            try:
                body=_decode(raw)
                if protocol=='anthropic' and isinstance(body,dict) and body.get('has_more') is True:
                    raise CatalogError('catalog_incomplete',200)
                body=catalog_response(protocol,body);rows=body['data']
                if not isinstance(rows,list) or len(rows)>MAX_MODELS:raise ValueError()
                models=[];seen=set()
                for row in rows:
                    name=row['id']
                    if (not isinstance(name,str) or not name or len(name)>160 or
                            any(ord(c)<=32 or ord(c)>126 for c in name) or key in name or base in name or name in seen):raise ValueError()
                    models.append(name);seen.add(name)
                return models,hashlib.sha256(raw).hexdigest()
            except CatalogError:raise
            except (ValueError,TypeError,KeyError,AttributeError):raise CatalogError('response_shape',200) from None
        finally:connection.close()
