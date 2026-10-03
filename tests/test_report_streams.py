import asyncio
import csv
import io
import json
import sqlite3
import tracemalloc

import pytest
from aegis import reporting
from aegis.store import Store
from tests.test_validation import client
from tests.test_identity import add, login


def seed(store, count=1005):
    task={'id':'report-task','name':'Export test','status':'completed','asset_ids':['a'],'done':1,'errors':0,
          'scope_snapshot':[{'id':'a','revision':1}],'checks':['security_headers'],'created_at':1}
    store.put('tasks',task)
    store.put('coverage',{'id':'report-task:a:security_headers','task_id':'report-task','asset_id':'a',
                          'check':'security_headers','status':'completed'})
    rows=[]
    for i in range(count):
        rows.extend([
            ('findings',{'id':str(i),'task_ids':['report-task'],'title':f'Finding {i}','severity':'low',
                         'status':'open','asset_name':'asset','check':'security_headers','confidence':'configuration',
                         'remediation':'fix','evidence':{'header':'missing'},'evidence_ids':[f'e-{i}']}),
            ('evidence',{'id':f'e-{i}','task_id':'report-task','proof':'x'*2048}),
            ('traffic',{'id':f't-{i}','task_id':'report-task','url':'https://example.invalid/'}),
            ('finding_history',{'id':f'h-{i}','finding_id':str(i),'reason':'original'})])
    store.put_many(rows)
    store.put('tasks',{**task,'id':'other','name':'Foreign','scope_snapshot':[]})
    store.put_many([('findings',{'id':'foreign','task_ids':['other']}),
                    ('evidence',{'id':'foreign','task_id':'other'}),('traffic',{'id':'foreign','task_id':'other'}),
                    ('finding_history',{'id':'foreign','finding_id':'foreign'}),
                    ('traffic',{'id':'orphan','task_id':'missing'}),('evidence',{'id':'orphan','task_id':'missing'})])


def test_complete_scoped_exports_no_full_reads_csv_and_auth(client,monkeypatch):
    store=client.app.state.store
    seed(store)
    original_get=store.get
    monkeypatch.setattr(store,'all',lambda *_:pytest.fail('Unbounded export read'))
    monkeypatch.setattr(store,'get',lambda kind,id,**kw: original_get(kind,id,**kw) if kind=='tasks' else pytest.fail('Coverage escaped report snapshot'))
    path='/api/reports/export'
    response=client.get(path,params={'format':'json','task_id':'report-task'})
    response.raise_for_status()
    data=response.json()
    assert response.headers['Cache-Control']=='no-store' and 'content-length' not in response.headers
    assert data['tasks'][0]['id']=='report-task' and len(data['tasks'])==1
    for kind in ('findings','evidence','traffic','finding_history'):
        assert len(data[kind])==1005 and all(row['id'] not in ('foreign','orphan') for row in data[kind])
    assert data['findings'][0]['task_ids']==['report-task']
    assert data['coverage'][0]['status']=='completed'
    markdown=client.get(path,params={'task_id':'report-task'}).text
    assert '검증 완료: 1/1' in markdown and 'Finding 0' in markdown and 'Finding 1004' in markdown
    store.put('findings',{**original_get('findings','0'),'title':' \t=HYPERLINK("x")','remediation':'@SUM(1,2)'})
    text=client.get(path,params={'format':'csv','task_id':'report-task'}).text
    rows=list(csv.reader(io.StringIO(text.lstrip('\ufeff'))))
    assert len(rows)==1006 and rows[-1][2].startswith("'") and rows[-1][-1]=="'@SUM(1,2)"
    assert client.get(path+'?task_id=missing').status_code==404
    assert client.get(path+'?format=xml').status_code==422
    viewer=add(client,'viewer')
    with login(client.app,viewer['username']) as read:
        assert read.get(path,params={'format':'csv','task_id':'report-task'}).status_code==200
    client.post('/api/auth/logout')
    assert client.get(path).status_code==401


def test_report_snapshot_includes_consistent_coverage_and_excludes_later_edits(tmp_path):
    store=Store(tmp_path/'report.db')
    seed(store,1)
    stream=reporting.report_chunks(store.path,'json','report-task')
    first=next(stream)
    store.patch('tasks','report-task',name='changed')
    store.patch('findings','0',title='changed')
    store.patch('coverage','report-task:a:security_headers',status='failed')
    store.patch('finding_history','h-0',reason='changed')
    store.put('evidence',{'id':'new','task_id':'report-task'})
    data=json.loads(first+b''.join(stream))
    assert data['tasks'][0]['name']=='Export test'
    assert data['findings'][0]['title']=='Finding 0'
    assert data['coverage'][0]['status']=='completed'
    assert data['finding_history'][0]['reason']=='original'
    assert len(data['evidence'])==1


