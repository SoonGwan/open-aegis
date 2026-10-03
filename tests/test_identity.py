import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from fastapi.testclient import TestClient
from aegis.app import create_app
from aegis.auth import password_hash
from aegis.store import Store
from aegis.maintenance import WorkspaceBusy
import pytest
from tests.test_validation import client, register

PASSWORD = 'identity-fixture-password'


def add(client, role, username=None):
    response = client.post('/api/users', json={'username': username or role, 'name': role, 'role': role, 'password': PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()


@contextmanager
def login(app, username, password=PASSWORD):
    other = TestClient(app)
    response = other.post('/api/auth/login', json={'username': username, 'password': password})
    assert response.status_code == 200, response.text
    try:
        yield other
    finally:
        other.close()


def test_viewer_cannot_mutate_and_operator_cannot_approve(client):
    viewer = add(client, 'viewer')
    operator = add(client, 'operator')
    asset = register(client, 'https://fixture.invalid/')
    with login(client.app, viewer['username']) as v, login(client.app, operator['username']) as op:
        assert v.get('/api/assets').status_code == 200
        for path, data in [('/api/assets', {'name':'asset','url':'https://other.invalid/','authorized':True}),
                           ('/api/tasks', {'name':'task','asset_ids':[asset['id']]}),
                           ('/api/notes', {'title':'note','content':'test'}),
                           ('/api/schedules', {'name':'schedule','asset_ids':[asset['id']], 'interval_hours':24})]:
            assert v.post(path, json=data).status_code == 403
        assert v.get('/api/users').status_code == 403
        task = op.post('/api/tasks', json={'name':'plan','asset_ids':[asset['id']]}).json()
        assert task['status'] == 'pending'
        assert op.post('/api/tasks/'+task['id']+'/approve').status_code == 403
        assert op.post('/api/tasks/'+task['id']+'/stop').status_code == 200
        assert op.get('/api/users').status_code == 403
        assert op.post('/api/users', json={'username':'admin2','name':'admin2','role':'admin','password':PASSWORD}).status_code == 403


def test_identity_public_payloads_do_not_expose_hashes(client):
    user = add(client, 'viewer', 'CaseUser')
    assert user['username'] == 'caseuser'
    for response in (client.get('/api/users'), client.get('/api/auth/status')):
        assert 'password_hash' not in response.text and 'salt' not in response.text
    with login(client.app, 'CASEUSER') as v:
        status = v.get('/api/auth/status').json()
        assert status['user']['role'] == 'viewer'
        assert status['user']['id'] == user['id']
    assert client.post('/api/users', json={'username':'caseuser','name':'duplicate','role':'admin','password':PASSWORD}).status_code == 409


def test_role_and_disable_changes_revoke_all_sessions(client):
    user = add(client, 'operator')
    with login(client.app, 'operator') as first, login(client.app, 'operator') as second:
        assert client.patch('/api/users/'+user['id'], json={'role':'viewer'}).status_code == 200
        assert first.get('/api/assets').status_code == 401
        assert second.get('/api/assets').status_code == 401
    with login(client.app, 'operator') as current:
        assert client.patch('/api/users/'+user['id'], json={'disabled':True}).status_code == 200
        assert current.get('/api/assets').status_code == 401
        assert current.post('/api/auth/login', json={'username':'operator','password':PASSWORD}).status_code == 401


def test_last_admin_guard_and_password_changes(client):
    admin = client.get('/api/auth/status').json()['user']
    assert client.patch('/api/users/'+admin['id'], json={'disabled':True}).status_code == 409
    assert client.patch('/api/users/'+admin['id'], json={'role':'viewer'}).status_code == 409
    user = add(client, 'viewer')
    with login(client.app, 'viewer') as v:
        assert v.post('/api/auth/password', json={'current_password':'wrong-password','new_password':'replacement-fixture-password'}).status_code == 403
        assert v.post('/api/auth/password', json={'current_password':PASSWORD,'new_password':'replacement-fixture-password'}).status_code == 200
        assert v.get('/api/assets').status_code == 401
        assert v.post('/api/auth/login', json={'username':'viewer','password':PASSWORD}).status_code == 401
        assert v.post('/api/auth/login', json={'username':'viewer','password':'replacement-fixture-password'}).status_code == 200
        assert client.post('/api/users/'+user['id']+'/password', json={'password':'reset-fixture-password'}).status_code == 200
        assert v.get('/api/assets').status_code == 401
    events = client.get('/api/events').text
    assert PASSWORD not in events and 'replacement-fixture-password' not in events
    assert 'actor_id' in events


def test_two_admins_cannot_concurrently_remove_last_admin(client):
    a = client.get('/api/auth/status').json()['user']
    b = add(client, 'admin', 'second-admin')
    with login(client.app, b['username']) as second:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(client.patch, '/api/users/'+a['id'], json={'role':'viewer'}),
                       pool.submit(second.patch, '/api/users/'+b['id'], json={'role':'viewer'})]
            codes = sorted(f.result().status_code for f in futures)
        assert codes == [200, 409]
        assert sum(u['role']=='admin' and not u['disabled'] for u in client.app.state.store.users()) == 1


def test_old_auth_migration_and_session_revocation(tmp_path):
    path = tmp_path/'aegis.db'
    salt = '01'*16
    with sqlite3.connect(path) as db:
        db.executescript('CREATE TABLE records(kind TEXT,id TEXT,data TEXT,PRIMARY KEY(kind,id)); CREATE TABLE events(seq INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL,task_id TEXT,level TEXT,message TEXT,detail TEXT); CREATE TABLE sessions(digest TEXT PRIMARY KEY,expires REAL);')
        db.execute('INSERT INTO records VALUES(?,?,?)', ('settings','auth',json.dumps({'id':'auth','salt':salt,'password_hash':password_hash(PASSWORD,salt)})))
        db.execute('INSERT INTO records VALUES(?,?,?)', ('assets','fixture',json.dumps({'id':'fixture','url':'https://example.invalid/'})))
        db.execute('INSERT INTO sessions VALUES(?,?)', ('legacy-session',9999999999))
    store = Store(path)
    assert store.user(username='admin')['password_hash'] == password_hash(PASSWORD,salt)
    assert store.get('settings','auth') is None
    assert store.get('assets','fixture')['url'] == 'https://example.invalid/'
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 0
        assert db.execute('PRAGMA user_version').fetchone()[0] == 1
    backups = list(tmp_path.glob('*.pre-schema1-*.db'))
    assert len(backups) == 1 and backups[0].stat().st_mode & 0o777 == 0o600
    Store(path)
    assert len(list(tmp_path.glob('*.pre-schema1-*.db'))) == 1
    with TestClient(create_app(tmp_path)) as migrated:
        assert migrated.get('/api/auth/status').json()['setup_required'] is False
        assert migrated.post('/api/auth/login', json={'password':PASSWORD}).status_code == 200


def test_future_schema_refused_and_migration_rollback(tmp_path):
    path = tmp_path/'future.db'
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA user_version=9')
    original = path.read_bytes()
    with pytest.raises(RuntimeError, match='최신'):
        Store(path)
    assert path.read_bytes() == original
    broken = tmp_path/'broken.db'
    with sqlite3.connect(broken) as db:
        db.execute('CREATE TABLE records(kind TEXT,id TEXT,data TEXT,PRIMARY KEY(kind,id))')
        db.execute('INSERT INTO records VALUES(?,?,?)', ('settings','auth','{"id":"auth"}'))
    with pytest.raises(KeyError):
        Store(broken)
    with sqlite3.connect(broken) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 0
        assert db.execute("SELECT name FROM sqlite_master WHERE name='users'").fetchone() is None
        assert db.execute('SELECT COUNT(*) FROM records').fetchone()[0] == 1


def test_workspace_cannot_be_opened_twice(client):
    with pytest.raises(WorkspaceBusy):
        create_app(client.app.state.store.path.parent)


def test_nonsecurity_profile_change_keeps_session_and_scheme_csrf_rejected(client):
    admin = client.get('/api/auth/status').json()['user']
    assert client.patch('/api/users/'+admin['id'], json={'name':'New name','role':'admin','disabled':False}).status_code == 200
    assert client.get('/api/assets').status_code == 200
    assert client.post('/api/notes', json={'title':'note','content':'test'}, headers={'Origin':'https://testserver'}).status_code == 403
    assert client.post('/api/notes', json={'title':'note','content':'test'}, headers={'Origin':'http://testserver'}).status_code == 200


def test_stale_user_edit_is_rejected(client):
    user = add(client, 'viewer', 'stale.user')
    assert client.patch('/api/users/'+user['id'], json={'name':'Changed by admin','expected_updated_at':user['updated_at']}).status_code == 200
    response = client.patch('/api/users/'+user['id'], json={'role':'admin','expected_updated_at':user['updated_at']})
    assert response.status_code == 409
    assert client.app.state.store.user(id=user['id'])['role'] == 'viewer'


def test_validation_errors_do_not_echo_passwords(client):
    response = client.post('/api/auth/login', json={'password':'secret123'})
    assert response.status_code == 422
    assert 'secret123' not in response.text
    assert all('input' not in item and 'ctx' not in item for item in response.json()['detail'])
    response = client.post('/api/users', json={'username':'invalid space', 'name':'Invalid','role':'viewer','password':PASSWORD})
    assert response.status_code == 422
    assert PASSWORD not in response.text
