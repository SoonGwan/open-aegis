import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from aegis.scopesentry import parse_export
from tests.test_identity import add, login
from tests.test_validation import client, lab, register, task


def row(number=1, url='https://sentry-fixture.invalid/', **fields):
    return {'_id': f'{number:024x}', 'type': 'http', 'url': url, **fields}


def preview(client, rows, source='fixture-main'):
    response = client.post('/api/integrations/scopesentry/preview', json={
        'source_key': source, 'export': '\n'.join(json.dumps(r) for r in rows)})
    assert response.status_code == 200, response.text
    return response.json()


def apply(client, plan, selected=None, authorized=True):
    return client.post('/api/integrations/scopesentry/' + plan['id'] + '/apply', json={
        'selected': selected or [r['external_id'] for r in plan['rows'] if r['status'] == 'ready'],
        'authorized': authorized})


def test_preview_review_selection_and_private_fields_never_persist(client, lab):
    store = client.app.state.store
    plan = preview(client, [row(1, lab[0], body='secret-body-marker', rawheaders='secret-header-marker', title='secret-title-marker'),
                            row(2, 'https://other.invalid/')])
    assert plan['format'] == 'scopesentry-asset-ndjson-v1'
    assert store.count('assets') == store.count('tasks') == 0
    assert plan['rows'][0]['action'] == 'create'
    assert 'expected_source' not in plan['rows'][0]
    raw = json.dumps(store.get('import_previews', plan['id']))
    assert 'secret-' not in raw and 'secret-' not in json.dumps(plan)
    assert apply(client, plan, authorized=False).status_code == 422
    result = apply(client, plan, [plan['rows'][0]['external_id']]).json()
    assert result['created'] == result['linked'] == 1
    asset = store.get('assets', result['items'][0]['asset_id'])
    assert asset['authorization_rules'] == [] and asset['revision'] == 1
    assert store.count('assets') == 1 and store.count('tasks') == 0
    sources = client.get('/api/assets/' + asset['id'] + '/sources').json()['items']
    assert sources[0]['external_id'] == row()['_id'] and sources[0]['source_key'] == 'fixture-main'
    assert sources[0]['export_sha256'] == plan['export_sha256']
    assert sources[0]['first_seen'] == sources[0]['last_seen']
    assert lab[1].requests == []


def test_same_preview_concurrent_apply_and_retry_are_idempotent(client, lab):
    plan = preview(client, [row(1, lab[0])])
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: apply(client, plan), range(2)))
    assert all(r.status_code == 200 for r in responses)
    assert responses[0].json() == responses[1].json() == apply(client, plan).json()
    assert client.app.state.store.count('assets') == client.app.state.store.count('asset_sources') == 1
    assert lab[1].requests == []


def test_repeat_files_link_existing_assets_and_keep_local_edits(client):
    asset = register(client, 'https://sentry-fixture.invalid/', tags=['local'], owner='local owner')
    first = apply(client, preview(client, [row()])).json()
    assert first['created'] == 0 and first['linked'] == 1
    before = client.app.state.store.get('assets', asset['id'])
    plan = preview(client, [row(tags=['external'], title='external title')])
    assert plan['rows'][0]['action'] == 'seen'
    assert apply(client, plan).json()['seen'] == 1
    assert client.app.state.store.get('assets', asset['id']) == before
    assert client.app.state.store.count('asset_sources') == 1


def test_changed_source_address_keeps_old_scope_history_and_evidence(client, lab):
    original_result = apply(client, preview(client, [row(1, lab[0])])).json()
    old_id = original_result['items'][0]['asset_id']
    old_asset = client.app.state.store.get('assets', old_id)
    pending = task(client, old_asset, ['security_headers'])
    plan = preview(client, [row(1, 'https://changed.invalid/')])
    assert plan['rows'][0]['source_changed'] and plan['rows'][0]['previous_url'] == lab[0]
    fresh = apply(client, plan).json()
    assert fresh['source_changed'] == fresh['created'] == 1
    assert fresh['items'][0]['asset_id'] != old_id
    assert client.app.state.store.get('assets', old_id) == old_asset
    assert client.app.state.store.get('tasks', pending['id']) == pending
    history = client.get('/api/assets/' + old_id + '/sources?history=true').json()['items']
    assert history[0]['source_url'] == lab[0] and history[0]['replaced_at']
    assert client.get('/api/assets/' + old_id + '/sources').json()['total'] == 0
    assert lab[1].requests == []


