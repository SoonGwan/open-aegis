from concurrent.futures import ThreadPoolExecutor
import importlib
import threading

import pytest
from fastapi.testclient import TestClient

from aegis.login_limits import LoginGate, LoginLimited
from tests.test_validation import client


def test_rate_window_expiry_and_capacity_cannot_evict_live_history():
    timestamp = [0.0]
    gate = LoginGate(window=10, attempts=2, addresses=2, clock=lambda: timestamp[0])
    for _ in range(2):
        with gate.attempt('a'):
            pass
    with pytest.raises(LoginLimited) as limited:
        with gate.attempt('a'):
            pytest.fail('rate-limited work entered')
    assert limited.value.reason == 'rate' and limited.value.retry_after == 10
    timestamp[0] = 3
    with gate.attempt('b'):
        pass
    for index in range(1000):
        with pytest.raises(LoginLimited) as limited:
            with gate.attempt(f'new-address-{index}'):
                pytest.fail('capacity-limited work entered')
        assert limited.value.reason == 'capacity'
    assert gate.metrics()['tracked_addresses'] == 2
    assert gate.metrics()['denied']['capacity'] == 1000
    with pytest.raises(LoginLimited) as limited:
        with gate.attempt('a'):
            pass
    assert limited.value.reason == 'rate'  # Address rotation did not erase a.
    timestamp[0] = 10
    with gate.attempt('c'):
        pass
    assert set(gate.addresses) == {'b', 'c'}
    timestamp[0] = 20
    assert gate.metrics()['tracked_addresses'] == 0


def test_busy_rejection_does_not_consume_attempt_and_exception_releases_slot():
    gate = LoginGate(attempts=1, parallel=1)
    with pytest.raises(ValueError):
        with gate.attempt('first'):
            with pytest.raises(LoginLimited) as limited:
                with gate.attempt('second'):
                    pass
            assert limited.value.reason == 'busy'
            assert gate.metrics()['active'] == 1
            assert gate.metrics()['tracked_addresses'] == 1
            raise ValueError('hash or storage failed')
    assert gate.metrics()['active'] == 0
    with gate.attempt('second') as attempt:
        attempt.succeeded()
    assert set(gate.addresses) == {'first'}


def test_late_success_retains_newer_attempt_history():
    gate = LoginGate(attempts=2)
    with gate.attempt('shared') as older:
        with gate.attempt('shared'):
            pass
        older.succeeded()
        assert len(gate.addresses['shared']) == 1
    with gate.attempt('shared'):
        pass
    with pytest.raises(LoginLimited):
        with gate.attempt('shared'):
            pass


def test_login_rate_http_retry_and_success_reset(client, monkeypatch):
    module = importlib.import_module('aegis.app')
    calls = []
    original = module.password_hash

    def count(password, salt):
        calls.append(1)
        return original(password, salt)

    monkeypatch.setattr(module, 'password_hash', count)
    for _ in range(10):
        assert client.post('/api/auth/login', json={'password': 'wrong-fixture-password'}).status_code == 401
    limited = client.post('/api/auth/login', json={'password': 'aegis-test-password-only'})
    assert limited.status_code == 429
    assert 1 <= int(limited.headers['retry-after']) <= 300
    assert len(calls) == 10  # Rejected request never derives a password hash.
    metrics = client.get('/api/runtime').json()['authentication']
    assert metrics['tracked_addresses'] == 1 and metrics['active'] == 0
    assert metrics['denied']['rate'] == 1
    assert 'testclient' not in str(metrics) and 'password' not in str(metrics)


def test_http_parallel_admission_releases_after_failed_password(tmp_path, monkeypatch):
    module = importlib.import_module('aegis.app')
    gate = LoginGate(parallel=1)
    monkeypatch.setattr(module, 'LoginGate', lambda: gate)
    app = module.create_app(tmp_path)
    entered, release = threading.Event(), threading.Event()
    calls = []

    def held_hash(*args):
        calls.append(1)
        entered.set()
        assert release.wait(5)
        return '00' * 32

    with TestClient(app) as api:
        assert api.post('/api/auth/setup', json={'password': 'aegis-test-password-only'}).status_code == 200
        monkeypatch.setattr(module, 'password_hash', held_hash)
        with ThreadPoolExecutor(max_workers=1) as workers:
            pending = workers.submit(api.post, '/api/auth/login', json={'password':'wrong-fixture-password'})
            assert entered.wait(5)
            try:
                denied = api.post('/api/auth/login', json={'password':'wrong-fixture-password'})
                assert denied.status_code == 429 and denied.headers['retry-after'] == '1'
                assert api.get('/api/health').status_code == 200
                assert len(calls) == 1 and gate.metrics()['active'] == 1
            finally:
                release.set()
            assert pending.result().status_code == 401
        assert gate.metrics()['active'] == 0
        assert api.post('/api/auth/login', json={'password':'wrong-fixture-password'}).status_code == 401


def test_successful_login_clears_earlier_failed_attempts(client):
    assert client.post('/api/auth/login', json={'password':'wrong-fixture-password'}).status_code == 401
    assert client.get('/api/runtime').json()['authentication']['tracked_addresses'] == 1
    assert client.post('/api/auth/login', json={'password':'aegis-test-password-only'}).status_code == 200
    assert client.get('/api/runtime').json()['authentication']['tracked_addresses'] == 0
