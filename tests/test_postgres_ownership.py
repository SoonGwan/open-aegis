"""Owned real backend-session loss and cross-process/runtime fencing."""
import os
import select
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from aegis import postgres_transfer as transfer
from aegis.postgres_maintenance import PostgresLease
from aegis.postgres_store import PostgresStore
from aegis.maintenance import WorkspaceBusy
from aegis.engine import Engine
from aegis.network import Transport
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_store import stores
from tests.test_postgres_engine import plan


def terminate_owner(postgres,owner):
    # Kill only the dedicated backend this test acquired in its disposable DB.
    with transfer.connect(postgres['dsn']) as db:
        identity=db.execute('SELECT backend_start FROM pg_stat_activity WHERE pid=%s',(owner.pid,)).fetchone()
        assert identity and identity['backend_start']==owner.backend_start
        assert db.execute('SELECT pg_terminate_backend(%s) AS killed',(owner.pid,)).fetchone()['killed']


def test_owner_exclusion_cross_process_and_release(stores,postgres):
    _,pg=stores
    environment={**os.environ,'OWNED_PG_DSN':postgres['dsn'],'OWNED_PG_SCHEMA':pg.schema}
    code="""
import os,sys
from aegis.postgres_maintenance import PostgresLease
with PostgresLease(os.environ['OWNED_PG_DSN'],os.environ['OWNED_PG_SCHEMA']):
    print('owned-ready',flush=True)
    sys.stdin.readline()
"""
    child=subprocess.Popen([sys.executable,'-c',code],env=environment,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        assert select.select([child.stdout],[],[],10)[0]
        assert child.stdout.readline().strip()=='owned-ready'
        with pytest.raises(WorkspaceBusy):PostgresLease(postgres['dsn'],pg.schema)
        child.communicate('\n',timeout=10);assert child.returncode==0
        with PostgresLease(postgres['dsn'],pg.schema):pass
    finally:
        if child.poll() is None:child.kill();child.communicate(timeout=10)


def test_lost_owner_never_reconnects_or_accepts_replacement(stores,postgres):
    _,pg=stores;owner=pg.acquire_runtime()
    try:
        pg.put('notes',{'id':'before','title':'Owned'})
        terminate_owner(postgres,owner)
        fresh=PostgresStore(postgres['dsn'],pg.schema)
        with fresh.acquire_runtime():
            with pytest.raises(WorkspaceBusy):pg.put('notes',{'id':'stale','title':'must refuse'})
            with pytest.raises(WorkspaceBusy):
                with pg.execution_permit():pytest.fail('Stale admission')
            assert fresh.get('notes','stale') is None
            fresh.put('notes',{'id':'new','title':'Replacement'})
            with pytest.raises(WorkspaceBusy):pg.acquire_runtime()
    finally:owner.close()


def test_admitted_write_transaction_fences_takeover_until_commit(stores,postgres):
    _,pg=stores;owner=pg.acquire_runtime()
    try:
        with pg.write_transaction() as db:
            pg.put_many([('notes',{'id':'admitted','title':'Complete admitted write'})],connection=db)
            terminate_owner(postgres,owner)
            with pytest.raises(WorkspaceBusy):PostgresLease(postgres['dsn'],pg.schema)
        with PostgresLease(postgres['dsn'],pg.schema):
            assert PostgresStore(postgres['dsn'],pg.schema).get('notes','admitted')
        with pytest.raises(WorkspaceBusy):pg.patch('notes','admitted',title='stale')
    finally:owner.close()


def test_active_owner_refuses_offline_writer_and_export(stores,postgres,tmp_path):
    import psycopg
    _,pg=stores;owner=pg.acquire_runtime()
    try:
        offline=PostgresStore(postgres['dsn'],pg.schema)
        with pytest.raises(psycopg.errors.LockNotAvailable):offline.put('notes',{'id':'offline','title':'must refuse'})
        assert offline.get('notes','offline') is None
        output=tmp_path/'blocked'/'aegis.db'
        with pytest.raises(WorkspaceBusy):transfer.postgres_to_sqlite(postgres['dsn'],pg.schema,output)
        assert not output.exists() and not list(output.parent.glob('.pg-transfer-*'))
    finally:owner.close()
    assert transfer.postgres_to_sqlite(postgres['dsn'],pg.schema,tmp_path/'returned'/'aegis.db')['audit']['valid']


@pytest.fixture
def held_http():
    entered=threading.Event();release=threading.Event();requests=[]
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path);entered.set();release.wait(5)
            try:
                self.send_response(200);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'OK')
            except (BrokenPipeError,ConnectionResetError):pass
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}/',entered,release,requests
    finally:
        release.set();server.shutdown();server.server_close();thread.join(timeout=2)


