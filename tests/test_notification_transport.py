"""Owned POST receiver verifies destination admission and transport boundaries."""
import json,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from aegis.notification_transport import Webhooks,DispatchError

@pytest.fixture
def receiver(monkeypatch):
    class Handler(BaseHTTPRequestHandler):
        requests=[];status=204
        def log_message(self,*args):pass
        def do_POST(self):
            self.__class__.requests.append({'path':self.path,'headers':dict(self.headers),'body':json.loads(self.rfile.read(int(self.headers['Content-Length'])))})
            self.send_response(self.status);self.send_header('Location','http://127.0.0.1:1/never');self.end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    monkeypatch.setenv('OWNED_NOTIFICATION_ENDPOINT',f'http://127.0.0.1:{server.server_port}/owned-secret-path')
    monkeypatch.setenv('OWNED_NOTIFICATION_TOKEN','owned-transport-token')
    webhooks=Webhooks([{'id':'owned','name':'Owned receiver','endpoint_env':'OWNED_NOTIFICATION_ENDPOINT','token_env':'OWNED_NOTIFICATION_TOKEN','lab_http':True}])
    try:yield webhooks,Handler
    finally:server.shutdown();server.server_close();thread.join(3)


def test_owned_post_has_idempotency_and_current_credentials_without_public_secret(receiver):
    webhooks,handler=receiver;prepared=webhooks.prepare('owned')
    assert webhooks.public()==[{'id':'owned','name':'Owned receiver','configured':True}]
    result=webhooks.send(prepared,{'kind':'task.failed','task_id':'owned-task'},'owned-delivery-001')
    assert result=={'http_status':204,'receiver_accepted':True}
    assert len(handler.requests)==1
    row=handler.requests[0];assert row['path']=='/owned-secret-path' and row['headers']['Idempotency-Key']=='owned-delivery-001'
    assert row['headers']['Authorization']=='Bearer owned-transport-token' and row['body']['kind']=='task.failed'


@pytest.mark.parametrize('status',[302,400,429,500])
def test_redirect_and_rejection_are_single_attempt_receipts(receiver,status):
    webhooks,handler=receiver;handler.status=status
    with pytest.raises(DispatchError) as caught:webhooks.send(webhooks.prepare('owned'),{},'owned-delivery-001')
    assert caught.value.code=='receiver_rejected' and caught.value.possibly_sent and caught.value.status==status
    assert len(handler.requests)==1


@pytest.mark.parametrize('endpoint',['http://example.com/hook','http://localhost/hook','https://a:b@example.com/hook','https://example.com/hook?secret=x','https://example.com/hook#x','https://example.com/\nsecret'])
def test_invalid_destinations_never_send(receiver,monkeypatch,endpoint):
    webhooks,handler=receiver;monkeypatch.setenv('OWNED_NOTIFICATION_ENDPOINT',endpoint)
    with pytest.raises(DispatchError) as caught:webhooks.prepare('owned')
    assert caught.value.code=='endpoint_invalid' and not caught.value.possibly_sent and handler.requests==[]


def test_environment_change_updates_contract_and_missing_secret_stays_private(receiver,monkeypatch):
    webhooks,handler=receiver;before=webhooks.prepare('owned');monkeypatch.setenv('OWNED_NOTIFICATION_TOKEN','changed-owned-token')
    assert webhooks.prepare('owned').fingerprint!=before.fingerprint
    monkeypatch.delenv('OWNED_NOTIFICATION_TOKEN');assert not webhooks.public()[0]['configured']
    with pytest.raises(DispatchError) as caught:webhooks.prepare('owned')
    assert caught.value.code=='credential_unavailable' and handler.requests==[]


def test_dns_rejection_is_known_unsent_and_oversized_payload_never_resolves(receiver,monkeypatch):
    from aegis import notification_transport as transport
    webhooks,handler=receiver
    def forbidden(*args,**kwargs):raise ValueError('owned rejected address')
    monkeypatch.setattr(transport,'resolve',forbidden)
    with pytest.raises(DispatchError) as caught:webhooks.send(webhooks.prepare('owned'),{},'owned-delivery-001')
    assert caught.value.code=='address_unavailable' and not caught.value.possibly_sent
    with pytest.raises(DispatchError) as caught:webhooks.send(webhooks.prepare('owned'),{'large':'x'*16384},'owned-delivery-001')
    assert caught.value.code=='payload_invalid' and handler.requests==[]


def test_cancelled_control_refuses_post_and_setup_failure_is_known_unsent(receiver,monkeypatch):
    from aegis.runtime import TaskControl
    from aegis import notification_transport as transport
    webhooks,handler=receiver;control=TaskControl();control.stop.set()
    with pytest.raises(DispatchError) as caught:webhooks.send(webhooks.prepare('owned'),{},'owned-delivery-001',control=control)
    assert not caught.value.possibly_sent and handler.requests==[]
    monkeypatch.setattr(transport,'resolve',lambda *a,**k:['127.0.0.1'])
    def broken(*args,**kwargs):raise OSError('owned constructor failure')
    monkeypatch.setattr(transport,'PinnedHTTP',broken)
    with pytest.raises(DispatchError) as caught:webhooks.send(webhooks.prepare('owned'),{},'owned-delivery-001')
    assert caught.value.code=='transport_unconfirmed' and not caught.value.possibly_sent and handler.requests==[]


@pytest.mark.parametrize('raw',['null','{}','[{"id":"a","id":"b"}]','[{"id":"a","name":"Owned","endpoint_env":"OWNED","lab_http":"true"}]'])
def test_bad_environment_configuration_fails_without_echoing_values(monkeypatch,raw):
    monkeypatch.setenv('AEGIS_NOTIFICATION_DESTINATIONS',raw)
    with pytest.raises(RuntimeError) as caught:Webhooks.from_env()
    assert raw not in str(caught.value)


@pytest.mark.parametrize('token',['owned\r\nInjected: value','owned-비밀'])
def test_invalid_header_credentials_never_send(receiver,monkeypatch,token):
    webhooks,handler=receiver;monkeypatch.setenv('OWNED_NOTIFICATION_TOKEN',token)
    with pytest.raises(DispatchError) as caught:webhooks.prepare('owned')
    assert caught.value.code=='credential_invalid' and handler.requests==[]
