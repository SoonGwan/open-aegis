"""Versioned recipient review is atomic and never retains endpoint/token values."""
import pytest
from fastapi import HTTPException
from tests.test_mcp_registry import client
from tests.test_postgres_transfer import postgres
from aegis.notification_channels import Channels,ChannelInput,ChannelEdit
from aegis.notification_transport import Webhooks

@pytest.fixture
def channels(client,monkeypatch):
    monkeypatch.setenv('OWNED_NOTIFICATION_ENDPOINT','https://example.com/owned-secret-endpoint')
    monkeypatch.setenv('OWNED_NOTIFICATION_TOKEN','owned-token-value')
    webhooks=Webhooks([{'id':'owned','name':'Owned receiver','endpoint_env':'OWNED_NOTIFICATION_ENDPOINT','token_env':'OWNED_NOTIFICATION_TOKEN'}])
    return Channels(client.app.state.store,webhooks),client.app.state.store.user(username='admin')

def fields(**changes):return {'name':'Owned alerts','destination_id':'owned','request_id':'owned-channel-create-001',**changes}

def test_disabled_default_versioned_enable_duplicate_retry_and_public_secret_mask(channels,monkeypatch):
    service,actor=channels;first=service.create(ChannelInput(**fields()),actor);channel=first['channel']
    assert not channel['enabled'] and channel['activated_at'] is None and channel['configured']
    assert service.create(ChannelInput(**fields()),actor)['replayed']
    updated=service.change(channel['id'],ChannelEdit(**fields(enabled=True,expected_revision=1,request_id='owned-channel-enable-001')),actor)
    assert updated['channel']['revision']==2 and updated['channel']['enabled'] and updated['channel']['destination_review_current']
    assert service.change(channel['id'],ChannelEdit(**fields(enabled=True,expected_revision=1,request_id='owned-channel-enable-001')),actor)['replayed']
    monkeypatch.setenv('OWNED_NOTIFICATION_TOKEN','rotated-owned-token')
    public=service.public(service.get(channel['id']));assert public['configured'] and not public['destination_review_current']
    import json
    for kind in ('notification_channels','notification_channel_versions','notification_channel_operations'):
        raw=json.dumps(service.store.all(kind));assert 'owned-token-value' not in raw and 'owned-secret-endpoint' not in raw and 'rotated-owned-token' not in raw


def test_role_conflict_and_audit_rollback_do_not_enable_channel(channels,monkeypatch):
    service,actor=channels;channel=service.create(ChannelInput(**fields()),actor)['channel']
    before=service.store.audit_integrity()
    def broken(*args,**kwargs):raise RuntimeError('owned final audit failure')
    monkeypatch.setattr(service.store,'event',broken)
    with pytest.raises(RuntimeError):service.change(channel['id'],ChannelEdit(**fields(enabled=True,expected_revision=1,request_id='owned-channel-enable-001')),actor)
    assert service.get(channel['id'])['revision']==1 and not service.get(channel['id'])['enabled']
    assert service.store.count('notification_channel_operations')==0 and service.store.count('notification_channel_versions')==1
    assert service.store.audit_integrity()==before
    monkeypatch.undo();service.store.update_user(actor['id'],role='operator')
    with pytest.raises(HTTPException) as caught:service.create(ChannelInput(**fields(name='Other',request_id='owned-channel-create-002')),actor)
    assert caught.value.status_code==403 and service.store.count('notification_channels')==1


def test_missing_credentials_refuse_activation_and_stale_changes_preserve_review(channels,monkeypatch):
    service,actor=channels;channel=service.create(ChannelInput(**fields()),actor)['channel']
    monkeypatch.delenv('OWNED_NOTIFICATION_TOKEN')
    with pytest.raises(HTTPException) as caught:service.change(channel['id'],ChannelEdit(**fields(enabled=True,expected_revision=1,request_id='owned-channel-enable-001')),actor)
    assert caught.value.status_code==409 and service.get(channel['id'])['revision']==1
    with pytest.raises(HTTPException) as caught:service.change(channel['id'],ChannelEdit(**fields(name='Renamed',expected_revision=2,request_id='owned-channel-edit-001')),actor)
    assert caught.value.status_code==409 and service.get(channel['id'])['name']=='Owned alerts'


def test_committed_create_and_edit_replay_survive_missing_current_credential(channels,monkeypatch):
    service,actor=channels;input=ChannelInput(**fields(enabled=True));created=service.create(input,actor)['channel']
    edit=ChannelEdit(**fields(name='Reviewed rename',enabled=True,expected_revision=1,request_id='owned-channel-edit-001'))
    assert service.change(created['id'],edit,actor)['channel']['revision']==2
    monkeypatch.delenv('OWNED_NOTIFICATION_TOKEN')
    first=service.create(input,actor);assert first['replayed'] and first['channel']['revision']==2 and not first['channel']['configured']
    again=service.change(created['id'],edit,actor);assert again['replayed'] and again['channel']['name']=='Reviewed rename' and not again['channel']['configured']
    assert service.store.count('notification_channel_versions')==2 and service.store.count('notification_channel_operations')==1