def test_inflight_target_request_fences_takeover_and_next_request_is_denied(stores,postgres,held_http):
    _,pg=stores;owner=pg.acquire_runtime();url,entered,release,requests=held_http
    transport=Transport(url,allow_private=True,execution_permit=pg.execution_permit,delay=0)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(transport.get)
            assert entered.wait(2)
            terminate_owner(postgres,owner)
            with pytest.raises(WorkspaceBusy):PostgresLease(postgres['dsn'],pg.schema)
            release.set();assert future.result(timeout=5)['status']==200
        with PostgresLease(postgres['dsn'],pg.schema):
            with pytest.raises(WorkspaceBusy):transport.get()
        assert requests==['/']
    finally:release.set();owner.close()


def test_engine_constructor_failure_releases_runtime_lease(stores,postgres,monkeypatch):
    _,pg=stores
    asset={'id':'owned','name':'Owned','url':'https://owned.invalid/','revision':1}
    pg.put('tasks',plan('interrupted',asset,status='running'))
    def fail(*args):raise RuntimeError('Owned startup recovery failure')
    monkeypatch.setattr('aegis.engine.finish_remaining',fail)
    with pytest.raises(RuntimeError):Engine(pg)
    assert pg.owner.closed
    with PostgresLease(postgres['dsn'],pg.schema):
        assert PostgresStore(postgres['dsn'],pg.schema).get('tasks','interrupted')['status']=='running'


def test_engine_duplicate_start_does_not_recover_live_task(stores,postgres):
    _,pg=stores;engine=Engine(pg)
    try:
        pg.put('tasks',{'id':'live','status':'running'})
        other=PostgresStore(postgres['dsn'],pg.schema)
        with pytest.raises(WorkspaceBusy):Engine(other)
        assert pg.get('tasks','live')['status']=='running'
        terminate_owner(postgres,engine.owner)
        end=time.monotonic()+3
        while not engine.closed and time.monotonic()<end:time.sleep(.02)
        assert engine.closed and engine.queue_stop.is_set()
    finally:engine.shutdown()
    replacement_store=PostgresStore(postgres['dsn'],pg.schema);replacement=Engine(replacement_store)
    try:
        assert replacement_store.get('tasks','live')['status']=='interrupted'
        assert replacement_store.audit_integrity()['valid']
    finally:replacement.shutdown()


def test_closed_or_unbound_store_cannot_start_target_request(stores,held_http):
    _,pg=stores;url,_,_,requests=held_http
    transport=Transport(url,allow_private=True,execution_permit=pg.execution_permit)
    with pytest.raises(WorkspaceBusy):transport.get()
    owner=pg.acquire_runtime();owner.close()
    with pytest.raises(WorkspaceBusy):transport.get()
    assert not requests


def test_engine_pool_creation_failure_releases_owner(stores,postgres):
    from aegis.runtime import ExecutionPolicy
    _,pg=stores
    with pytest.raises(ValueError):Engine(pg,policy=ExecutionPolicy(concurrent_tasks=0))
    assert pg.owner.closed
    with PostgresLease(postgres['dsn'],pg.schema):pass


