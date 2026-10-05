"""Actual channel HTTP and task execution reach only the owned receiver after approval."""
import json,time
import pytest
from tests.test_mcp_registry import client
from tests.test_postgres_transfer import postgres
from tests.test_notification_transport import receiver
from tests.test_notification_channels import fields
from tests.test_validation import lab,register,task,finish
from tests.test_identity import add,login
from aegis.notification_events import terminal


def bind(client,receiver):
    webhooks,handler=receiver;channels=client.app.state.notification_channels
    channels.webhooks=webhooks
    client.app.state.notification_deliveries.start()
    return handler


def wait_delivery(client):
    end=time.monotonic()+5
    while time.monotonic()<end:
        page=client.get('/api/notification-deliveries').json()
        if page['total'] and page['items'][0]['status'] in ('delivered','failed','unknown','blocked'):return page['items'][0]
        time.sleep(.02)
    pytest.fail('owned delivery did not settle')


def test_actual_approved_task_completion_reaches_receiver_with_durable_history(client,receiver,lab):
    handler=bind(client,receiver)
    response=client.post('/api/notification-channels',json=fields(enabled=True,task_statuses=['completed'],interval_seconds=1));assert response.status_code==200,response.text
    channel=response.json()['channel'];asset=register(client,lab[0]);created=task(client,asset,['security_headers'])
    time.sleep(.15);assert handler.requests==[] and client.get('/api/notification-deliveries').json()['total']==0
    assert client.post('/api/tasks/'+created['id']+'/approve').status_code==200
    completed=finish(client,created['id']);assert completed['task']['status']=='completed'
    record=wait_delivery(client);assert record['status']=='delivered' and record['task_id']==created['id'] and record['channel_id']==channel['id']
    assert len(handler.requests)==1 and handler.requests[0]['body']['kind']=='task.completed'
    attempts=client.get('/api/notification-deliveries/'+record['id']+'/attempts').json()
    assert attempts['total']==1 and attempts['items'][0]['status']=='delivered'
    assert client.get('/api/notification-channels/'+channel['id']+'/history').json()['total']==1
    raw=json.dumps(client.get('/api/notification-deliveries').json())+json.dumps(client.get('/api/notification-channels').json())
    assert 'owned-secret-path' not in raw and 'owned-transport-token' not in raw and 'destination_fingerprint' not in raw
    assert client.app.state.store.audit_integrity()['valid']


def test_operator_reads_but_cannot_enable_or_retry_notifications(client,receiver):
    bind(client,receiver)
    channel=client.post('/api/notification-channels',json=fields()).json()['channel']
    add(client,'operator')
    with login(client.app,'operator') as other:
        assert other.get('/api/notification-channels').status_code==200
        assert other.post('/api/notification-channels',json=fields(name='Unauthorized',request_id='other-channel-request-001')).status_code==403
        assert other.put('/api/notification-channels/'+channel['id'],json=fields(enabled=True,expected_revision=1)).status_code==403
        assert other.post('/api/notification-deliveries/absent/retry',json={'expected_attempts':0,'request_id':'owned-retry-request-001'}).status_code==403


def test_terminal_state_and_notification_source_rollback_together_preserves_classification(client,monkeypatch):
    store=client.app.state.store
    original={'id':'owned-atomic-task','name':'Owned atomic task','status':'running','category_ref':{'id':'owned','name':'Owned','revision':1},'category_revision':2}
    store.put('tasks',original);audit=store.audit_integrity();event=store.event
    monkeypatch.setattr(store,'event',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('owned terminal audit failure')))
    with pytest.raises(RuntimeError):terminal(store,original['id'],{'status':'completed'},'Owned terminal')
    assert store.get('tasks',original['id'])==original and store.audit_integrity()==audit
    monkeypatch.setattr(store,'event',event);result=terminal(store,original['id'],{'status':'completed'},'Owned terminal')
    assert result['category_ref']==original['category_ref'] and result['category_revision']==2
    assert store.events(task_id=original['id'])[-1]['detail']=={'notification_kind':'task.terminal','task_status':'completed'}


