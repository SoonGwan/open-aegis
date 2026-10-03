from concurrent.futures import ThreadPoolExecutor
import threading

import pytest
from fastapi.testclient import TestClient

from aegis.audit_review import AuditReview, AuditReviewBusy
from aegis.store import Store
from tests.test_validation import client
from tests.test_identity import add, login


def test_admin_review_is_readonly_private_and_compares_prefix(client):
    store = client.app.state.store
    store.event(None, 'DO-NOT-EXPOSE-EVENT', detail={'secret': 'DO-NOT-EXPOSE-DETAIL'})
    before = store.audit_integrity()
    response = client.post('/api/audit/verify', json={})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    result = response.json()
    assert result['status'] == 'verified' and result['checkpoint_compared'] is False
    assert result['checkpoint'] == before['checkpoint']
    assert 'DO-NOT-EXPOSE' not in response.text
    assert store.audit_integrity() == before  # No verification event or repair.
    store.event(None, 'new event')
    assert client.post('/api/audit/verify', json={'checkpoint': before['checkpoint']}).json()['checkpoint_compared'] is True
    wrong = {**before['checkpoint'], 'hash': 'f' * 64}
    assert client.post('/api/audit/verify', json={'checkpoint': wrong}).json()['status'] == 'mismatch'
    with store.connect() as db:
        db.execute("UPDATE events SET message='DO-NOT-EXPOSE-TAMPER' WHERE seq=1")
    damaged = client.post('/api/audit/verify', json={})
    assert damaged.json()['status'] == 'mismatch'
    assert 'DO-NOT-EXPOSE' not in damaged.text
    with store.connect() as db:
        assert db.execute('SELECT message FROM events WHERE seq=1').fetchone()[0] == 'DO-NOT-EXPOSE-TAMPER'


def test_review_auth_roles_and_strict_checkpoint(client):
    with TestClient(client.app) as anonymous:
        assert anonymous.post('/api/audit/verify', json={}).status_code == 401
    for role in ('viewer', 'operator'):
        add(client, role)
        with login(client.app, role) as other:
            assert other.post('/api/audit/verify', json={}).status_code == 403
    checkpoint = client.app.state.store.audit_integrity()['checkpoint']
    for patch in ({'seq': True}, {'seq': -1}, {'seq': 1.2}, {'hash': 'bad'}, {'chain_id': 'bad'}, {'extra': 'untrusted'}):
        assert client.post('/api/audit/verify', json={'checkpoint': {**checkpoint, **patch}}).status_code == 422


def test_review_busy_http_is_retryable(client, monkeypatch):
    def busy(*args):
        raise AuditReviewBusy()
    monkeypatch.setattr(AuditReview, 'run', busy)
    response = client.post('/api/audit/verify', json={})
    assert response.status_code == 429
    assert response.headers['retry-after'] == '5'
    assert response.headers['cache-control'] == 'no-store'


def test_review_timeout_read_error_and_capacity_release(tmp_path, monkeypatch):
    import aegis.audit_review as module
    store = Store(tmp_path/'audit.db')
    store.event(None, 'event')
    service = AuditReview(store.path, timeout=0)
    assert service.run()['status'] == 'inconclusive'
    service.timeout = 10
    assert service.run()['status'] == 'verified'
    missing = AuditReview(tmp_path/'missing.db')
    assert missing.run()['status'] == 'inconclusive'
    assert not (tmp_path/'missing.db').exists()
    original = module.verify_chain
    entered, release = threading.Event(), threading.Event()

    def held(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, 'verify_chain', held)
    with ThreadPoolExecutor(max_workers=1) as executor:
        running = executor.submit(service.run)
        assert entered.wait(5)
        try:
            with pytest.raises(AuditReviewBusy):
                service.run()
        finally:
            release.set()
        assert running.result()['status'] == 'verified'
    assert service.run()['status'] == 'verified'
