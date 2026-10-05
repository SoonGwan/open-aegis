"""SQLite persistence. Connections are short-lived and writes serialized."""
import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager, nullcontext
from pathlib import Path


from .store_util import now, identifier
from .migrations import migrate
from .audit import append_event, verify_chain
from .call_ledger import commit as commit_call

# Read clients page proofs and retests separately instead of serializing growing ID arrays.
FINDING_READ_PROJECTION = "json_set(json_remove(data,'$.evidence_ids','$.task_ids'),'$.evidence_reference_count',coalesce(json_array_length(data,'$.evidence_ids'),0),'$.task_count',coalesce(json_array_length(data,'$.task_ids'),0),'$.related_ids_omitted',json('true'))"

def compact_finding(record):
    """Project an already committed decision without re-reading a later concurrent edit."""
    return {**{key:value for key,value in record.items() if key not in ('task_ids','evidence_ids')},
            'task_count':len(record.get('task_ids') or []),
            'evidence_reference_count':len(record.get('evidence_ids') or []), 'related_ids_omitted':True}


class MessageRequestConflict(ValueError):
    """A committed message request key was reused with different content."""


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
            db.execute("CREATE INDEX IF NOT EXISTS records_asset_url ON records(json_extract(data,'$.url')) WHERE kind='assets'")
            db.execute("CREATE INDEX IF NOT EXISTS records_source_asset ON records(kind,json_extract(data,'$.asset_id')) WHERE kind IN ('asset_sources','asset_source_history')")
            db.execute("CREATE INDEX IF NOT EXISTS records_task_status_approval ON records(json_extract(data,'$.status'),json_extract(data,'$.approved_at')) WHERE kind='tasks'")
            db.execute("CREATE INDEX IF NOT EXISTS records_schedule_due ON records(kind,json_extract(data,'$.next_at')) WHERE kind='schedules' AND json_extract(data,'$.enabled')=1")
            db.execute("CREATE INDEX IF NOT EXISTS records_calls_state ON records(json_extract(data,'$.state'),json_extract(data,'$.source')) WHERE kind='llm_calls'")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15, factory=ClosingConnection)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def put(self, kind, record):
        self.put_many([(kind, record)])
        return record

    @contextmanager
    def read_transaction(self):
        with self.connect() as db:
            db.execute('BEGIN')
            yield db

    @contextmanager
    def write_transaction(self):
        with self.lock, self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            yield db

    def put_many(self, records, *, connection=None):
        with (nullcontext(connection) if connection is not None else self.write_transaction()) as db:
            db.executemany("INSERT INTO records VALUES (?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
                           [(kind, record['id'], json.dumps(record, ensure_ascii=False)) for kind, record in records])

    def put_message_exchange(self, question, reply):
        """Commit one exchange, or replay its original reply under a SQLite write lock."""
        with self.lock, self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute("SELECT data FROM records WHERE kind='messages' AND id=?",
                                  (question['id'],)).fetchone()
            if existing:
                original = json.loads(existing['data'])
                if (original['content'] != question['content'] or
                        original.get('mode','rules') != question.get('mode','rules')):
                    raise MessageRequestConflict('message request content conflict')
                stored = db.execute("SELECT data FROM records WHERE kind='messages' AND id=?",
                                    (reply['id'],)).fetchone()
                if not stored:
                    raise RuntimeError('message exchange is incomplete')
                return json.loads(stored['data'])
            db.executemany("INSERT INTO records VALUES ('messages',?,?)",
                           [(record['id'], json.dumps(record, ensure_ascii=False))
                            for record in (question, reply)])
            if reply.get('assistant_generation'):
                commit_call(db,reply['assistant_generation'],reply['task_id'],'conversation','messages',reply['id'])
                append_event(db,(now(),reply['task_id'],'info','AI 대화 호출 결과',
                                 json.dumps(reply['assistant_generation'],ensure_ascii=False)))
        return reply

    def get(self, kind, id, *, compact_findings=False, connection=None):
        with (nullcontext(connection) if connection is not None else self.connect()) as db:
            projection = FINDING_READ_PROJECTION if kind == 'findings' and compact_findings else 'data'
            row = db.execute("SELECT " + projection + " AS data FROM records WHERE kind=? AND id=?", (kind, id)).fetchone()
        return json.loads(row['data']) if row else None

    def recovery_tasks(self):
        """Read only unfinished tasks in bounded keyset batches, closing before writes."""
        with self.connect() as db:
            upper = db.execute('SELECT coalesce(max(rowid),0) FROM records').fetchone()[0]
        before = None
        while True:
            with self.connect() as db:
                rows = db.execute("SELECT rowid,data FROM records WHERE kind='tasks' AND rowid<=? AND (? IS NULL OR rowid<?) "
                                  "AND json_extract(data,'$.status') IN ('running','queued','stopping') "
                                  "ORDER BY rowid DESC LIMIT 100", (upper, before, before)).fetchall()
            if not rows:
                return
            before = rows[-1]['rowid']
            for row in rows:
                yield json.loads(row['data'])

    def asset_url_exists(self, url, exclude_id=None):
        with self.connect() as db:
            return db.execute("SELECT 1 FROM records WHERE kind='assets' "
                              "AND json_extract(data,'$.url')=? AND (? IS NULL OR id!=?) LIMIT 1",
                              (url, exclude_id, exclude_id)).fetchone() is not None

    def asset_has_tasks(self, asset_id, *, active_only=False):
        active = " AND json_extract(data,'$.status') IN ('queued','running','stopping')" if active_only else ''
        with self.connect() as db:
            return db.execute("SELECT 1 FROM records WHERE kind='tasks'" + active +
                              " AND EXISTS (SELECT 1 FROM json_each(records.data,'$.asset_ids') WHERE value=?) LIMIT 1",
                              (asset_id,)).fetchone() is not None

    def enabled_schedule_ids(self, asset_id):
        # Only IDs are needed to pause schedules. Keep a stable read snapshot while writes
        # use other short-lived connections; no schedule payloads are decoded here.
        with self.connect() as db:
            for row in db.execute("SELECT id FROM records WHERE kind='schedules' "
                                  "AND json_extract(data,'$.enabled')=1 AND EXISTS "
                                  "(SELECT 1 FROM json_each(records.data,'$.task.asset_ids') WHERE value=?)",
                                  (asset_id,)):
                yield row['id']

    def all(self, kind):
        with self.connect() as db:
            rows = db.execute("SELECT data FROM records WHERE kind=? ORDER BY rowid DESC", (kind,)).fetchall()
        return [json.loads(row['data']) for row in rows]

    def page(self, kind, *, limit=25, offset=0, snapshot=None, search='', filters=None, archived=None, compact_findings=False, priority=False, connection=None):
        """Bounded SQL reads; an insertion watermark keeps later inserts out of a page walk.

        Updates remain live. The watermark is not a historical database snapshot.
        """
        fields = {
            'assets': ('name', 'url', 'owner', 'tags'),
            'tasks': ('name', 'status', 'goal'),
            'task_archive_history':('actor.name','actor.username'),

            'notification_channels':('name','destination_id'),
            'notification_channel_versions':('action','actor.name','snapshot.name'),
            'notification_deliveries':('channel_id','task_id','status','payload.task_name','result_code'),
            'notification_attempts':('status','result_code'),
            'task_categories':('name',),
            'task_category_versions':('action','actor.name','snapshot.name'),
            'task_category_history':('actor.name','before.name','after.name'),
            'task_templates': ('name','description','category','definition.goal'),
            'task_template_history': ('action','actor.name','snapshot.name'),
            'findings': ('title', 'asset_name', 'check', 'severity', 'status'),
            'traffic': ('url', 'method', 'status'),
            'coverage': ('check', 'status'),
            'observations': ('url', 'title', 'asset_id', 'task_id'),
            'finding_history': ('action', 'reason', 'actor.name', 'actor.username'),
            'notes': ('title', 'content'),
            'todos': ('title', 'description', 'status', 'assignee_name'),
            'todo_history': ('action', 'reason', 'actor.name', 'actor.username'),
            'schedules': ('task.name', 'task.goal'),
            'evidence': ('id', 'check', 'task_id'),
            'retests': ('conclusion', 'state_note', 'task_id'),
            'messages': ('content', 'role'),
            'llm_calls': ('id', 'model', 'source', 'state', 'task_id'),
            'asset_sources': ('source_key', 'external_id', 'source_url'),
            'asset_source_history': ('source_key', 'external_id', 'source_url'),
        }
        if kind not in fields or not 1 <= limit <= 1000 or offset < 0 or (snapshot is not None and snapshot < 0):
            raise ValueError('Invalid record query')
        if priority and kind != 'findings':
            raise ValueError('Priority order is only valid for findings')
        filters = filters or {}
        if not filters.keys() <= {'status', 'severity', 'asset_id', 'task_id', 'check', 'finding_id', 'enabled', 'source', 'state', 'todo_id', 'category_id','channel_id','delivery_id'}:
            raise ValueError('Unknown record filter')
        if 'channel_id' in filters and kind!='notification_deliveries':raise ValueError('Channel filter requires deliveries')
        if 'delivery_id' in filters and kind!='notification_attempts':raise ValueError('Delivery filter requires attempts')
        if 'category_id' in filters and kind != 'tasks':raise ValueError('Category filter requires tasks')
        if 'todo_id' in filters and kind != 'todo_history':raise ValueError('Todo filter requires todo history')
        if ('source' in filters or 'state' in filters) and kind != 'llm_calls':
            raise ValueError('Call filters require provider attempts')
        if 'enabled' in filters and kind != 'schedules':
            raise ValueError('Enabled filter is only valid for schedules')
        with (nullcontext(connection) if connection is not None else self.connect()) as db:
            if connection is None:
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
                if key == 'category_id':
                    if value == 'unclassified':
                        clauses.append("json_extract(data,'$.category_ref.id') IS NULL")
                    else:
                        clauses.append("json_extract(data,'$.category_ref.id')=?");args.append(value)
                    continue
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
                if kind not in ('assets','tasks'):
                    raise ValueError('Archive filter requires assets or tasks')
                clauses.append("coalesce(json_extract(data,'$.archived_at'),0)" + ('!=0' if archived else '=0'))
            where = ' AND '.join(clauses)
            total = db.execute('SELECT count(*) FROM records WHERE ' + where, args).fetchone()[0]
            projection = FINDING_READ_PROJECTION if kind == 'findings' and compact_findings else 'data'
            order = "CASE json_extract(data,'$.severity') WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 WHEN 'info' THEN 4 ELSE 5 END, rowid DESC" if priority else 'rowid DESC'
            rows = db.execute('SELECT ' + projection + ' AS data FROM records WHERE ' + where + ' ORDER BY ' + order + ' LIMIT ? OFFSET ?',
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

    def event(self, task_id, message, level='info', detail=None, *, connection=None):
        with self.lock, (nullcontext(connection) if connection is not None else self.connect()) as db:
            append_event(db, (now(), task_id, level, message, json.dumps(detail or {}, ensure_ascii=False)))

    def record_planner_call(self, task_id, detail, message, level):
        """Commit bounded planner metadata and its audit event together."""
        with self.lock, self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT data FROM records WHERE kind='tasks' AND id=?", (task_id,)).fetchone()
            if row is None:
                raise KeyError(task_id)
            task = json.loads(row['data'])
            commit_call(db,detail,task_id,'planner','tasks',task_id)
            task['llm_usage'] = detail
            db.execute("UPDATE records SET data=? WHERE kind='tasks' AND id=?",
                       (json.dumps(task, ensure_ascii=False), task_id))
            append_event(db, (now(), task_id, level, message, json.dumps(detail, ensure_ascii=False)))

    def audit_integrity(self, checkpoint=None):
        with self.connect() as db:
            db.execute('BEGIN')
            return verify_chain(db, checkpoint)

    def events(self, after=0, task_id=None, limit=200, *, connection=None):
        query = 'SELECT * FROM events WHERE seq>?'
        args = [after]
        if task_id:
            query += ' AND task_id=?'
            args.append(task_id)
        query += ' ORDER BY seq LIMIT ?'
        args.append(limit)
        with (nullcontext(connection) if connection is not None else self.connect()) as db:
            rows = db.execute(query, args).fetchall()
        return [{**dict(row), 'detail': json.loads(row['detail'])} for row in rows]

    def event_progress(self, after, *, connection=None):
        if after is not None and (type(after) is not int or after<0):raise ValueError('Invalid event position')
        with (nullcontext(connection) if connection is not None else self.read_transaction()) as db:
            latest=db.execute('SELECT coalesce(max(seq),0) FROM events').fetchone()[0]
            if after is None:return {'latest_event_seq':latest,'pending_events':None,'first_pending_seq':None,'oldest_pending_at':None}
            row=db.execute('SELECT count(*),min(seq),min(ts) FROM events WHERE seq>?',(after,)).fetchone()
            return {'latest_event_seq':latest,'pending_events':row[0],'first_pending_seq':row[1],'oldest_pending_at':row[2]}

    def recent_events(self, limit=100):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM events ORDER BY seq DESC LIMIT ?', (limit,)).fetchall()
        return [{**dict(row), 'detail': json.loads(row['detail'])} for row in reversed(rows)]

    def event_page(self, task_id, *, limit=25, offset=0, snapshot=None, search='', asset_id=None, connection=None):
        if not 1 <= limit <= 100 or offset < 0 or (snapshot is not None and snapshot < 0):
            raise ValueError('Invalid event query')
        with (nullcontext(connection) if connection is not None else self.read_transaction()) as db:
            if snapshot is None:
                snapshot = db.execute('SELECT coalesce(max(seq),0) FROM events WHERE task_id=?', (task_id,)).fetchone()[0]
            where, args = 'task_id=? AND seq<=?', [task_id, snapshot]
            if asset_id is not None:
                where += " AND json_type(detail,'$.asset_id')='text' AND json_extract(detail,'$.asset_id')=?"
                args.append(asset_id)
            if search:
                where += " AND instr(lower(message||' '||level),lower(?))>0"
                args.append(search)
            total = db.execute('SELECT count(*) FROM events WHERE ' + where, args).fetchone()[0]
            items = [{**dict(row), 'detail': json.loads(row['detail'])} for row in db.execute('SELECT * FROM events WHERE ' + where + ' ORDER BY seq DESC LIMIT ? OFFSET ?', (*args,limit,offset))]
        return {'items':items,'total':total,'limit':limit,'offset':offset,'snapshot':snapshot,'has_more':offset+len(items)<total}

    def worker_event_page(self, *, limit=25, offset=0, snapshot=None, search='', task_id=None, asset_id=None, connection=None):
        if not 1 <= limit <= 100 or not 0 <= offset <= 10_000_000 or len(search) > 200 or (snapshot is not None and snapshot < 0):
            raise ValueError('Invalid Worker event query')
        with (nullcontext(connection) if connection is not None else self.read_transaction()) as db:
            if snapshot is None:snapshot=db.execute('SELECT coalesce(max(seq),0) FROM events').fetchone()[0]
            where="seq<=? AND json_type(detail,'$.asset_id')='text' AND length(json_extract(detail,'$.asset_id')) BETWEEN 1 AND 80 AND length(task_id) BETWEEN 1 AND 80"
            args=[snapshot]
            for field,value in (("task_id",task_id),("json_extract(detail,'$.asset_id')",asset_id)):
                if value is not None:where+=' AND '+field+'=?';args.append(value)
            if search:
                where+=" AND instr(lower(message||' '||level||' '||task_id||' '||json_extract(detail,'$.asset_id')),lower(?))>0";args.append(search)
            total=db.execute('SELECT count(*) FROM events WHERE '+where,args).fetchone()[0]
            items=[{**dict(row),'detail':json.loads(row['detail'])} for row in db.execute('SELECT * FROM events WHERE '+where+' ORDER BY seq DESC LIMIT ? OFFSET ?',(*args,limit,offset))]
            return {'items':items,'total':total,'limit':limit,'offset':offset,'snapshot':snapshot,'has_more':offset+len(items)<total}

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

    def user(self, *, id=None, username=None, connection=None):
        with (nullcontext(connection) if connection is not None else self.connect()) as db:
            row = db.execute('SELECT * FROM users WHERE ' + ('id=?' if id is not None else 'username=?'),
                             (id if id is not None else username,)).fetchone()
        return dict(row) if row else None

    def finding_by_fingerprint(self, fingerprint, *, connection=None):
        with (nullcontext(connection) if connection is not None else self.connect()) as db:
            row=db.execute("SELECT data FROM records WHERE kind='findings' AND json_extract(data,'$.fingerprint')=? ORDER BY rowid LIMIT 1",(fingerprint,)).fetchone()
            return json.loads(row['data']) if row else None

    def task_metrics(self):
        with self.connect() as db:
            db.execute('BEGIN')
            counts={row[0]:row[1] for row in db.execute("SELECT json_extract(data,'$.status'),count(*) FROM records WHERE kind='tasks' GROUP BY json_extract(data,'$.status')")}
            oldest=db.execute("SELECT min(json_extract(data,'$.approved_at')) FROM records WHERE kind='tasks' AND json_extract(data,'$.status')='queued'").fetchone()[0]
            timeouts=db.execute("SELECT count(*) FROM records WHERE kind='tasks' AND json_extract(data,'$.termination_reason') IN ('timeout','queue_timeout')").fetchone()[0]
            return {'tasks':counts,'oldest_queued_at':oldest,'timeouts':timeouts}

    def overdue_task_ids(self, before, limit=100):
        if not 1<=limit<=100:raise ValueError('Invalid queue batch size')
        with self.connect() as db:
            return [row['id'] for row in db.execute("SELECT id FROM records WHERE kind='tasks' AND json_extract(data,'$.status')='queued' AND json_extract(data,'$.approved_at')<? ORDER BY json_extract(data,'$.approved_at'),rowid LIMIT ?",(before,limit))]

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