def test_provider_inflight_fences_takeover_and_loss_recovers_unknown_usage(stores,postgres,monkeypatch):
    import json
    from aegis.conversation_ai import draft
    _,pg=stores;owner=pg.acquire_runtime();entered=threading.Event();release=threading.Event();requests=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']));requests.append(self.path);entered.set();release.wait(5)
            body=json.dumps({'choices':[{'message':{'content':json.dumps({'blocks':[{'text':'Owned draft','citations':['T1']}]})}}],
                             'usage':{'prompt_tokens':3,'completion_tokens':2,'total_tokens':5}}).encode()
            try:
                self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError):pass
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    monkeypatch.setenv('AEGIS_LLM_MODEL','owned-model');monkeypatch.setenv('AEGIS_LLM_API_KEY','owned-lease-key')
    monkeypatch.setenv('AEGIS_LLM_BASE_URL',f'http://127.0.0.1:{server.server_port}/v1');monkeypatch.setenv('AEGIS_LLM_PRICES','[]')
    summary={'content':'Owned summary','provenance':{'citations':[{'label':'T1','title':'Owned','snapshot':{'id':'owned'}}]}}
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future=executor.submit(draft,summary,'Owned question',store=pg,task_id='owned',actor_id=None,allow_local=True)
            assert entered.wait(2)
            terminate_owner(postgres,owner)
            with pytest.raises(WorkspaceBusy):PostgresLease(postgres['dsn'],pg.schema)
            release.set()
            with pytest.raises(WorkspaceBusy):future.result(timeout=5)
        replacement_store=PostgresStore(postgres['dsn'],pg.schema);replacement=Engine(replacement_store)
        try:
            row=replacement_store.page('llm_calls')['items'][0]
            assert row['state']=='interrupted' and row['tokens']['status']=='missing'
            assert row['tokens']['total_tokens'] is None and row['outcome']=='unknown'
            assert replacement_store.count('messages')==0 and replacement_store.audit_integrity()['valid']
            with pytest.raises(WorkspaceBusy):draft(summary,'Another question',store=pg,task_id='owned',actor_id=None,allow_local=True)
            assert requests==['/v1/chat/completions']
        finally:replacement.shutdown()
    finally:
        release.set();owner.close();server.shutdown();server.server_close();thread.join(timeout=2)


def test_owner_protocol_works_without_superuser_permissions(stores,postgres):
    _,pg=stores;_,sql,_=transfer.driver();role=schema()
    with transfer.connect(postgres['dsn']) as admin:
        admin.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
        admin.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(pg.schema),sql.Identifier(role)))
        admin.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(pg.schema),sql.Identifier(role)))
        admin.execute(sql.SQL('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA {} TO {}').format(sql.Identifier(pg.schema),sql.Identifier(role)))
    try:
        ordinary=PostgresStore(postgres['dsn']+' user='+role,pg.schema)
        with ordinary.acquire_runtime():
            with ordinary.transaction() as db:assert not db.execute("SELECT rolsuper FROM pg_roles WHERE rolname=current_user").fetchone()['rolsuper']
            ordinary.put('notes',{'id':'ordinary','title':'Owned ordinary role'})
            ordinary.event('owned','Ordinary role audit')
            assert ordinary.audit_integrity()['valid']
        assert pg.get('notes','ordinary')['title']=='Owned ordinary role'
    finally:
        with transfer.connect(postgres['dsn']) as admin:
            admin.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
            admin.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))


def test_runtime_ownership_is_independent_per_schema(stores,postgres):
    sqlite,pg=stores;other=schema()
    transfer.sqlite_to_postgres(sqlite.path,postgres['dsn'],other)
    second=PostgresStore(postgres['dsn'],other)
    with pg.acquire_runtime(),second.acquire_runtime():
        pg.put('notes',{'id':'one','title':'First schema'})
        second.put('notes',{'id':'two','title':'Second schema'})
        assert pg.get('notes','two') is None and second.get('notes','one') is None