def track_connections(monkeypatch):
    opened=[]
    original=sqlite3.connect
    class Tracked(sqlite3.Connection):
        closed=False
        def close(self):
            self.closed=True
            super().close()
    def connect(*args,**kwargs):
        if kwargs.get('uri'):
            kwargs['factory']=Tracked
        db=original(*args,**kwargs)
        if kwargs.get('uri'): opened.append(db)
        return db
    monkeypatch.setattr(reporting.sqlite3,'connect',connect)
    return opened


@pytest.mark.parametrize('task_id,error',[(None,json.JSONDecodeError),('report-task',sqlite3.OperationalError)])
def test_stream_read_only_cleanup_on_close_and_data_error(tmp_path,monkeypatch,task_id,error):
    store=Store(tmp_path/'unicode space #?.db')
    seed(store,1)
    opened=track_connections(monkeypatch)
    stream=reporting.report_chunks(store.path,'json','report-task')
    next(stream)
    with pytest.raises(sqlite3.OperationalError,match='readonly'):
        opened[-1].execute('DELETE FROM records')
    stream.close()
    assert opened[-1].closed
    with store.connect() as db:
        db.execute("UPDATE records SET data='invalid json' WHERE kind='findings'")
    with pytest.raises(error):
        list(reporting.report_chunks(store.path,'json',task_id))
    assert opened[-1].closed


def test_async_stream_early_close_releases_snapshot(tmp_path,monkeypatch):
    store=Store(tmp_path/'report.db')
    seed(store,1)
    opened=track_connections(monkeypatch)
    async def consume():
        stream=reporting.report_stream(store.path,'json','report-task')
        assert await anext(stream)
        await stream.aclose()
    asyncio.run(consume())
    assert len(opened)==1 and opened[0].closed


def test_stream_python_memory_does_not_scale_with_export_size(tmp_path):
    store=Store(tmp_path/'report.db')
    seed(store,6000)
    target=tmp_path/'report.json'
    tracemalloc.start()
    with target.open('wb') as output:
        for chunk in reporting.report_chunks(store.path,'json','report-task'):
            output.write(chunk)
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert target.stat().st_size>12_000_000
    assert peak<2_000_000
    with target.open() as source:
        data=json.load(source)
    assert all(len(data[kind])==6000 for kind in ('findings','evidence','traffic','finding_history'))


@pytest.mark.parametrize('spec',['2.0','2.4'])
def test_asgi_disconnect_closes_report_connection(tmp_path,monkeypatch,spec):
    from starlette.requests import ClientDisconnect
    store=Store(tmp_path/'report.db')
    seed(store,1005)
    opened=track_connections(monkeypatch)
    async def disconnect():
        first_body=asyncio.Event()
        sent=[]
        async def send(message):
            sent.append(message)
            if message['type']=='http.response.body' and message.get('body'):
                first_body.set()
                if spec=='2.4': raise OSError('client disconnected')
        async def receive():
            await first_body.wait()
            return {'type':'http.disconnect'}
        response=reporting.ReportResponse(reporting.report_stream(store.path,'json','report-task'))
        if spec=='2.4':
            with pytest.raises(ClientDisconnect):
                await response({'type':'http','asgi':{'spec_version':spec}},receive,send)
        else:
            await response({'type':'http','asgi':{'spec_version':spec}},receive,send)
        assert any(m['type']=='http.response.body' for m in sent)
    asyncio.run(disconnect())
    assert len(opened)==1 and opened[0].closed


def test_report_sql_does_not_sort_or_buffer_matching_payloads(tmp_path):
    store=Store(tmp_path/'report.db')
    seed(store,2)
    queries=[]
    with store.connect() as db:
        db.set_trace_callback(queries.append)
        snapshot=reporting.Snapshot(db,'report-task')
        for kind in ('tasks','findings','evidence','finding_history','traffic'):
            list(snapshot.records(kind))
        selects=[sql for sql in queries if sql.startswith('SELECT r.data')]
        assert len(selects)==5
        for sql in selects:
            plan=[row[3] for row in db.execute('EXPLAIN QUERY PLAN '+sql)]
            assert not any('TEMP B-TREE' in step for step in plan),plan
            assert any('SCAN r' in step for step in plan),plan
