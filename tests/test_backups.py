import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from aegis.app import create_app
from aegis.backups import backup_database, restore_database, validate_backup, InvalidBackup
from aegis.maintenance import WorkspaceBusy


def test_online_backup_offline_restore_and_session_revocation(tmp_path):
    directory = tmp_path/'live'
    app = create_app(directory)
    with TestClient(app) as client:
        client.post('/api/auth/setup', json={'password':'backup-fixture-password'})
        cookie = client.cookies.get('aegis_session')
        app.state.store.put('notes', {'id':'original','title':'preserve this'})
        backup = tmp_path/'backup ?한글.db'
        metadata = backup_database(app.state.store.path, backup)
        assert metadata['records']['notes'] == 1
        assert backup.stat().st_mode & 0o777 == 0o600
        with pytest.raises(FileExistsError):
            backup_database(app.state.store.path, backup)
        with pytest.raises(WorkspaceBusy):
            restore_database(backup, app.state.store.path)
        app.state.store.put('notes', {'id':'later','title':'keep rollback'})
    result = restore_database(backup, app.state.store.path)
    assert result['sessions_revoked']
    rollback = Path(result['rollback'])
    assert validate_backup(rollback)['records']['notes'] == 2
    with TestClient(create_app(directory)) as restored:
        restored.cookies.set('aegis_session',cookie)
        assert restored.get('/api/notes').status_code == 401
        assert restored.post('/api/auth/login',json={'password':'backup-fixture-password'}).status_code == 200
        assert restored.get('/api/notes').json() == [{'id':'original','title':'preserve this'}]
    assert not list(directory.glob('.restore-*'))


def test_invalid_backup_never_changes_destination(tmp_path):
    app = create_app(tmp_path/'live')
    with TestClient(app):
        pass
    path = app.state.store.path
    before = path.read_bytes()
    bad = tmp_path/'bad.db'
    bad.write_text('this is not a SQLite database')
    with pytest.raises(InvalidBackup):
        restore_database(bad,path)
    assert path.read_bytes() == before
    with sqlite3.connect(bad.with_name('future.db')) as db:
        db.execute('PRAGMA user_version=9')
    with pytest.raises(InvalidBackup,match='스키마'):
        restore_database(bad.with_name('future.db'),path)
    assert path.read_bytes() == before
    assert not list(path.parent.glob('*.pre-restore-*'))
