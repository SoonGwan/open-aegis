"""Atomic source receipts and unknown transport recovery never automatically resend."""
import pytest
from tests.test_notification_channels import channels,fields
from tests.test_notification_transport import receiver
from tests.test_mcp_registry import client
from tests.test_postgres_transfer import postgres
from tests.test_postgres_store import stores
from aegis.notification_channels import ChannelInput
from aegis.notification_deliveries import Deliveries,STATE
from aegis.notification_transport import DispatchError


def source(service,status='failed',id='owned-finished-task'):
    service.store.put('tasks',{'id':id,'name':'Owned failed task','status':status})
    service.store.event(id,'Owned terminal source',detail={'notification_kind':'task.terminal','task_status':status})


def enabled(channels):
    service,actor=channels;service.create(ChannelInput(**fields(enabled=True,interval_seconds=1)),actor)
    return service,Deliveries(service.store,service)


def drain(deliveries):
    for _ in range(200):
        if not deliveries.scan():return
    pytest.fail('notification cursor did not settle')


def test_source_cursor_receipt_audit_atomicity_and_single_receiver_acceptance(channels,monkeypatch):
    service,deliveries=enabled(channels);drain(deliveries);cursor=service.store.get('notification_state',STATE);source(service);before=service.store.audit_integrity()
    original=service.store.event
    def fail(*args,**kwargs):raise RuntimeError('owned queued audit failure')
    monkeypatch.setattr(service.store,'event',fail)
    with pytest.raises(RuntimeError):deliveries.scan()
    assert service.store.count('notification_deliveries')==0 and service.store.get('notification_state',STATE)==cursor
    assert service.store.audit_integrity()==before
    monkeypatch.setattr(service.store,'event',original);drain(deliveries)
    assert service.store.count('notification_deliveries')==1
    calls=[]
    monkeypatch.setattr(service.webhooks,'send',lambda prepared,payload,id,**kw:calls.append(id) or {'http_status':202,'receiver_accepted':True})
    assert deliveries.dispatch_one();drain(deliveries);assert not deliveries.dispatch_one()
    assert len(calls)==1 and service.store.all('notification_deliveries')[0]['status']=='delivered'
    assert service.store.all('notification_attempts')[0]['status']=='delivered' and service.store.audit_integrity()['valid']


@pytest.mark.parametrize('error',[DispatchError('address_unavailable'),DispatchError('transport_unconfirmed',possibly_sent=True),DispatchError('receiver_rejected',possibly_sent=True,status=500)])
def test_transport_failure_is_not_automatically_retried(channels,monkeypatch,error):
    service,deliveries=enabled(channels);source(service);drain(deliveries);calls=[]
    def broken(*args,**kwargs):calls.append(1);raise error
    monkeypatch.setattr(service.webhooks,'send',broken)
    assert deliveries.dispatch_one();drain(deliveries)
    assert not deliveries.dispatch_one() and calls==[1]
    record=service.store.all('notification_deliveries')[0]
    assert record['status']==('unknown' if error.possibly_sent and error.status is None else 'failed')
    assert record['attempts']==1 and record['result_code']==error.code


def test_saved_dispatch_receipt_lost_after_receiver_is_recovered_unknown(channels,monkeypatch):
    service,deliveries=enabled(channels);source(service);drain(deliveries);calls=[];original=service.store.event
    def sent(*args,**kwargs):
        calls.append(1)
        monkeypatch.setattr(service.store,'event',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('owned receipt audit lost')))
        return {'http_status':204,'receiver_accepted':True}
    monkeypatch.setattr(service.webhooks,'send',sent)
    with pytest.raises(RuntimeError):deliveries.dispatch_one()
    assert service.store.all('notification_deliveries')[0]['status']=='dispatching'
    monkeypatch.setattr(service.store,'event',original)
    restarted=Deliveries(service.store,service);assert restarted.recover();assert not restarted.dispatch_one()
    assert calls==[1] and service.store.all('notification_deliveries')[0]['status']=='unknown'
    assert service.store.all('notification_attempts')[0]['result_code']=='process_receipt_unconfirmed'


def test_credential_rotation_blocks_without_send(channels,monkeypatch):
    service,deliveries=enabled(channels);source(service);drain(deliveries)
    monkeypatch.setenv('OWNED_NOTIFICATION_TOKEN','rotated-token')
    monkeypatch.setattr(service.webhooks,'send',lambda *a,**k:pytest.fail('unreviewed destination must not send'))
    assert deliveries.dispatch_one() and service.store.all('notification_deliveries')[0]['result_code']=='destination_changed'


