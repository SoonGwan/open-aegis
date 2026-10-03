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
            db.execute("CREATE INDEX IF NOT EXISTS records_task_status_approval ON records(json_extract(data,'$.status'),json_extract(data,'$.approved_at')) WHERE kind='tasks'")
            db.execute("CREATE INDEX IF NOT EXISTS records_schedule_due ON records(kind,json_extract(data,'$.next_at')) WHERE kind='schedules' AND json_extract(data,'$.enabled')=1")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15, factory=ClosingConnection)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def put(self, kind, record):
        self.put_many([(kind, record)])
        return record

    def put_many(self, records):
        with self.lock, self.connect() as db:
            db.executemany("INSERT INTO records VALUES (?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
                           [(kind, record['id'], json.dumps(record, ensure_ascii=False)) for kind, record in records])

    def get(self, kind, id):
        with self.connect() as db:
            row = db.execute("SELECT data FROM records WHERE kind=? AND id=?", (kind, id)).fetchone()
        return json.loads(row['data']) if row else None

    def all(self, kind):
        with self.connect() as db:
            rows = db.execute("SELECT data FROM records WHERE kind=? ORDER BY rowid DESC", (kind,)).fetchall()
        return [json.loads(row['data']) for row in rows]

    def page(self, kind, *, limit=25, offset=0, snapshot=None, search='', filters=None, archived=None):
        """Bounded SQL reads; an insertion watermark keeps later inserts out of a page walk.

        Updates remain live. The watermark is not a historical database snapshot.
        """
        fields = {
            'assets': ('name', 'url', 'owner', 'tags'),
            'tasks': ('name', 'status', 'goal'),
            'findings': ('title', 'asset_name', 'check', 'severity', 'status'),
            'traffic': ('url', 'method', 'status'),
            'coverage': ('check', 'status'),
            'observations': ('url', 'title', 'asset_id', 'task_id'),
            'finding_history': ('action', 'reason'),
            'notes': ('title', 'content'),
            'schedules': ('task.name', 'task.goal'),
            'evidence': ('check', 'task_id'),
            'retests': ('conclusion', 'state_note', 'task_id'),
        }
        if kind not in fields or not 1 <= limit <= 1000 or offset < 0 or (snapshot is not None and snapshot < 0):
            raise ValueError('Invalid record query')
        filters = filters or {}
        if not filters.keys() <= {'status', 'severity', 'asset_id', 'task_id', 'check', 'finding_id', 'enabled'}:
            raise ValueError('Unknown record filter')
        if 'enabled' in filters and kind != 'schedules':
            raise ValueError('Enabled filter is only valid for schedules')
        with self.connect() as db:
            db.execute('BEGIN')
            if snapshot is None:
                snapshot = db.execute('SELECT coalesce(max(rowid),0) FROM records WHERE kind=?', (kind,)).fetchone()[0]
            clauses, args = ['kind=?', 'rowid<=?'], [kind, snapshot]
            if search:
                expression = " || ' ' || ".join(f"coalesce(json_extract(data,'$.{field}'),'')" for field in fields[kind])
                if kind == 'observations':
                    for source, reference in (('assets', 'asset_id'), ('tasks', 'task_id')):
                        expression += f" || ' ' || coalesce((SELECT json_extract(source.data,'$.name') FROM records source WHERE source.kind='{source}' AND source.id=json_extract(records.data,'$.{reference}')),'')"
                # instr treats %, _, quotes and SQL fragments as literal search text.
                clauses.append(f'instr(lower({expression}),lower(?))>0')
                args.append(search)
            for key, value in filters.items():
                if key == 'finding_id' and kind == 'evidence':
                    clauses.append("""id IN (SELECT ref.value FROM records f CROSS JOIN json_each(f.data,'$.evidence_ids') ref
                      WHERE f.kind='findings' AND f.id=?)""")
                    args.append(value)
                    clauses.append("""EXISTS (SELECT 1 FROM records f WHERE f.kind='findings' AND f.id=?
                        AND json_extract(records.data,'$.asset_id')=json_extract(f.data,'$.asset_id')
                        AND json_extract(records.data,'$.check')=json_extract(f.data,'$.check')
                        AND json_extract(records.data,'$.fingerprint')=json_extract(f.data,'$.fingerprint')
                        AND json_extract(records.data,'$.task_id') IN (SELECT value FROM json_each(f.data,'$.task_ids')))""")
                elif key == 'task_id' and kind == 'findings':
                    clauses.append("EXISTS (SELECT 1 FROM json_each(records.data,'$.task_ids') WHERE value=?)")
                elif key == 'asset_id' and kind == 'tasks':
                    clauses.append("EXISTS (SELECT 1 FROM json_each(records.data,'$.asset_ids') WHERE value=?)")
                elif key == 'asset_id' and kind == 'schedules':
                    clauses.append("EXISTS (SELECT 1 FROM json_each(records.data,'$.task.asset_ids') WHERE value=?)")
                else:
                    clauses.append(f"json_extract(data,'$.{key}')=?")
                args.append(value)
            if archived is not None:
                if kind != 'assets':
                    raise ValueError('Archive filter is only valid for assets')
                clauses.append("coalesce(json_extract(data,'$.archived_at'),0)" + ('!=0' if archived else '=0'))
            where = ' AND '.join(clauses)
            total = db.execute('SELECT count(*) FROM records WHERE ' + where, args).fetchone()[0]
            rows = db.execute('SELECT data FROM records WHERE ' + where + ' ORDER BY rowid DESC LIMIT ? OFFSET ?',
                              (*args, limit, offset)).fetchall()
            items = [json.loads(row['data']) for row in rows]
            if kind == 'observations' and items:
                for source, reference, name in (('assets', 'asset_id', 'asset_name'), ('tasks', 'task_id', 'task_name')):
                    ids = list(dict.fromkeys(item[reference] for item in items if item.get(reference)))
                    names = dict(db.execute("SELECT id,json_extract(data,'$.name') FROM records WHERE kind=? AND id IN (" + ','.join('?' for _ in ids) + ')', [source, *ids]).fetchall()) if ids else {}
                    for item in items:
                        item[name] = names.get(item.get(reference))
            if kind == 'assets' and items:
                counts = dict(db.execute("SELECT json_extract(data,'$.asset_id'),count(DISTINCT json_extract(data,'$.check')) FROM records WHERE kind='coverage' AND json_extract(data,'$.asset_id') IN (" + ','.join('?' for _ in items) + ") AND json_extract(data,'$.status')='completed' GROUP BY json_extract(data,'$.asset_id')", [item['id'] for item in items]).fetchall())
                for item in items:
                    item['completed_check_count'] = counts.get(item['id'], 0)
                from .coverage import latest_summary
                latest = latest_summary(db, [item['id'] for item in items])['assets']
                for item in items:
                    item['coverage_summary'] = latest.get(item['id'])
        return {'items': items, 'total': total,
                'limit': limit, 'offset': offset, 'snapshot': snapshot, 'has_more': offset + len(rows) < total}

    def due_schedules(self, timestamp, limit=100):
        """Only materialize the oldest due, enabled schedules for one scheduler batch."""
        if not 1 <= limit <= 100:
            raise ValueError('Invalid schedule batch size')
        with self.connect() as db:
            rows = db.execute("SELECT data FROM records WHERE kind='schedules' AND json_extract(data,'$.enabled')=1 AND json_extract(data,'$.next_at')<=? ORDER BY json_extract(data,'$.next_at'),rowid LIMIT ?", (timestamp, limit)).fetchall()
        return [json.loads(row['data']) for row in rows]

    def count(self, kind, *, statuses=None, active_assets=False):
        clauses, args = ['kind=?'], [kind]
        if statuses:
            clauses.append("json_extract(data,'$.status') IN (" + ','.join('?' for _ in statuses) + ')')
            args.extend(statuses)
        if active_assets:
            clauses.append("coalesce(json_extract(data,'$.archived_at'),0)=0")
        with self.connect() as db:
            return db.execute('SELECT count(*) FROM records WHERE ' + ' AND '.join(clauses), args).fetchone()[0]

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
