"""Complete report streams from one read-only storage snapshot.

Memory grows with the largest record plus a bounded delivery buffer, not the
number of exported records.
Slow downloads retain their read snapshot (and can delay WAL checkpointing).
"""
import csv
import io
import json
import sqlite3
import time
from contextlib import closing, nullcontext
from urllib.parse import quote

import anyio
from starlette.responses import StreamingResponse
from starlette.requests import ClientDisconnect
from .export_limits import ExportDeadline
from . import __version__
from .coverage import iter_task_rows
from .store_util import now


class Snapshot:
    def __init__(self, db, task_id):
        self.db, self.task_id = db, task_id

    def records(self, kind):
        where, args = 'r.kind=?', [kind]
        if kind == 'tasks' and self.task_id:
            where += ' AND r.id=?'
            args.append(self.task_id)
        elif kind == 'findings' and self.task_id:
            where += " AND EXISTS (SELECT 1 FROM json_each(r.data,'$.task_ids') WHERE value=?)"
            args.append(self.task_id)
        elif kind in ('evidence', 'traffic'):
            where += " AND EXISTS (SELECT 1 FROM records t WHERE t.kind='tasks' AND t.id=json_extract(r.data,'$.task_id')"
            if self.task_id:
                where += ' AND t.id=?'
                args.append(self.task_id)
            where += ')'
        elif kind == 'finding_history':
            where += " AND EXISTS (SELECT 1 FROM records f WHERE f.kind='findings' AND f.id=json_extract(r.data,'$.finding_id')"
            if self.task_id:
                where += " AND EXISTS (SELECT 1 FROM json_each(f.data,'$.task_ids') WHERE value=?)"
                args.append(self.task_id)
            where += ')'
        # Traverse rowids directly: the (kind,id) index would require sorting all
        # matching payloads before yielding, moving the memory cost into SQLite.
        for row in self.db.execute('SELECT r.data FROM records r NOT INDEXED WHERE '+where+' ORDER BY r.rowid DESC',args):
            yield json.loads(row[0])

    def get(self, kind, id):
        row = self.db.execute('SELECT data FROM records WHERE kind=? AND id=?',(kind,id)).fetchone()
        return json.loads(row[0]) if row else None

    def coverage(self):
        for task in self.records('tasks'):
            yield from iter_task_rows(None,task,get_record=self.get)


def json_report(snapshot, generated_at):
    yield '{"version":'+json.dumps(__version__)+',"generated_at":'+json.dumps(generated_at)
    for kind in ('tasks','findings','evidence','finding_history','coverage','traffic'):
        yield ',\n'+json.dumps(kind)+':['
        first = True
        rows = snapshot.coverage() if kind == 'coverage' else snapshot.records(kind)
        for record in rows:
            yield ('' if first else ',\n')+json.dumps(record,ensure_ascii=False)
            first = False
        yield ']'
    yield '}\n'


def csv_report(snapshot):
    def row(values):
        buf = io.StringIO()
        csv.writer(buf).writerow(values)
        return buf.getvalue()
    def cell(value):
        value = str(value)
        return "'"+value if value.lstrip().startswith(('=','+','-','@')) else value
    yield '\ufeff'+row(['severity','status','title','asset','check','confidence','remediation'])
    for finding in snapshot.records('findings'):
        yield row([cell(finding[k]) for k in ('severity','status','title','asset_name','check','confidence','remediation')])


def markdown_report(snapshot, generated_at):
    yield '\n'.join(['# Open Aegis 검증 보고서','',
                     '생성 시각: '+time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime(generated_at)),'',
                     '설정 관찰·권한 규칙 불일치는 확인된 침입 또는 데이터 유출과 구분됩니다.',''])+'\n'
    for task in snapshot.records('tasks'):
        lines = ['## 작업: '+task['name'],'','상태: '+task['status'],'검증 도구: '+', '.join(task['checks']),
                 f"처리 자산: {task['done']}/{len(task['asset_ids'])} · 오류: {task['errors']}",'']
        for key, label in (('execution_policy','실행 정책'),('termination_reason','종료 사유'),('retry_of','재실행 원본 작업')):
            if task.get(key):
                value = json.dumps(task[key],ensure_ascii=False) if key == 'execution_policy' else task[key]
                lines += [label+': '+value,'']
        if task.get('llm_usage'):
            lines += ['AI 계획 호출 기록 (제공자 보고값·설정 가격의 비용 추정; 청구 확인 아님):',
                      '```json', json.dumps(task['llm_usage'],ensure_ascii=False,indent=2), '```', '']
        completed = total = 0
        for record in iter_task_rows(None,task,get_record=snapshot.get):
            total += 1
            completed += record['status']=='completed'
        lines += [f'검증 완료: {completed}/{total} (선택한 자산 × 도구)','']
        yield '\n'.join(lines)+'\n'
        for record in iter_task_rows(None,task,get_record=snapshot.get):
            yield f"- {record['asset_id']} / {record['check']}: {record['status']} · {record.get('reason','')}\n"
        yield '\n'
    for finding in snapshot.records('findings'):
        yield '\n'.join(['## ['+finding['severity'].upper()+'] '+finding['title'],'',
                         '자산: '+finding['asset_name'],'상태: '+finding['status'],
                         '담당자: '+(finding.get('assignee_name') or '미지정'),
                         '위험 수용 사유: '+finding.get('acceptance_reason',''),
                         '해결 사유: '+finding.get('resolution_reason',''),
                         '판정 유형: '+finding['confidence'],'','```json',
                         json.dumps(finding['evidence'],ensure_ascii=False,indent=2),'```','',finding['remediation'],''])+'\n'