def test_revoked_original_channel_admin_blocks_without_send(channels,monkeypatch):
    service,deliveries=enabled(channels);source(service);drain(deliveries)
    actor=channels[1];service.store.update_user(actor['id'],role='operator')
    monkeypatch.setattr(service.webhooks,'send',lambda *a,**k:pytest.fail('revoked admin must not send'))
    assert deliveries.dispatch_one()
    assert service.store.all('notification_deliveries')[0]['result_code']=='channel_approver_unavailable'


def test_due_sql_does_not_starve_second_channel_behind_26_cooled_down_rows(channels,monkeypatch):
    service,actor=channels
    first=service.create(ChannelInput(**fields(enabled=True,interval_seconds=3600)),actor)['channel']
    second=service.create(ChannelInput(**fields(name='Other status',task_statuses=['completed'],enabled=True,interval_seconds=1,request_id='owned-channel-create-002')),actor)['channel']
    deliveries=Deliveries(service.store,service)
    for i in range(27):source(service,id='owned-failed-'+str(i))
    source(service,status='completed',id='owned-completed');drain(deliveries)
    calls=[]
    monkeypatch.setattr(service.webhooks,'send',lambda prepared,payload,id,**kw:calls.append(payload['kind']) or {'http_status':204,'receiver_accepted':True})
    assert deliveries.dispatch_one() and deliveries.dispatch_one() and not deliveries.dispatch_one()
    assert calls==['task.failed','task.completed']
    assert sum(row['status']=='queued' for row in service.store.all('notification_deliveries'))==26


def test_manual_unknown_retry_requires_confirmation_is_idempotent_and_keeps_attempts(channels,monkeypatch):
    from fastapi import HTTPException
    service,deliveries=enabled(channels);source(service);drain(deliveries);calls=[]
    def lost(*args,**kwargs):calls.append(1);raise DispatchError('transport_unconfirmed',possibly_sent=True)
    monkeypatch.setattr(service.webhooks,'send',lost);assert deliveries.dispatch_one()
    record=service.store.all('notification_deliveries')[0];actor=channels[1]
    kwargs={'expected_attempts':1,'request_id':'owned-retry-request-001','confirm_possible_duplicate':False,'actor':actor}
    with pytest.raises(HTTPException) as caught:deliveries.retry(record['id'],**kwargs)
    assert caught.value.status_code==409 and record['status']=='unknown'
    kwargs['confirm_possible_duplicate']=True
    assert not deliveries.retry(record['id'],**kwargs)['replayed']
    assert deliveries.retry(record['id'],**kwargs)['replayed']
    assert service.store.count('notification_retry_operations')==1
    # Release only the owned persisted cooldown, preserving the delivery/receiver binding.
    service.store.put('notification_runtime',{'id':record['channel_id'],'next_at':0})
    monkeypatch.setattr(service.webhooks,'send',lambda *a,**k:calls.append(1) or {'http_status':204,'receiver_accepted':True})
    assert deliveries.dispatch_one();assert calls==[1,1]
    assert deliveries.retry(record['id'],**kwargs)['replayed']
    latest=service.store.get('notification_deliveries',record['id']);assert latest['status']=='delivered' and latest['attempts']==2
    attempts=sorted(service.store.all('notification_attempts'),key=lambda a:a['attempt'])
    assert [a['status'] for a in attempts]==['unknown','delivered'] and service.store.audit_integrity()['valid']


def test_retry_audit_failure_rolls_back_queue_and_receipt(channels,monkeypatch):
    service,deliveries=enabled(channels);source(service);drain(deliveries)
    monkeypatch.setattr(service.webhooks,'send',lambda *a,**k:(_ for _ in ()).throw(DispatchError('address_unavailable')))
    assert deliveries.dispatch_one();record=service.store.all('notification_deliveries')[0];before=service.store.audit_integrity()
    monkeypatch.setattr(service.store,'event',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('owned retry audit failure')))
    with pytest.raises(RuntimeError):deliveries.retry(record['id'],expected_attempts=1,request_id='owned-retry-request-001',confirm_possible_duplicate=False,actor=channels[1])
    assert service.store.get('notification_deliveries',record['id'])==record and service.store.count('notification_retry_operations')==0
    assert service.store.audit_integrity()==before