def test_disabled_channel_test_is_separate_review_and_duplicate_request_is_single_post(client,receiver):
    handler=bind(client,receiver);channel=client.post('/api/notification-channels',json=fields()).json()['channel']
    assert not channel['enabled']
    data={'expected_revision':1,'request_id':'owned-notification-test-001'}
    first=client.post('/api/notification-channels/'+channel['id']+'/test',json=data);assert first.status_code==200,first.text
    record=wait_delivery(client);assert record['id']==first.json()['delivery_id'] and record['status']=='delivered' and record['test_mode']
    assert handler.requests[0]['body']['kind']=='test' and len(handler.requests)==1
    replay=client.post('/api/notification-channels/'+channel['id']+'/test',json=data);assert replay.status_code==200 and replay.json()['replayed']
    assert client.get('/api/notification-deliveries').json()['total']==1
    assert not client.get('/api/notification-channels/'+channel['id']).json()['enabled']


def test_rejected_unapproved_task_notifies_without_target_execution(client,receiver,lab):
    handler=bind(client,receiver)
    assert client.post('/api/notification-channels',json=fields(enabled=True,task_statuses=['rejected'],interval_seconds=1)).status_code==200
    created=task(client,register(client,lab[0]),['security_headers'])
    response=client.post('/api/tasks/'+created['id']+'/stop');assert response.status_code==200 and response.json()['status']=='rejected'
    record=wait_delivery(client)
    assert record['status']=='delivered' and handler.requests[0]['body']['kind']=='task.rejected'
    assert not client.app.state.store.page('traffic',filters={'task_id':created['id']})['items']


def test_notification_list_filters_and_budgets_do_not_cross_channels(client,receiver):
    bind(client,receiver)
    first=client.post('/api/notification-channels',json=fields(name='Owned Alpha')).json()['channel']
    second=client.post('/api/notification-channels',json=fields(name='Owned Beta',request_id='owned-filter-channel-002')).json()['channel']
    first_delivery=client.post('/api/notification-channels/'+first['id']+'/test',json={'expected_revision':1,'request_id':'owned-filter-test-001'}).json()['delivery_id']
    client.post('/api/notification-channels/'+second['id']+'/test',json={'expected_revision':1,'request_id':'owned-filter-test-002'})
    assert client.get('/api/notification-channels',params={'search':'Alpha','status':'disabled'}).json()['total']==1
    page=client.get('/api/notification-deliveries',params={'channel_id':first['id']}).json()
    assert page['total']==1 and page['items'][0]['id']==first_delivery
    for path,params in [('/api/notification-channels',{'limit':26}),('/api/notification-deliveries',{'status':'invented'}),('/api/notification-deliveries',{'limit':26}),('/api/notification-channels/'+first['id']+'/history',{'limit':26})]:
        assert client.get(path,params=params).status_code==422


def test_bad_notification_configuration_releases_workspace_lease(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from aegis.app import create_app
    monkeypatch.setenv('AEGIS_STORAGE_BACKEND','sqlite');monkeypatch.setenv('AEGIS_NOTIFICATION_DESTINATIONS','{invalid owned configuration')
    with pytest.raises(RuntimeError,match='알림 수신처 설정'):create_app(tmp_path/'owned-startup')
    monkeypatch.setenv('AEGIS_NOTIFICATION_DESTINATIONS','[]')
    with TestClient(create_app(tmp_path/'owned-startup')) as restored:
        assert restored.get('/api/health').status_code==200
        assert not restored.app.state.notification_deliveries.thread


@pytest.mark.parametrize('route,data',[
    ('/api/notification-channels',{'name':'Owned','destination_id':'owned'}),
    ('/api/notification-channels/owned/test',{'expected_revision':1}),
    ('/api/notification-deliveries/owned/retry',{'expected_attempts':0}),
])
def test_short_request_id_rejected_before_any_notification_operation(client,route,data):
    response=client.post(route,json={**data,'request_id':'short'})
    assert response.status_code==422,response.text
    assert client.app.state.store.count('notification_channels')==client.app.state.store.count('notification_deliveries')==client.app.state.store.count('notification_retry_operations')==0
