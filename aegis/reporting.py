"""Complete report streams from one read-only SQLite snapshot.

Memory grows with the largest record, not the number of exported records.
Slow downloads retain their read snapshot (and can delay WAL checkpointing).
"""
import csv
import io
import json
import sqlite3
import time
from contextlib import closing
from urllib.parse import quote

import anyio
from starlette.responses import StreamingResponse
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


def report_chunks(path, format, task_id=None):
    # Threadpool iteration is serialized but may use a different worker each time.
    uri = 'file:'+quote(str(path.resolve()),safe='/')+'?mode=ro'
    with closing(sqlite3.connect(uri,uri=True,check_same_thread=False)) as db:
        db.execute('BEGIN')
        db.execute('SELECT rowid FROM records LIMIT 1').fetchone()  # establish one snapshot before yielding
        snapshot = Snapshot(db,task_id)
        generator = {'json':json_report,'csv':csv_report,'markdown':markdown_report}[format]
        rows = generator(snapshot) if format == 'csv' else generator(snapshot,now())
        for chunk in rows:
            yield chunk.encode('utf-8')


def next_chunk(iterator):
    return next(iterator,None)


async def report_stream(path, format, task_id=None):
    iterator = report_chunks(path,format,task_id)
    try:
        while (chunk := await anyio.to_thread.run_sync(next_chunk,iterator)) is not None:
            yield chunk
    finally:
        # Close the cursor/snapshot even if a client disconnects or streaming fails.
        with anyio.CancelScope(shield=True):
            await anyio.to_thread.run_sync(iterator.close)


class ReportResponse(StreamingResponse):
    """Also close a paused iterator when ASGI 2.4 send raises on disconnect."""
    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            with anyio.CancelScope(shield=True):
                await self.body_iterator.aclose()