def test_partial_file_does_not_delete_absent_source_or_asset(client):
    result = apply(client, preview(client, [row(1), row(2, 'https://second.invalid/')])).json()
    assets = [client.app.state.store.get('assets', r['asset_id']) for r in result['items']]
    apply(client, preview(client, [row(1)]))
    assert client.app.state.store.count('asset_sources') == 2
    assert all(client.app.state.store.get('assets', a['id']) == a for a in assets)


def test_two_sources_and_same_url_rows_reuse_one_asset(client):
    plan = preview(client, [row(1), row(2)])
    result = apply(client, plan).json()
    assert result['created'] == 1 and result['linked'] == 2
    assert len({r['asset_id'] for r in result['items']}) == 1
    assert apply(client, preview(client, [row(1)], source='other-instance')).json()['linked'] == 1
    assert client.app.state.store.count('assets') == 1
    assert client.app.state.store.count('asset_sources') == 3


def test_stale_plan_rejects_entire_batch_after_existing_asset_changed(client):
    asset = register(client, 'https://sentry-fixture.invalid/')
    plan = preview(client, [row(1), row(2, 'https://not-created.invalid/')])
    client.put('/api/assets/' + asset['id'], json={**asset, 'name': 'Changed'})
    assert apply(client, plan).status_code == 409
    assert client.app.state.store.count('assets') == 1
    assert client.app.state.store.count('asset_sources') == 0


def test_stale_source_conflicts_and_archived_items_cannot_be_applied(client):
    old = preview(client, [row()])
    result = apply(client, preview(client, [row()])).json()
    assert apply(client, old).status_code == 409
    asset_id = result['items'][0]['asset_id']
    client.post('/api/assets/' + asset_id + '/archive', json={'archived': True})
    blocked = preview(client, [row()])
    assert blocked['rows'][0]['status'] == 'blocked'
    assert apply(client, blocked, [row()['_id']]).status_code == 422


def test_roles_actor_binding_and_anonymous_denial(client):
    plan = preview(client, [row()])
    viewer = add(client, 'viewer')
    with login(client.app, viewer['username']) as read:
        assert read.post('/api/integrations/scopesentry/preview', json={'source_key':'fixture','export':json.dumps(row())}).status_code == 403
        assert apply(read, plan).status_code == 403
    operator = add(client, 'operator')
    with login(client.app, operator['username']) as ops:
        assert apply(ops, plan).status_code == 403
        own = preview(ops, [row()])
        assert apply(ops, own).status_code == 200
    with TestClient(client.app) as anonymous:
        assert anonymous.post('/api/integrations/scopesentry/preview', json={'source_key':'fixture','export':json.dumps(row())}).status_code == 401


def test_expired_unknown_selection_and_changed_retry_selection(client):
    plan = preview(client, [row(1), row(2)])
    assert apply(client, plan, ['unknown']).status_code == 422
    assert apply(client, plan, [row()['_id'], row()['_id']]).status_code == 422
    assert apply(client, plan, [row()['_id']]).status_code == 200
    assert apply(client, plan, [row(2)['_id']]).status_code == 409
    client.app.state.store.patch('import_previews', plan['id'], expires_at=1)
    assert apply(client, plan, [row()['_id']]).status_code == 410


def test_apply_storage_failure_rolls_back_assets_links_result_and_audit(client):
    store = client.app.state.store
    plan = preview(client, [row()])
    with store.connect() as db:
        before = db.execute('SELECT count(*) FROM events').fetchone()[0]
        db.execute("CREATE TRIGGER reject_import BEFORE INSERT ON event_hashes BEGIN SELECT RAISE(ABORT,'synthetic source audit rollback'); END")
    with pytest.raises(sqlite3.IntegrityError, match='synthetic source audit rollback'):
        apply(client, plan)
    assert store.count('assets') == store.count('asset_sources') == 0
    assert store.get('import_previews', plan['id'])['applied_at'] is None
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM events').fetchone()[0] == before


@pytest.mark.parametrize('url', ['https://user:secret@invalid/', 'https://invalid/?secret=value',
                                'https://invalid/#fragment', 'https://invalid/\x00secret', 'https://invalid/\ud800'])