def test_actual_owned_receiver_gets_single_durable_service_post(client,receiver):
    from aegis.notification_channels import Channels
    webhooks,handler=receiver;service=Channels(client.app.state.store,webhooks)
    actor=service.store.user(username='admin')
    service.create(ChannelInput(**fields(enabled=True,interval_seconds=1)),actor)
    deliveries=Deliveries(service.store,service);source(service);drain(deliveries)
    assert deliveries.dispatch_one();drain(deliveries);assert not deliveries.dispatch_one()
    assert len(handler.requests)==1 and handler.requests[0]['body']['kind']=='task.failed'
    record=service.store.all('notification_deliveries')[0]
    assert handler.requests[0]['headers']['Idempotency-Key']==record['id'] and record['status']=='delivered'
    assert service.store.audit_integrity()['valid']


def test_three_failed_attempts_keep_history_and_reject_fourth(channels,monkeypatch):
    from fastapi import HTTPException
    service,deliveries=enabled(channels);source(service);drain(deliveries);calls=[]
    def failed(*args,**kwargs):
        calls.append(1);raise DispatchError('receiver_rejected',possibly_sent=True,status=503)
    monkeypatch.setattr(service.webhooks,'send',failed)
    for attempt in range(1,4):
        assert deliveries.dispatch_one()
        record=service.store.all('notification_deliveries')[0]
        assert record['attempts']==attempt and record['status']=='failed'
        if attempt<3:
            deliveries.retry(record['id'],expected_attempts=attempt,request_id=f'owned-cap-retry-request-{attempt}',confirm_possible_duplicate=True,actor=channels[1])
            service.store.put('notification_runtime',{'id':record['channel_id'],'next_at':0})
    with pytest.raises(HTTPException) as caught:
        deliveries.retry(record['id'],expected_attempts=3,request_id='owned-cap-retry-request-4',confirm_possible_duplicate=True,actor=channels[1])
    assert caught.value.status_code==409 and len(calls)==3
    assert service.store.count('notification_attempts')==3 and service.store.count('notification_retry_operations')==2
    assert service.store.audit_integrity()['valid']


@pytest.mark.parametrize('cursor',[-1,True,'1',10**9])
def test_invalid_saved_cursor_never_creates_or_sends_receipts(channels,monkeypatch,cursor):
    service,deliveries=enabled(channels);source(service)
    service.store.put('notification_state',{'id':STATE,'after':cursor})
    monkeypatch.setattr(service.webhooks,'send',lambda *a,**k:pytest.fail('invalid cursor must not send'))
    with pytest.raises(ValueError):deliveries.scan()
    assert service.store.count('notification_deliveries')==0 and not deliveries.dispatch_one()


def test_native_notification_post_fences_owner_loss_and_recovers_without_resend(stores,postgres,receiver,monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from aegis.auth import new_user
    from aegis.notification_channels import Channels
    from aegis.postgres_store import PostgresStore
    from aegis.postgres_maintenance import PostgresLease
    from aegis.maintenance import WorkspaceBusy
    from tests.test_postgres_ownership import terminate_owner
    _,store=stores;owner=store.acquire_runtime();webhooks,handler=receiver
    entered=threading.Event();release=threading.Event();original=handler.do_POST
    def held(self):
        entered.set();assert release.wait(5);original(self)
    monkeypatch.setattr(handler,'do_POST',held)
    actor=new_user('owned-admin','Owned admin','admin','owned-notification-fence-password');store.add_user(actor)
    channels=Channels(store,webhooks);channels.create(ChannelInput(**fields(enabled=True,interval_seconds=1)),actor)
    deliveries=Deliveries(store,channels);source(channels);drain(deliveries)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(deliveries.dispatch_one)
            try:
                assert entered.wait(2);terminate_owner(postgres,owner)
                with pytest.raises(WorkspaceBusy):
                    with PostgresLease(postgres['dsn'],store.schema):pass
            finally:release.set()
            with pytest.raises(WorkspaceBusy):future.result(timeout=5)
        fresh=PostgresStore(postgres['dsn'],store.schema)
        with fresh.acquire_runtime():
            recovered=Deliveries(fresh,Channels(fresh,webhooks));assert recovered.recover()
            assert fresh.all('notification_deliveries')[0]['status']=='unknown'
            assert not recovered.dispatch_one() and len(handler.requests)==1
            assert fresh.audit_integrity()['valid']
    finally:release.set();owner.close()
