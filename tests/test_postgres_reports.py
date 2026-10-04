"""Actual native report snapshots, bounded client reads and cancellation."""
import asyncio
import csv
import io
import json
import threading
import time
import tracemalloc

import anyio
import pytest
from aegis import reporting,postgres_transfer as transfer
from aegis.export_limits import ExportPolicy,ExportPool,ExportDeadline
from aegis.maintenance import WorkspaceBusy
from aegis.postgres_maintenance import PostgresLease
from aegis.postgres_reporting import PostgresSnapshot
from aegis.postgres_store import PostgresStore
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_store import stores
from tests.test_report_streams import seed


def track(monkeypatch):
    opened=[];original=transfer.connect
    def connect(*args,**kwargs):
        db=original(*args,**kwargs);opened.append(db);return db
    monkeypatch.setattr(transfer,'connect',connect)
    return opened


def test_complete_native_report_formats_scope_orphans_and_literal_ids(stores,monkeypatch):
    sqlite,pg=stores
    for store in stores:seed(store,1005)
    monkeypatch.setattr(reporting,'now',lambda:42)
    monkeypatch.setattr(pg,'all',lambda *_:pytest.fail('Unbounded report materialization'))
    monkeypatch.setattr(pg,'get',lambda *_:pytest.fail('Coverage escaped report transaction'))
    for format in ('json','csv','markdown'):
        actual=b''.join(reporting.report_chunks(pg,format,'report-task'))
        assert actual==b''.join(reporting.report_chunks(sqlite,format,'report-task'))
        if format=='json':
            data=json.loads(actual)
            assert len(data['tasks'])==1 and data['coverage'][0]['status']=='completed'
            for kind in ('findings','evidence','finding_history','traffic'):
                assert len(data[kind])==1005 and all(row['id'] not in ('foreign','orphan') for row in data[kind])
    data=json.loads(b''.join(reporting.report_chunks(pg,'json')))
    assert len(data['tasks'])==2 and len(data['findings'])==1006
    assert all(row['id']!='orphan' for kind in ('evidence','traffic') for row in data[kind])
    assert data==json.loads(b''.join(reporting.report_chunks(sqlite,'json')))
    empty=json.loads(b''.join(reporting.report_chunks(pg,'json',"report-task' OR 1=1 --")))
    assert all(empty[kind]==[] for kind in ('tasks','findings','evidence','finding_history','coverage','traffic'))


def test_native_csv_formula_protection(stores):
    sqlite,pg=stores
    for store in stores:
        seed(store,1)
        store.patch('findings','0',title=' \t=HYPERLINK("x")',remediation='@SUM(1,2)')
    text=b''.join(reporting.report_chunks(pg,'csv','report-task')).decode()
    assert text==b''.join(reporting.report_chunks(sqlite,'csv','report-task')).decode()
    rows=list(csv.reader(io.StringIO(text.lstrip('\ufeff'))))
    assert len(rows)==2 and rows[1][2].startswith("'") and rows[1][-1]=="'@SUM(1,2)"


def test_native_same_snapshot_including_coverage_and_history(stores):
    _,pg=stores;seed(pg,1);owner=pg.acquire_runtime()
    try:
        stream=reporting.report_chunks(pg,'json','report-task');first=next(stream)
        pg.patch('tasks','report-task',name='changed')
        pg.patch('findings','0',title='changed')
        pg.patch('coverage','report-task:a:security_headers',status='failed')
        pg.patch('finding_history','h-0',reason='changed')
        pg.put('evidence',{'id':'new','task_id':'report-task'})
        data=json.loads(first+b''.join(stream))
        assert data['tasks'][0]['name']=='Export test' and data['findings'][0]['title']=='Finding 0'
        assert data['coverage'][0]['status']=='completed' and data['finding_history'][0]['reason']=='original'
        assert len(data['evidence'])==1
        later=json.loads(b''.join(reporting.report_chunks(pg,'json','report-task')))
        assert later['coverage'][0]['status']=='failed' and len(later['evidence'])==2
    finally:owner.close()


def test_native_read_only_early_close_and_invalid_json_cleanup(stores,monkeypatch):
    import psycopg
    _,pg=stores;seed(pg,1);opened=track(monkeypatch)
    stream=reporting.report_chunks(pg,'json','report-task');next(stream)
    db=opened[-1]
    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):db.execute('DELETE FROM records')
    stream.close();assert db.closed
    async def consume():
        stream=reporting.report_stream(pg,'json','report-task')
        assert await anext(stream)
        await stream.aclose()
    asyncio.run(consume());assert opened[-1].closed
    with pg.transaction(write=True) as db:
        db.execute("UPDATE records SET data='invalid json' WHERE kind='findings'")
    with pytest.raises(psycopg.errors.InvalidTextRepresentation):
        list(reporting.report_chunks(pg,'json','report-task'))
    assert opened[-1].closed


