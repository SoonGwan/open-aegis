"""SQLite persistence. Connections are short-lived and writes serialized."""
import hashlib
import json
import sqlite3
import threading
from pathlib import Path


from .store_util import now, identifier
from .migrations import migrate


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        migrate(self.path)
        self.path.chmod(0o600)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15, factory=ClosingConnection)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def put(self, kind, record):
        with self.lock, self.connect() as db:
            db.execute("INSERT OR REPLACE INTO records VALUES (?,?,?)",
                       (kind, record['id'], json.dumps(record, ensure_ascii=False)))
        return record

    def get(self, kind, id):
        with self.connect() as db:
            row = db.execute("SELECT data FROM records WHERE kind=? AND id=?", (kind, id)).fetchone()
        return json.loads(row['data']) if row else None

    def all(self, kind):
        with self.connect() as db:
            rows = db.execute("SELECT data FROM records WHERE kind=? ORDER BY rowid DESC", (kind,)).fetchall()
        return [json.loads(row['data']) for row in rows]

    def patch(self, kind, id, **changes):
        with self.lock:
            record = self.get(kind, id)
            if record is None:
                raise KeyError(id)
            record.update(changes)
            return self.put(kind, record)

    def event(self, task_id, message, level='info', detail=None):
        with self.lock, self.connect() as db:
            db.execute("INSERT INTO events(ts,task_id,level,message,detail) VALUES(?,?,?,?,?)",
                       (now(), task_id, level, message, json.dumps(detail or {}, ensure_ascii=False)))

    def events(self, after=0, task_id=None, limit=200):
        query = 'SELECT * FROM events WHERE seq>?'
        args = [after]
        if task_id:
            query += ' AND task_id=?'
            args.append(task_id)
        query += ' ORDER BY seq LIMIT ?'
        args.append(limit)
        with self.connect() as db:
            rows = db.execute(query, args).fetchall()
        return [{**dict(row), 'detail': json.loads(row['detail'])} for row in rows]

    def recent_events(self, limit=100):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM events ORDER BY seq DESC LIMIT ?', (limit,)).fetchall()
        return [{**dict(row), 'detail': json.loads(row['detail'])} for row in reversed(rows)]

    def session(self, token, expires, user_id):
        with self.lock, self.connect() as db:
            db.execute('DELETE FROM sessions WHERE expires<?', (now(),))
            db.execute('INSERT INTO sessions VALUES (?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), expires, user_id))

    def session_user(self, token):
        with self.connect() as db:
            row = db.execute('SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.digest=? AND s.expires>? AND u.disabled=0',
                             (hashlib.sha256(token.encode()).hexdigest(), now())).fetchone()
        return dict(row) if row else None

    def valid_session(self, token):
        return self.session_user(token) is not None

    def user(self, *, id=None, username=None):
        with self.connect() as db:
            row = db.execute('SELECT * FROM users WHERE ' + ('id=?' if id is not None else 'username=?'),
                             (id if id is not None else username,)).fetchone()
        return dict(row) if row else None

    def users(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM users ORDER BY created_at,id')]

    def add_user(self, user):
        with self.lock, self.connect() as db:
            db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)',
                       tuple(user[k] for k in ('id','username','name','role','salt','password_hash','disabled','created_at','updated_at')))
        return user

    def update_user(self, id, **changes):
        if not changes.keys() <= {'name','role','disabled','salt','password_hash'}:
            raise ValueError('Unknown user field')
        changes['updated_at'] = now()
        with self.lock, self.connect() as db:
            before = db.execute('SELECT * FROM users WHERE id=?', (id,)).fetchone()
            security_changed = before and any(key in changes and changes[key] != before[key] for key in ('role', 'disabled', 'password_hash'))
            db.execute('UPDATE users SET ' + ','.join(f'{key}=?' for key in changes) + ' WHERE id=?', (*changes.values(), id))
            # Password/role/disabled changes invalidate all old sessions atomically.
            if security_changed:
                db.execute('DELETE FROM sessions WHERE user_id=?', (id,))
        return self.user(id=id)

    def logout(self, token):
        with self.lock, self.connect() as db:
            db.execute('DELETE FROM sessions WHERE digest=?', (hashlib.sha256(token.encode()).hexdigest(),))

    def backup(self, destination):
        from .backups import backup_database
        with self.lock:
            return backup_database(self.path, destination)