def render_chunks(snapshot, format, permit=None):
    generator = {'json':json_report,'csv':csv_report,'markdown':markdown_report}[format]
    rows = generator(snapshot) if format == 'csv' else generator(snapshot,now())
    with closing(rows):
        for chunk in rows:
            if permit: permit.check()
            yield chunk.encode('utf-8')


def report_chunks(path, format, task_id=None, permit=None):
    if getattr(path,'backend',None)=='postgres':
        from .postgres_reporting import PostgresSnapshot
        if permit:permit.check()
        with path.transaction(permit=permit) as db:
            # Pin the snapshot before the first streamed byte, including an empty DB.
            db.execute('SELECT rowid FROM records LIMIT 1').fetchone()
            yield from render_chunks(PostgresSnapshot(db,task_id,permit),format,permit)
        return
    path=getattr(path,'path',path)
    # Threadpool iteration is serialized but may use a different worker each time.
    uri = 'file:'+quote(str(path.resolve()),safe='/')+'?mode=ro'
    if permit: permit.check()
    timeout = min(1,permit.remaining()) if permit else 5
    try:
        with closing(sqlite3.connect(uri,uri=True,check_same_thread=False,timeout=timeout)) as db:
            if permit: db.set_progress_handler(permit.interrupt_sql,1000)
            db.execute('BEGIN')
            db.execute('SELECT rowid FROM records LIMIT 1').fetchone()
            snapshot = Snapshot(db,task_id)
            yield from render_chunks(snapshot,format,permit)
    except sqlite3.OperationalError:
        if permit: permit.check()
        raise


def next_report_batch(iterator):
    # Keep the DB iterator on serialized worker calls, but avoid a thread/ASGI
    # transition for every small JSON delimiter or record. An oversized record
    # stays intact; memory is bounded by 64 KiB plus the largest record.
    chunks=[];size=0
    for _ in range(128):
        chunk=next(iterator,None)
        if chunk is None:break
        chunks.append(chunk);size+=len(chunk)
        if size>=64*1024:break
    return b''.join(chunks) if chunks else None


async def report_stream(path, format, task_id=None, permit=None):
    iterator = report_chunks(path,format,task_id,permit)
    try:
        while (chunk := await anyio.to_thread.run_sync(next_report_batch,iterator)) is not None:
            yield chunk
    finally:
        # Close the cursor/snapshot even if a client disconnects or streaming fails.
        with anyio.CancelScope(shield=True):
            await anyio.to_thread.run_sync(iterator.close)


class ReportResponse(StreamingResponse):
    """Bound the entire send and release the read snapshot and admission slot."""
    def __init__(self, *args, permit=None, **kwargs):
        self.permit=permit
        super().__init__(*args,**kwargs)

    async def listen_for_disconnect(self, receive):
        await super().listen_for_disconnect(receive)
        if self.permit:self.permit.cancelled.set()

    async def __call__(self, scope, receive, send):
        completed=False
        outcome='failed'
        async def tracked_send(message):
            nonlocal completed
            await send(message)
            if message['type']=='http.response.body' and not message.get('more_body',False):
                completed=True
        try:
            with anyio.fail_after(self.permit.remaining()) if self.permit else nullcontext():
                await super().__call__(scope,receive,tracked_send)
            outcome='completed' if completed else 'cancelled'
        except (TimeoutError,ExportDeadline):
            outcome='timed_out'
            raise ExportDeadline('보고서 내보내기 시간 제한을 초과했습니다.') from None
        except BaseException as exc:
            if isinstance(exc,(ClientDisconnect,anyio.get_cancelled_exc_class(),InterruptedError)):
                outcome='cancelled'
            if not (isinstance(exc,InterruptedError) and self.permit and self.permit.cancelled.is_set()):
                raise
        finally:
            if self.permit:self.permit.cancelled.set()
            try:
                with anyio.CancelScope(shield=True):
                    await self.body_iterator.aclose()
            finally:
                if self.permit:self.permit.finish(outcome)
