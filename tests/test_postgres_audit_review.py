"""Read-only native audit review, snapshot integrity and bounded cancellation."""
from concurrent.futures import ThreadPoolExecutor
import json
import threading
import time
import tracemalloc

import pytest
from aegis import postgres_transfer as transfer
from aegis.audit import event_hash,GENESIS
from aegis.audit_review import AuditReview,AuditReviewBusy
from aegis.maintenance import WorkspaceBusy
from aegis.postgres_maintenance import PostgresLease
from aegis.postgres_store import PostgresStore
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_store import stores
from tests.test_postgres_reports import track


def test_native_review_readonly_private_checkpoint_prefix_and_empty(stores,monkeypatch):
    import psycopg
    sqlite,pg=stores
    expected=AuditReview(sqlite).run();actual=AuditReview(pg).run()
    for field in ('status','events','sealed_legacy_until','checkpoint_compared'):
        assert actual[field]==expected[field]
    assert actual['events']==0
    pg.event(None,'DO-NOT-EXPOSE-EVENT',detail={'secret':'DO-NOT-EXPOSE-DETAIL'})
    before=pg.audit_integrity();prefix=before['checkpoint']
    with pg.transaction() as db:manifest=transfer.postgres_manifest(db)
    opened=track(monkeypatch);review=AuditReview(pg)
    verified=review.run();assert verified['status']=='verified' and verified['checkpoint']==prefix
    assert verified['checkpoint_compared'] is False and 'DO-NOT-EXPOSE' not in json.dumps(verified)
    assert opened[-1].closed
    with pg.transaction() as db:assert transfer.postgres_manifest(db)==manifest
    original=transfer.verify_chain
    def try_write(db,*args,**kwargs):
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):db.execute('DELETE FROM events')
        return original(db,*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(transfer,'verify_chain',try_write)
        assert review.run()['status']=='inconclusive'
    assert pg.audit_integrity()==before
    pg.event(None,'later');result=review.run(prefix)
    assert result['status']=='verified' and result['events']==2 and result['checkpoint_compared'] is True
    for changes in ({'hash':'f'*64},{'chain_id':'f'*32},{'seq':100},{'hash':'bad'}):
        result=review.run({**prefix,**changes})
        assert result['status']=='mismatch' and 'DO-NOT-EXPOSE' not in json.dumps(result)
    assert all(db.closed for db in opened)
    assert pg.audit_integrity()['events']==2


@pytest.mark.parametrize('change',[
    "UPDATE events SET message='DO-NOT-EXPOSE-TAMPER' WHERE seq=2",
    'DELETE FROM event_hashes WHERE seq=2',
    'DELETE FROM event_hashes WHERE seq=3; DELETE FROM events WHERE seq=3',
    "UPDATE audit_state SET head_hash='0000000000000000000000000000000000000000000000000000000000000000'",
    "UPDATE audit_state SET chain_id=''",
    'UPDATE audit_state SET sealed_legacy_until=99',
    "INSERT INTO events(ts,message,detail) VALUES(0,'DO-NOT-EXPOSE-UNSEALED','{}')",
])
def test_native_review_mismatch_never_repairs_or_exposes_payload(stores,change):
    _,pg=stores
    for i in range(3):pg.event(None,'event'+str(i))
    with pg.transaction(write=True) as db:
        for statement in change.split(';'):db.execute(statement)
    with pg.transaction() as db:before=transfer.postgres_manifest(db)
    result=AuditReview(pg).run()
    assert result['status']=='mismatch' and 'DO-NOT-EXPOSE' not in json.dumps(result)
    with pg.transaction() as db:assert transfer.postgres_manifest(db)==before


def test_native_review_same_snapshot_when_audit_is_appended(stores,monkeypatch):
    _,pg=stores;pg.event(None,'before');expected=pg.audit_integrity();owner=pg.acquire_runtime()
    original=transfer.verify_chain;written=[]
    def changed(*args,**kwargs):
        if not written:
            written.append(True);pg.event(None,'concurrent')
        return original(*args,**kwargs)
    monkeypatch.setattr(transfer,'verify_chain',changed)
    try:
        result=AuditReview(pg).run(expected['checkpoint'])
        assert written and result['events']==1 and result['checkpoint']==expected['checkpoint']
        next_result=AuditReview(pg).run(expected['checkpoint'])
        assert next_result['events']==2 and next_result['status']=='verified'
    finally:owner.close()


def test_native_review_capacity_actual_sql_timeout_and_retry(stores,monkeypatch):
    _,pg=stores;pg.event(None,'preserved')
    review=AuditReview(pg,timeout=.15);opened=track(monkeypatch);original=transfer.verify_chain
    def expensive(db,*args,**kwargs):
        db.execute('SELECT pg_sleep(10)').fetchone()
        return original(db,*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(transfer,'verify_chain',expensive)
        start=time.monotonic();result=review.run()
        assert result['status']=='inconclusive' and time.monotonic()-start<2
    assert opened[-1].closed
    assert not any(t.name=='aegis-report-cancel' and t.is_alive() for t in threading.enumerate())
    review.timeout=10;assert review.run()['status']=='verified'
    entered,release=threading.Event(),threading.Event()
    def held(*args,**kwargs):
        entered.set();assert release.wait(5)
        return original(*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(transfer,'verify_chain',held)
        with ThreadPoolExecutor(max_workers=1) as executor:
            active=executor.submit(review.run);assert entered.wait(5)
            try:
                with pytest.raises(AuditReviewBusy):review.run()
            finally:release.set()
            assert active.result()['status']=='verified'
    assert review.run()['status']=='verified' and all(db.closed for db in opened)


def test_native_review_read_error_and_closed_owner_are_inconclusive(stores,monkeypatch):
    _,pg=stores;pg.event(None,'DO-NOT-EXPOSE-EVENT')
    opened=track(monkeypatch);review=AuditReview(pg)
    with pg.transaction(write=True) as db:db.execute('ALTER TABLE event_hashes RENAME TO hidden_hashes')
    try:
        result=review.run()
        assert result['status']=='inconclusive' and 'hidden_hashes' not in json.dumps(result)
        assert opened[-1].closed
    finally:
        with pg.transaction(write=True) as db:db.execute('ALTER TABLE hidden_hashes RENAME TO event_hashes')
    owner=pg.acquire_runtime();owner.close()
    assert review.run()['status']=='inconclusive' and opened[-1].closed
    assert AuditReview(PostgresStore(pg._dsn,pg.schema)).run()['status']=='verified'


def test_native_review_streams_large_history_with_bounded_client_memory(stores,monkeypatch):
    import psycopg
    _,pg=stores;rows=[];previous=GENESIS
    for i in range(1,10001):
        row={'seq':i,'ts':1.0,'task_id':None,'level':'info','message':'audit'+str(i),'detail':'x'*2048}
        digest=event_hash(row,previous);rows.append((row,previous,digest));previous=digest
    with pg.transaction(write=True) as db,db.cursor() as cursor:
        cursor.executemany('INSERT INTO events(seq,ts,task_id,level,message,detail) VALUES (%s,%s,%s,%s,%s,%s)',
                           [tuple(row[k] for k in ('seq','ts','task_id','level','message','detail')) for row,_,_ in rows])
        cursor.executemany('INSERT INTO event_hashes VALUES (%s,%s,%s)',[(row['seq'],prior,digest) for row,prior,digest in rows])
        db.execute('UPDATE audit_state SET last_seq=10000,head_hash=%s',(previous,))
        db.execute("SELECT setval(pg_get_serial_sequence('events','seq'),10000,true)")
        db.execute('UPDATE storage_metadata SET event_sequence=10000')
    del rows
    cursors=[];original=psycopg.Connection.cursor
    def cursor(self,*args,**kwargs):
        result=original(self,*args,**kwargs)
        if kwargs.get('name')=='aegis_audit_verification':cursors.append(result)
        return result
    monkeypatch.setattr(psycopg.Connection,'cursor',cursor)
    tracemalloc.start()
    try:
        result=AuditReview(pg,timeout=10).run()
        _,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop()
    assert result['status']=='verified' and result['events']==10000 and peak<2_000_000
    assert len(cursors)==1 and cursors[0].itersize==32 and cursors[0].closed


def test_native_admitted_review_fences_replacement_until_finished(stores,postgres,monkeypatch):
    _,pg=stores;pg.event(None,'before');owner=pg.acquire_runtime()
    original=transfer.verify_chain;entered,release=threading.Event(),threading.Event();replacement=None
    def held(*args,**kwargs):
        entered.set();assert release.wait(5)
        return original(*args,**kwargs)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(transfer,'verify_chain',held)
            with ThreadPoolExecutor(max_workers=1) as executor:
                active=executor.submit(AuditReview(pg).run);assert entered.wait(5)
                try:
                    with transfer.connect(postgres['dsn']) as db:
                        assert db.execute('SELECT pg_terminate_backend(%s) AS killed',(owner.pid,)).fetchone()['killed']
                    with pytest.raises(WorkspaceBusy):PostgresLease(postgres['dsn'],pg.schema)
                finally:release.set()
                assert active.result()['status']=='verified'
        replacement=PostgresLease(postgres['dsn'],pg.schema)
        assert AuditReview(pg).run()['status']=='inconclusive'
    finally:
        release.set()
        if replacement:replacement.close()
        owner.close()