def test_bad_urls_are_not_reflected_or_imported(url):
    result = parse_export(json.dumps(row(url=url)))
    assert result[0]['status'] == 'invalid' and result[0]['url'] is None
    assert 'secret' not in json.dumps(result)


@pytest.mark.parametrize('text', ['[]', '{"_id":"x","_id":"y"}', '{"value":NaN}', '{', '\n'.join(json.dumps(row()) for _ in range(101))])
def test_bad_export_rejected(client, text):
    response = client.post('/api/integrations/scopesentry/preview', json={'source_key': 'fixture', 'export': text})
    assert response.status_code == 422
    assert client.app.state.store.count('import_previews') == 0


def test_mixed_export_unknown_fields_utf8_and_duplicate_ids(client):
    plan = preview(client, [row(1), row(2, type='tcp'), {'url':'https://no-id.invalid/'}])
    assert [r['status'] for r in plan['rows']] == ['ready','unsupported','invalid']
    assert apply(client, plan).status_code == 200
    response = client.post('/api/integrations/scopesentry/preview', json={'source_key':'fixture','export':'한'*400000})
    assert response.status_code == 413
    response = client.post('/api/integrations/scopesentry/preview', json={'source_key':'fixture','export':json.dumps(row()),'unexpected':True})
    assert response.status_code == 422
    response = client.post('/api/integrations/scopesentry/preview', json={'source_key':'fixture','export':json.dumps(row())+'\n'+json.dumps(row())})
    assert response.status_code == 422


def test_source_pages_search_watermark_and_missing_asset(client):
    result = apply(client, preview(client, [row(i) for i in range(1, 32)])).json()
    asset_id = result['items'][0]['asset_id']
    path = '/api/assets/' + asset_id + '/sources'
    first = client.get(path).json()
    assert first['total'] == 31 and len(first['items']) == 25 and first['has_more']
    apply(client, preview(client, [row(32)]) )
    second = client.get(path, params={'offset':25,'snapshot':first['snapshot']}).json()
    assert second['total'] == 31 and len(second['items']) == 6
    assert client.get(path, params={'search':row(32)['_id']}).json()['total'] == 1
    assert client.get(path, params={'search':"' OR 1=1 --"}).json()['total'] == 0
    assert client.get('/api/assets/missing/sources').status_code == 404
    assert client.get(path, params={'limit':101}).status_code == 422


def test_preview_admission_expiry_cleanup_and_audit_chain(client):
    store=client.app.state.store
    for i in range(50):
        store.put('import_previews', {'id':str(i),'expires_at':99999999999})
    assert client.post('/api/integrations/scopesentry/preview',json={'source_key':'fixture','export':json.dumps(row())}).status_code == 429
    store.patch('import_previews','0',expires_at=1)
    plan=preview(client,[row()])
    assert store.count('import_previews') == 50
    assert apply(client,plan).status_code == 200
    assert client.post('/api/audit/verify',json={}).json()['valid'] is True


def test_import_links_history_and_retry_result_survive_backup_restore(client, tmp_path):
    from aegis.app import create_app
    from aegis.backups import backup_database, restore_database
    first = apply(client, preview(client, [row()])).json()
    changed_plan = preview(client, [row(url='https://restored-source.invalid/')])
    changed = apply(client, changed_plan).json()
    backup = tmp_path / 'source-snapshot.db'
    metadata = backup_database(client.app.state.store.path, backup)
    assert metadata['records']['asset_sources'] == 1
    assert metadata['records']['asset_source_history'] == 1
    destination = tmp_path / 'restored' / 'aegis.db'
    assert restore_database(backup, destination)['sessions_revoked']
    with TestClient(create_app(destination.parent, allow_private=True)) as restored:
        assert restored.post('/api/auth/login',json={'password':'aegis-test-password-only'}).status_code == 200
        old_id = first['items'][0]['asset_id']
        current_id = changed['items'][0]['asset_id']
        history = restored.get('/api/assets/' + old_id + '/sources?history=true').json()
        current = restored.get('/api/assets/' + current_id + '/sources').json()
        assert history['total'] == current['total'] == 1
        assert history['items'][0]['source_url'] == row()['url']
        assert current['items'][0]['source_url'] == 'https://restored-source.invalid/'
        assert apply(restored, changed_plan).json() == changed
        assert restored.app.state.store.count('assets') == 2
        assert restored.app.state.store.count('tasks') == 0