def test_native_stream_client_memory_and_server_side_cursors(stores,tmp_path,monkeypatch):
    import psycopg
    _,pg=stores;seed(pg,6000)
    cursors=[];original=psycopg.Connection.cursor
    def cursor(self,*args,**kwargs):
        result=original(self,*args,**kwargs)
        if kwargs.get('name','').startswith('aegis_report_'):cursors.append(result)
        return result
    monkeypatch.setattr(psycopg.Connection,'cursor',cursor)
    output=tmp_path/'report.json'
    tracemalloc.start()
    try:
        with output.open('wb') as destination:
            for chunk in reporting.report_chunks(pg,'json','report-task'):destination.write(chunk)
        _,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop()
    assert output.stat().st_size>12_000_000 and peak<2_000_000
    assert len(cursors)==6 and all(row.itersize==32 and row.closed for row in cursors)
    with output.open() as source:data=json.load(source)
    assert all(len(data[kind])==6000 for kind in ('findings','evidence','finding_history','traffic'))


@pytest.mark.parametrize('disconnect',[False,True])
def test_native_active_sql_deadline_and_disconnect_cleanup(stores,monkeypatch,disconnect):
    _,pg=stores;seed(pg,1);opened=track(monkeypatch)
    pool=ExportPool(ExportPolicy(timeout=10 if disconnect else .2));permit=pool.acquire()
    entered=threading.Event();original=PostgresSnapshot.records
    def slow(self,kind):
        if kind=='tasks':
            entered.set();self.db.execute('SELECT pg_sleep(10)').fetchone()
        yield from original(self,kind)
    monkeypatch.setattr(PostgresSnapshot,'records',slow)
    async def run():
        async def send(message):pass
        async def receive():
            if not disconnect:await anyio.sleep(10)
            while not entered.is_set():await anyio.sleep(.001)
            return {'type':'http.disconnect'}
        response=reporting.ReportResponse(reporting.report_stream(pg,'json','report-task',permit),permit=permit)
        if disconnect:await response({'type':'http','asgi':{'spec_version':'2.0'}},receive,send)
        else:
            with pytest.raises(ExportDeadline):
                await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
    started=time.monotonic();asyncio.run(run())
    assert entered.is_set() and time.monotonic()-started<2
    assert len(opened)==1 and opened[0].closed
    assert not any(thread.name=='aegis-report-cancel' and thread.is_alive() for thread in threading.enumerate())
    assert pool.metrics()['active']==0 and pool.metrics()['cancelled' if disconnect else 'timed_out']==1


def test_native_slow_send_deadline_releases_snapshot(stores,monkeypatch):
    _,pg=stores;seed(pg,1);opened=track(monkeypatch)
    pool=ExportPool(ExportPolicy(timeout=.1));permit=pool.acquire()
    async def run():
        async def send(message):
            if message['type']=='http.response.body':await anyio.sleep(10)
        async def receive():await anyio.sleep(10)
        response=reporting.ReportResponse(reporting.report_stream(pg,'json','report-task',permit),permit=permit)
        with pytest.raises(ExportDeadline):
            await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
    asyncio.run(run())
    assert len(opened)==1 and opened[0].closed and pool.metrics()['active']==0
    assert pool.metrics()['timed_out']==1


def test_native_report_fences_replacement_and_rejects_lost_owner(stores,postgres):
    _,pg=stores;seed(pg,1);owner=pg.acquire_runtime();replacement=None
    stream=reporting.report_chunks(pg,'json','report-task')
    try:
        assert next(stream)
        with transfer.connect(postgres['dsn']) as db:
            assert db.execute('SELECT pg_terminate_backend(%s) AS killed',(owner.pid,)).fetchone()['killed']
        with pytest.raises(WorkspaceBusy):PostgresLease(postgres['dsn'],pg.schema)
        stream.close()
        replacement=PostgresLease(postgres['dsn'],pg.schema)
        with pytest.raises(WorkspaceBusy):next(reporting.report_chunks(pg,'json','report-task'))
        replacement.close();replacement=None
        fresh=PostgresStore(postgres['dsn'],pg.schema)
        assert json.loads(b''.join(reporting.report_chunks(fresh,'json','report-task')))['tasks'][0]['id']=='report-task'
    finally:
        stream.close()
        if replacement:replacement.close()
        owner.close()
