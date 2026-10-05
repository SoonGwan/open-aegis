"""Fixed administrator-configured webhook destinations with bounded pinned POSTs."""
import json
import os
import re
from dataclasses import dataclass
from urllib.parse import urlsplit
from pydantic import BaseModel,ConfigDict,Field
from .network import PinnedHTTP,PinnedHTTPS,normalize_url,resolve
from .remote_mcp import _digest,_encode,_decode
from .runtime import RequestGuard,TaskControl


class Destination(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,frozen=True)
    id:str=Field(min_length=1,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')
    name:str=Field(min_length=1,max_length=100)
    endpoint_env:str=Field(min_length=1,max_length=100,pattern=r'^[A-Za-z_][A-Za-z0-9_]*$')
    token_env:str|None=Field(default=None,min_length=1,max_length=100,pattern=r'^[A-Za-z_][A-Za-z0-9_]*$')
    lab_http:bool=False


class DispatchError(ValueError):
    def __init__(self,code,*,possibly_sent=False,status=None):
        super().__init__(code);self.code=code;self.possibly_sent=possibly_sent;self.status=status


@dataclass(frozen=True)
class PreparedDestination:
    endpoint:str
    token:str|None
    fingerprint:str
    local:bool


class Webhooks:
    def __init__(self,destinations):
        if not isinstance(destinations,list) or len(destinations)>10:raise ValueError('destination_budget')
        self.destinations={}
        for item in destinations:
            record=Destination(**item)
            if record.id in self.destinations:raise ValueError('duplicate_destination')
            self.destinations[record.id]=record

    @classmethod
    def from_env(cls):
        try:
            raw=os.environ.get('AEGIS_NOTIFICATION_DESTINATIONS','[]').encode()
            if len(raw)>32768:raise ValueError('configuration_budget')
            return cls(_decode(raw))
        except (ValueError,TypeError,UnicodeError):
            raise RuntimeError('알림 수신처 설정을 확인하세요. 고정 수신처는 최대10개입니다.') from None

    def prepare(self,id):
        destination=self.destinations.get(id)
        if destination is None:raise DispatchError('destination_unavailable')
        endpoint=os.environ.get(destination.endpoint_env,'')
        token=os.environ.get(destination.token_env,'') if destination.token_env else None
        if not endpoint or destination.token_env and not token:raise DispatchError('credential_unavailable')
        if len(endpoint)>2000 or any(ord(c)<=32 or ord(c)==127 for c in endpoint):raise DispatchError('endpoint_invalid')
        if token is not None and (len(token)>4096 or any(ord(c)<32 or ord(c)>126 for c in token)):raise DispatchError('credential_invalid')
        try:
            endpoint=normalize_url(endpoint);parsed=urlsplit(endpoint);parsed.path.encode('ascii')
            local=destination.lab_http and parsed.hostname in ('127.0.0.1','::1')
            if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.scheme!='https' and not (local and parsed.scheme=='http'):
                raise ValueError('endpoint')
        except ValueError:raise DispatchError('endpoint_invalid') from None
        return PreparedDestination(endpoint,token,_digest({'id':id,'endpoint':endpoint,'token':token,'local':local}),local)

    def public(self):
        result=[]
        for destination in self.destinations.values():
            try:self.prepare(destination.id);configured=True
            except DispatchError:configured=False
            result.append({'id':destination.id,'name':destination.name,'configured':configured})
        return result

    def send(self,prepared,payload,delivery_id,*,control=None,timeout=8):
        if type(timeout) not in (int,float) or not .1<=timeout<=15:raise DispatchError('timeout_invalid')
        if not isinstance(delivery_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}',delivery_id):raise DispatchError('delivery_id_invalid')
        try:body=_encode(payload,limit=16*1024)
        except ValueError:raise DispatchError('payload_invalid') from None
        control=control or TaskControl();parsed=urlsplit(prepared.endpoint)
        port=parsed.port or (443 if parsed.scheme=='https' else 80)
        try:address=resolve(parsed.hostname,port,allow_private=prepared.local,control=control,timeout=min(4,timeout))[0]
        except Exception:raise DispatchError('address_unavailable') from None
        cls=PinnedHTTPS if parsed.scheme=='https' else PinnedHTTP
        connection=None
        headers={'Content-Type':'application/json','Idempotency-Key':delivery_id}
        if prepared.token is not None:headers['Authorization']='Bearer '+prepared.token
        started=False
        try:
            connection=cls(parsed.hostname,port,address,timeout=control.timeout(timeout))
            with RequestGuard(connection,control,timeout) as guard:
                control.check();started=True
                connection.request('POST',parsed.path or '/',body=body,headers=headers)
                guard.sock=connection.sock;response=connection.getresponse();status=response.status
                # The receiver's HTTP status is the receipt. No peer response text is retained.
                if not 200<=status<300:raise DispatchError('receiver_rejected',possibly_sent=True,status=status)
                return {'http_status':status,'receiver_accepted':True}
        except DispatchError:raise
        except Exception:raise DispatchError('transport_unconfirmed',possibly_sent=started) from None
        finally:
            if connection is not None:connection.close()
