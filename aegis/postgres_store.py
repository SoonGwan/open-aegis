"""Native PostgreSQL persistence. HTTP/runtime integration is a separate pending step."""
import hashlib
import json
import threading
from contextlib import contextmanager, nullcontext

from . import postgres_transfer as transfer
from .audit import GENESIS, AuditIntegrityError, event_hash, validate_state
from .migrations import SCHEMA_VERSION
from .store import MessageRequestConflict
from .store_util import now

FIELDS = {
    'assets':('name','url','owner','tags'), 'tasks':('name','status','goal'),
    'findings':('title','asset_name','check','severity','status'),
    'traffic':('url','method','status'), 'coverage':('check','status'),
    'observations':('url','title','asset_id','task_id'),
    'finding_history':('action','reason','actor.name','actor.username'),
    'notes':('title','content'), 'schedules':('task.name','task.goal'),
    'evidence':('id','check','task_id'), 'retests':('conclusion','state_note','task_id'),
    'messages':('content','role'), 'llm_calls':('id','model','source','state','task_id'),
    'asset_sources':('source_key','external_id','source_url'),
    'asset_source_history':('source_key','external_id','source_url'),
}


def text(field, alias=''):
    # Only reviewed static paths/aliases call this builder; request values are bound.
    return f"{alias+'.' if alias else ''}data::jsonb #>> '{{{field.replace('.',',')}}}'"


def array(field,alias=''):
    expression=f"{alias+'.' if alias else ''}data::jsonb #> '{{{field.replace('.',',')}}}'"
    return f"CASE WHEN jsonb_typeof({expression})='array' THEN {expression} ELSE '[]'::jsonb END"


COMPACT = "(data::jsonb - 'evidence_ids' - 'task_ids') || jsonb_build_object('evidence_reference_count',jsonb_array_length("+array('evidence_ids')+"),'task_count',jsonb_array_length("+array('task_ids')+"),'related_ids_omitted',true)"


def encoded(record):
    if not isinstance(record,dict) or not isinstance(record.get('id'),str) or not record['id']:
        raise ValueError('Record requires a string ID')
    return json.dumps(record,ensure_ascii=False,allow_nan=False)


def append_event(db, values):
    """Caller owns the schema write transaction and advisory lock."""
    state=db.execute('SELECT * FROM audit_state WHERE id=1 FOR UPDATE').fetchone()
    validate_state(state)
    tail=db.execute('SELECT * FROM events ORDER BY seq DESC LIMIT 1').fetchone()
    last=tail['seq'] if tail else 0
    link=db.execute('SELECT * FROM event_hashes WHERE seq=%s',(last,)).fetchone()
    if state['last_seq']!=last or state['head_hash']!=(link['event_hash'] if link else GENESIS):
        raise AuditIntegrityError('감사 로그의 마지막 기록이 일치하지 않습니다.')
    if tail:
        prior=db.execute('SELECT h.event_hash FROM events e LEFT JOIN event_hashes h ON h.seq=e.seq WHERE e.seq<%s ORDER BY e.seq DESC LIMIT 1',(last,)).fetchone()
        previous=prior['event_hash'] if prior else GENESIS
        if not link or link['previous_hash']!=previous or event_hash(tail,previous)!=link['event_hash']:
            raise AuditIntegrityError('감사 로그의 마지막 연결이 일치하지 않습니다.')
    row=db.execute('INSERT INTO events(ts,task_id,level,message,detail) VALUES (%s,%s,%s,%s,%s) RETURNING *',values).fetchone()
    digest=event_hash(row,state['head_hash'])
    db.execute('INSERT INTO event_hashes VALUES (%s,%s,%s)',(row['seq'],state['head_hash'],digest))
    db.execute('UPDATE audit_state SET last_seq=%s,head_hash=%s WHERE id=1',(row['seq'],digest))
    # Keep the transfer sequence watermark compatible after runtime writes.
    db.execute('UPDATE storage_metadata SET event_sequence=%s WHERE id=1',(row['seq'],))
    return row['seq']


