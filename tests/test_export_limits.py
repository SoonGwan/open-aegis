import asyncio
import threading
import time

import anyio
import pytest
from aegis.export_limits import ExportPolicy,ExportPool,ExportDeadline
from aegis import reporting
from tests.test_validation import client
from tests.test_report_streams import seed,track_connections
from aegis.store import Store


@pytest.mark.parametrize('name,values',[('AEGIS_EXPORT_PARALLEL',('0','5','1.5','nan')),
                                      ('AEGIS_EXPORT_TIMEOUT',('0','601','nan','inf','invalid'))])
def test_export_policy_environment_rejects_invalid_values(monkeypatch,name,values):
    for value in values:
        monkeypatch.setenv(name,value)
        with pytest.raises(ValueError,match=name):ExportPolicy.from_env()
    monkeypatch.delenv(name)
    assert ExportPolicy.from_env()==ExportPolicy()
    monkeypatch.setenv('AEGIS_EXPORT_PARALLEL','4')
    monkeypatch.setenv('AEGIS_EXPORT_TIMEOUT','600')
    assert ExportPolicy.from_env()==ExportPolicy(4,600)


def test_admission_is_atomic_and_permits_release_once():
    pool=ExportPool(ExportPolicy(parallel=2))
    barrier=threading.Barrier(9);release=threading.Event();accepted=[]
    def acquire():
        permit=pool.acquire()
        if permit:accepted.append(permit)
        barrier.wait(timeout=2)
        release.wait(timeout=2)
        if permit:
            permit.finish('completed');permit.finish('failed')
    threads=[threading.Thread(target=acquire) for _ in range(8)]
    for thread in threads:thread.start()
    barrier.wait(timeout=2)
    try:
        assert len(accepted)==2 and pool.metrics()['active']==2
        assert pool.metrics()['rejected']==6
    finally:
        release.set()
        for thread in threads:thread.join(timeout=2)
    assert pool.metrics()['active']==0 and pool.metrics()['completed']==2 and pool.metrics()['failed']==0


def test_capacity_rejection_is_before_stream_creation_and_runtime_is_visible(client,monkeypatch):
    pool=client.app.state.exports
    permits=[pool.acquire() for _ in range(pool.policy.parallel)]
    def unexpected(*args,**kwargs):pytest.fail('Over-capacity request opened a stream')
    with monkeypatch.context() as patch:
        patch.setattr('aegis.app.report_stream',unexpected)
        for format in ('csv','json','markdown'):
            response=client.get('/api/reports/export',params={'format':format})
            assert response.status_code==429 and response.headers['retry-after']=='5'
        assert client.get('/api/reports/export?task_id=missing').status_code==404
        metrics=client.get('/api/runtime').json()['exports']
        assert metrics['active']==pool.policy.parallel and metrics['rejected']==3
    for permit in permits:permit.finish('cancelled')
    response=client.get('/api/reports/export?format=json')
    assert response.status_code==200
    assert pool.metrics()['active']==0 and pool.metrics()['completed']==1


def test_slow_send_timeout_closes_snapshot_and_releases_capacity(tmp_path,monkeypatch):
    store=Store(tmp_path/'report.db');seed(store,2)
    opened=track_connections(monkeypatch)
    pool=ExportPool(ExportPolicy(timeout=.05));permit=pool.acquire()
    async def run():
        async def send(message):
            if message['type']=='http.response.body':await anyio.sleep(10)
        async def receive():await anyio.sleep(10)
        response=reporting.ReportResponse(reporting.report_stream(store.path,'json','report-task',permit),permit=permit)
        with pytest.raises(ExportDeadline):
            await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
    started=time.monotonic();asyncio.run(run())
    assert time.monotonic()-started<1
    assert len(opened)==1 and opened[0].closed
    assert pool.metrics()['active']==0 and pool.metrics()['timed_out']==1
    next_permit=pool.acquire();assert next_permit is not None;next_permit.finish('cancelled')


def test_expensive_sql_is_interrupted_by_monotonic_deadline(tmp_path,monkeypatch):
    store=Store(tmp_path/'report.db');seed(store,2)
    opened=track_connections(monkeypatch)
    pool=ExportPool(ExportPolicy(timeout=.05));permit=pool.acquire()
    original=reporting.Snapshot.records
    def expensive(self,kind):
        if kind=='tasks':
            self.db.execute('WITH RECURSIVE n(x) AS (VALUES(0) UNION ALL SELECT x+1 FROM n WHERE x<100000000) SELECT sum(x) FROM n').fetchone()
        yield from original(self,kind)
    monkeypatch.setattr(reporting.Snapshot,'records',expensive)
    async def run():
        async def send(message):pass
        async def receive():await anyio.sleep(10)
        response=reporting.ReportResponse(reporting.report_stream(store.path,'json','report-task',permit),permit=permit)
        with pytest.raises(ExportDeadline):
            await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
    started=time.monotonic();asyncio.run(run())
    assert time.monotonic()-started<1
    assert opened[0].closed and pool.metrics()['active']==0 and pool.metrics()['timed_out']==1


@pytest.mark.parametrize('error',[OSError('disconnected'),ValueError('failed send')])
def test_send_error_releases_slot_and_records_outcome(tmp_path,error):
    store=Store(tmp_path/'report.db');seed(store,1)
    pool=ExportPool(ExportPolicy());permit=pool.acquire()
    async def run():
        async def send(message):
            if message['type']=='http.response.body':raise error
        async def receive():await anyio.sleep(10)
        response=reporting.ReportResponse(reporting.report_stream(store.path,'json','report-task',permit),permit=permit)
        with pytest.raises(Exception):
            await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
    asyncio.run(run())
    expected='cancelled' if isinstance(error,OSError) else 'failed'
    assert pool.metrics()['active']==0 and pool.metrics()[expected]==1


def test_disconnect_interrupts_active_sql_before_deadline(tmp_path,monkeypatch):
    store=Store(tmp_path/'report.db');seed(store,1)
    opened=track_connections(monkeypatch)
    pool=ExportPool(ExportPolicy(timeout=10));permit=pool.acquire()
    started_sql=threading.Event()
    original=reporting.Snapshot.records
    def expensive(self,kind):
        if kind=='tasks':
            started_sql.set()
            self.db.execute('WITH RECURSIVE n(x) AS (VALUES(0) UNION ALL SELECT x+1 FROM n WHERE x<100000000) SELECT sum(x) FROM n').fetchone()
        yield from original(self,kind)
    monkeypatch.setattr(reporting.Snapshot,'records',expensive)
    async def run():
        async def send(message):pass
        async def receive():
            while not started_sql.is_set():await anyio.sleep(.001)
            return {'type':'http.disconnect'}
        response=reporting.ReportResponse(reporting.report_stream(store.path,'json','report-task',permit),permit=permit)
        await response({'type':'http','asgi':{'spec_version':'2.0'}},receive,send)
    started=time.monotonic();asyncio.run(run())
    assert time.monotonic()-started<1
    assert opened[0].closed and pool.metrics()['active']==0 and pool.metrics()['cancelled']==1
    assert pool.metrics()['timed_out']==0