class PostgresStore:
    backend='postgres'
    def __init__(self,dsn,schema):
        transfer.validate_schema(schema)
        self._dsn=dsn;self.schema=schema;self.lock=threading.RLock();self.owner=None
        with self.transaction() as db:
            metadata=db.execute('SELECT * FROM storage_metadata WHERE id=1').fetchone()
            if not metadata or metadata['format']!=transfer.FORMAT or metadata['sqlite_schema']!=SCHEMA_VERSION:
                raise transfer.TransferError('지원하지 않는 PostgreSQL 저장 형식입니다.')
            validate_state(db.execute('SELECT * FROM audit_state WHERE id=1').fetchone())
        # Constructor performs no recovery, session revocation or schema writes.

    @contextmanager
    def transaction(self, *, write=False):
        with transfer.connect(self._dsn) as db, db.transaction():
            db.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED' if write else
                       'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            transfer.set_schema(db,self.schema)
            if self.owner is not None:self.owner.protect(db,self._dsn,self.schema)
            elif write:
                from .postgres_maintenance import offline_write
                offline_write(db,self.schema)
            if write:
                # One cooperative write order per database/schema, including other processes.
                db.execute("SELECT pg_advisory_xact_lock(hashtextextended(current_database()||':'||%s,0))",(self.schema,))
            yield db

    def acquire_runtime(self):
        from .postgres_maintenance import PostgresLease
        from .maintenance import WorkspaceBusy
        with self.lock:
            if self.owner is not None:raise WorkspaceBusy('이 저장소의 실행 소유권은 이미 사용되었거나 종료되었습니다.')
            self.owner=PostgresLease(self._dsn,self.schema)
            return self.owner

    @contextmanager
    def execution_permit(self):
        from .maintenance import WorkspaceBusy
        if self.owner is None:raise WorkspaceBusy('PostgreSQL 요청에는 실행 소유권이 필요합니다.')
        with self.transaction():yield

    def put(self,kind,record):
        self.put_many([(kind,record)]);return record

    def write_transaction(self):
        return self.transaction(write=True)

    def read_transaction(self):
        return self.transaction()

    def put_many(self,records,*,connection=None):
        with (nullcontext(connection) if connection is not None else self.write_transaction()) as db, db.cursor() as cursor:
            cursor.executemany('INSERT INTO records(kind,id,data) VALUES (%s,%s,%s) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data',
                               [(kind,record['id'],encoded(record)) for kind,record in records])

    def get(self,kind,id,*,compact_findings=False,connection=None):
        with (nullcontext(connection) if connection is not None else self.transaction()) as db:
            projection=COMPACT if kind=='findings' and compact_findings else 'data'
            row=db.execute('SELECT '+projection+' AS data FROM records WHERE kind=%s AND id=%s',(kind,id)).fetchone()
            if not row:return None
            return row['data'] if isinstance(row['data'],dict) else json.loads(row['data'])

    def patch(self,kind,id,**changes):
        with self.transaction(write=True) as db:
            record=self.get(kind,id,connection=db)
            if record is None:raise KeyError(id)
            record.update(changes)
            db.execute('UPDATE records SET data=%s WHERE kind=%s AND id=%s',(encoded(record),kind,id))
            return record

    def all(self,kind):
        with self.transaction() as db:
            return [json.loads(row['data']) for row in db.execute('SELECT data FROM records WHERE kind=%s ORDER BY rowid DESC',(kind,))]

    def count(self,kind,*,statuses=None,active_assets=False):
        clauses=['kind=%s'];args=[kind]
        if statuses:clauses.append(text('status')+'=ANY(%s)');args.append(list(statuses))
        if active_assets:clauses.append('coalesce(('+text('archived_at')+")::numeric,0)=0")
        with self.transaction() as db:return db.execute('SELECT count(*) AS count FROM records WHERE '+' AND '.join(clauses),args).fetchone()['count']

    def asset_url_exists(self,url,exclude_id=None):
        with self.transaction() as db:
            return db.execute("SELECT 1 FROM records WHERE kind='assets' AND "+text('url')+'=%s AND (%s::text IS NULL OR id!=%s) LIMIT 1',(url,exclude_id,exclude_id)).fetchone() is not None

    def asset_has_tasks(self,asset_id,*,active_only=False):
        active=' AND '+text('status')+" IN ('queued','running','stopping')" if active_only else ''
        with self.transaction() as db:
            return db.execute("SELECT 1 FROM records WHERE kind='tasks'"+active+' AND '+array('asset_ids')+' ? %s LIMIT 1',(asset_id,)).fetchone() is not None

    def enabled_schedule_ids(self,asset_id):
        with self.transaction() as db, db.cursor(name='enabled_schedules') as cursor:
            cursor.execute("SELECT id FROM records WHERE kind='schedules' AND "+text('enabled')+"='true' AND "+array('task.asset_ids')+' ? %s',(asset_id,))
            for row in cursor:yield row['id']

    def due_schedules(self,timestamp,limit=100):
        if not 1<=limit<=100:raise ValueError('Invalid schedule batch size')
        with self.transaction() as db:
            rows=db.execute("SELECT data FROM records WHERE kind='schedules' AND "+text('enabled')+"='true' AND ("+text('next_at')+')::numeric<=%s ORDER BY ('+text('next_at')+')::numeric,rowid LIMIT %s',(timestamp,limit)).fetchall()
            return [json.loads(row['data']) for row in rows]

    def recovery_tasks(self):
        with self.transaction() as db:upper=db.execute('SELECT coalesce(max(rowid),0) AS upper FROM records').fetchone()['upper']
        before=None
        while True:
            with self.transaction() as db:
                rows=db.execute("SELECT rowid,data FROM records WHERE kind='tasks' AND rowid<=%s AND (%s::bigint IS NULL OR rowid<%s) AND "+text('status')+" IN ('queued','running','stopping') ORDER BY rowid DESC LIMIT 100",(upper,before,before)).fetchall()
            if not rows:return
            before=rows[-1]['rowid']
            for row in rows:yield json.loads(row['data'])

    def page(self,kind,*,limit=25,offset=0,snapshot=None,search='',filters=None,archived=None,compact_findings=False,priority=False,connection=None):
        if kind not in FIELDS or not 1<=limit<=1000 or offset<0 or (snapshot is not None and snapshot<0):raise ValueError('Invalid record query')
        if priority and kind!='findings':raise ValueError('Priority order is only valid for findings')
        filters=filters or {}
        if not filters.keys()<={'status','severity','asset_id','task_id','check','finding_id','enabled','source','state'}:raise ValueError('Unknown record filter')
        if ('source' in filters or 'state' in filters) and kind!='llm_calls':raise ValueError('Call filters require provider attempts')
        if 'enabled' in filters and kind!='schedules':raise ValueError('Enabled filter is only valid for schedules')
        if archived is not None and kind!='assets':raise ValueError('Archive filter is only valid for assets')
        with (nullcontext(connection) if connection is not None else self.transaction()) as db:
            if snapshot is None:snapshot=db.execute('SELECT coalesce(max(rowid),0) AS snapshot FROM records WHERE kind=%s',(kind,)).fetchone()['snapshot']
            clauses=['kind=%s','rowid<=%s'];args=[kind,snapshot]
            if search:
                expression=" || ' ' || ".join('coalesce('+text(field)+",'')" for field in FIELDS[kind])
                if kind=='observations':
                    for source,reference in (('assets','asset_id'),('tasks','task_id')):
                        expression+=" || ' ' || coalesce((SELECT "+text('name','source')+f" FROM records source WHERE source.kind='{source}' AND source.id="+text(reference,'records')+"),'')"
                # C collation retains SQLite's ASCII lower semantics; %, _ remain literal.
                clauses.append('strpos(lower(('+expression+') COLLATE "C"),lower(%s COLLATE "C"))>0');args.append(search)
            for key,value in filters.items():
                if key=='finding_id' and kind=='evidence':
                    clauses.append("EXISTS (SELECT 1 FROM records f WHERE f.kind='findings' AND f.id=%s AND "+array('evidence_ids','f')+" ? records.id AND "+text('asset_id','records')+'='+text('asset_id','f')+' AND '+text('check','records')+'='+text('check','f')+' AND '+text('fingerprint','records')+'='+text('fingerprint','f')+' AND '+array('task_ids','f')+' ? ('+text('task_id','records')+'))')
                elif key=='task_id' and kind=='findings':clauses.append(array('task_ids')+' ? %s')
                elif key=='asset_id' and kind in ('tasks','schedules'):clauses.append(array('asset_ids' if kind=='tasks' else 'task.asset_ids')+' ? %s')
                elif key=='enabled':
                    clauses.append(text(key)+'=%s')
                    value=('true' if value else 'false') if type(value) in (bool,int) and value in (0,1) else value
                else:clauses.append(text(key)+'=%s');value=None if value is None else str(value)
                args.append(value)
            if archived is not None:clauses.append('coalesce(('+text('archived_at')+')::numeric,0)'+('!=0' if archived else '=0'))
            where=' AND '.join(clauses)
            total=db.execute('SELECT count(*) AS count FROM records WHERE '+where,args).fetchone()['count']
            projection=COMPACT if kind=='findings' and compact_findings else 'data'
            order="CASE "+text('severity')+" WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 WHEN 'info' THEN 4 ELSE 5 END,rowid DESC" if priority else 'rowid DESC'
            rows=db.execute('SELECT '+projection+' AS data FROM records WHERE '+where+' ORDER BY '+order+' LIMIT %s OFFSET %s',(*args,limit,offset)).fetchall()
            items=[row['data'] if isinstance(row['data'],dict) else json.loads(row['data']) for row in rows]
            if kind=='observations':
                for source,reference,name in (('assets','asset_id','asset_name'),('tasks','task_id','task_name')):
                    ids=list({item[reference] for item in items if item.get(reference)})
                    names={row['id']:row['name'] for row in db.execute('SELECT id,'+text('name')+' AS name FROM records WHERE kind=%s AND id=ANY(%s)',(source,ids))} if ids else {}
                    for item in items:item[name]=names.get(item.get(reference))
            if kind=='assets' and items:
                ids=[item['id'] for item in items]
                counts={row['asset_id']:row['count'] for row in db.execute('SELECT '+text('asset_id')+' AS asset_id,count(DISTINCT '+text('check')+") AS count FROM records WHERE kind='coverage' AND "+text('asset_id')+'=ANY(%s) AND '+text('status')+"='completed' GROUP BY "+text('asset_id'),(ids,))}
                from .postgres_coverage import latest_summary
                latest=latest_summary(db,ids)['assets']
                for item in items:item.update(completed_check_count=counts.get(item['id'],0),coverage_summary=latest.get(item['id']))
        return {'items':items,'total':total,'limit':limit,'offset':offset,'snapshot':snapshot,'has_more':offset+len(rows)<total}

    def event(self,task_id,message,level='info',detail=None):
        with self.transaction(write=True) as db:append_event(db,(now(),task_id,level,message,json.dumps(detail or {},ensure_ascii=False,allow_nan=False)))

    def audit_integrity(self,checkpoint=None):
        with self.transaction() as db:return transfer.postgres_audit(db,checkpoint)

    def events(self,after=0,task_id=None,limit=200):
        where='seq>%s';args=[after]
        if task_id:where+=' AND task_id=%s';args.append(task_id)
        with self.transaction() as db:
            return [{**row,'detail':json.loads(row['detail'])} for row in db.execute('SELECT * FROM events WHERE '+where+' ORDER BY seq LIMIT %s',(*args,limit))]

    def recent_events(self,limit=100):
        with self.transaction() as db:
            rows=db.execute('SELECT * FROM events ORDER BY seq DESC LIMIT %s',(limit,)).fetchall()
            return [{**row,'detail':json.loads(row['detail'])} for row in reversed(rows)]

    def event_page(self,task_id,*,limit=25,offset=0,snapshot=None,search=''):
        if not 1<=limit<=100 or offset<0 or (snapshot is not None and snapshot<0):raise ValueError('Invalid event query')
        with self.transaction() as db:
            if snapshot is None:snapshot=db.execute('SELECT coalesce(max(seq),0) AS snapshot FROM events WHERE task_id=%s',(task_id,)).fetchone()['snapshot']
            where='task_id=%s AND seq<=%s';args=[task_id,snapshot]
            if search:where+=' AND strpos(lower((message||\' \'||level) COLLATE "C"),lower(%s COLLATE "C"))>0';args.append(search)
            total=db.execute('SELECT count(*) AS count FROM events WHERE '+where,args).fetchone()['count']
            items=[{**row,'detail':json.loads(row['detail'])} for row in db.execute('SELECT * FROM events WHERE '+where+' ORDER BY seq DESC LIMIT %s OFFSET %s',(*args,limit,offset))]
            return {'items':items,'total':total,'limit':limit,'offset':offset,'snapshot':snapshot,'has_more':offset+len(items)<total}

    def session(self,token,expires,user_id):
        with self.transaction(write=True) as db:
            db.execute('DELETE FROM sessions WHERE expires<%s',(now(),))
            db.execute('INSERT INTO sessions VALUES (%s,%s,%s)',(hashlib.sha256(token.encode()).hexdigest(),expires,user_id))

    def session_user(self,token):
        with self.transaction() as db:return db.execute('SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.digest=%s AND s.expires>%s AND u.disabled=0',(hashlib.sha256(token.encode()).hexdigest(),now())).fetchone()

    def valid_session(self,token):return self.session_user(token) is not None

    def logout(self,token):
        with self.transaction(write=True) as db:db.execute('DELETE FROM sessions WHERE digest=%s',(hashlib.sha256(token.encode()).hexdigest(),))

    def user(self,*,id=None,username=None,connection=None):
        with (nullcontext(connection) if connection is not None else self.transaction()) as db:return db.execute('SELECT * FROM users WHERE '+('id=%s' if id is not None else 'username=%s'),(id if id is not None else username,)).fetchone()

    def finding_by_fingerprint(self,fingerprint,*,connection=None):
        with (nullcontext(connection) if connection is not None else self.transaction()) as db:
            row=db.execute("SELECT data FROM records WHERE kind='findings' AND "+text('fingerprint')+'=%s ORDER BY rowid LIMIT 1',(fingerprint,)).fetchone()
            return json.loads(row['data']) if row else None

    def task_metrics(self):
        with self.transaction() as db:
            counts={row['status']:row['count'] for row in db.execute('SELECT '+text('status')+" AS status,count(*) AS count FROM records WHERE kind='tasks' GROUP BY "+text('status'))}
            oldest=db.execute('SELECT min(('+text('approved_at')+")::double precision) AS oldest FROM records WHERE kind='tasks' AND "+text('status')+"='queued'").fetchone()['oldest']
            timeouts=db.execute("SELECT count(*) AS count FROM records WHERE kind='tasks' AND "+text('termination_reason')+" IN ('timeout','queue_timeout')").fetchone()['count']
            return {'tasks':counts,'oldest_queued_at':oldest,'timeouts':timeouts}

    def overdue_task_ids(self,before,limit=100):
        if not 1<=limit<=100:raise ValueError('Invalid queue batch size')
        with self.transaction() as db:
            return [row['id'] for row in db.execute("SELECT id FROM records WHERE kind='tasks' AND "+text('status')+"='queued' AND ("+text('approved_at')+')::double precision<%s ORDER BY ('+text('approved_at')+')::double precision,rowid LIMIT %s',(before,limit))]

    def users(self):
        with self.transaction() as db:return db.execute('SELECT * FROM users ORDER BY created_at,id COLLATE "C"').fetchall()

    def add_user(self,user):
        with self.transaction(write=True) as db:db.execute('INSERT INTO users VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',tuple(user[key] for key in ('id','username','name','role','salt','password_hash','disabled','created_at','updated_at')))
        return user

    def update_user(self,id,**changes):
        if not changes.keys()<={'name','role','disabled','salt','password_hash'}:raise ValueError('Unknown user field')
        if type(changes.get('disabled')) is bool:changes['disabled']=int(changes['disabled'])
        changes['updated_at']=now()
        with self.transaction(write=True) as db:
            before=db.execute('SELECT * FROM users WHERE id=%s',(id,)).fetchone()
            changed=before and any(key in changes and changes[key]!=before[key] for key in ('role','disabled','password_hash'))
            row=db.execute('UPDATE users SET '+','.join(key+'=%s' for key in changes)+' WHERE id=%s RETURNING *',(*changes.values(),id)).fetchone()
            if changed:db.execute('DELETE FROM sessions WHERE user_id=%s',(id,))
            return row

    def _commit_call(self,db,detail,task_id,source,record_kind,record_id):
        from .call_ledger import commit
        commit(db,detail,task_id,source,record_kind,record_id,postgres=True)

    def put_message_exchange(self,question,reply):
        with self.transaction(write=True) as db:
            original=self.get('messages',question['id'],connection=db)
            if original:
                if original['content']!=question['content'] or original.get('mode','rules')!=question.get('mode','rules'):raise MessageRequestConflict('message request content conflict')
                stored=self.get('messages',reply['id'],connection=db)
                if not stored:raise RuntimeError('message exchange is incomplete')
                return stored
            with db.cursor() as cursor:cursor.executemany("INSERT INTO records(kind,id,data) VALUES ('messages',%s,%s)",[(record['id'],encoded(record)) for record in (question,reply)])
            if reply.get('assistant_generation'):
                self._commit_call(db,reply['assistant_generation'],reply['task_id'],'conversation','messages',reply['id'])
                append_event(db,(now(),reply['task_id'],'info','AI 대화 호출 결과',json.dumps(reply['assistant_generation'],ensure_ascii=False,allow_nan=False)))
        return reply

    def record_planner_call(self,task_id,detail,message,level):
        with self.transaction(write=True) as db:
            task=self.get('tasks',task_id,connection=db)
            if task is None:raise KeyError(task_id)
            self._commit_call(db,detail,task_id,'planner','tasks',task_id)
            task['llm_usage']=detail
            db.execute("UPDATE records SET data=%s WHERE kind='tasks' AND id=%s",(encoded(task),task_id))
            append_event(db,(now(),task_id,level,message,json.dumps(detail,ensure_ascii=False,allow_nan=False)))
