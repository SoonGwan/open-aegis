"""Native Store parity/concurrency against an actual owned PostgreSQL cluster."""
import json
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from aegis import postgres_transfer as transfer
from aegis import postgres_store
from aegis.postgres_store import PostgresStore
from aegis.store import Store,MessageRequestConflict
from aegis.auth import new_user
from aegis.coverage import latest_summary as sqlite_coverage
from aegis.postgres_coverage import latest_summary as pg_coverage
from tests.test_postgres_transfer import postgres,schema


@pytest.fixture
def stores(postgres,tmp_path):
    sqlite=Store(tmp_path/'source'/'aegis.db')
    name=schema();transfer.sqlite_to_postgres(sqlite.path,postgres['dsn'],name)
    return sqlite,PostgresStore(postgres['dsn'],name)


def seed(stores,records):
    for store in stores:store.put_many(records)


def test_literal_search_pages_upsert_watermark_and_atomic_batches(stores):
    sqlite,pg=stores
    seed(stores,[('notes',{'id':str(i),'title':'Owned %_ quote\' 한국 '+str(i),'content':'ÄBC abc'}) for i in range(30)])
    for query in ['%_','quote\'','한국','abc','äbc','% OR 1=1 --']:
        assert pg.page('notes',search=query)==sqlite.page('notes',search=query)
    first=pg.page('notes');old=pg.page('notes',offset=25,snapshot=first['snapshot'])
    pg.put('notes',{'id':'later','title':'later'});pg.patch('notes','0',content='updated')
    assert pg.page('notes',offset=25,snapshot=first['snapshot'])['total']==30
    assert pg.get('notes','0')['content']=='updated' and len(old['items'])==5
    assert pg.count('notes')==31
    with pytest.raises(ValueError):pg.put_many([('notes',{'id':'must-rollback'}),('notes',{'id':'bad','number':float('nan')})])
    assert pg.get('notes','must-rollback') is None
    with pytest.raises(KeyError):pg.patch('notes','missing',title='x')


def test_roles_sessions_uniqueness_and_security_change_revocation(stores):
    _,pg=stores;user=new_user('admin','합성 관리자','admin','owned-pg-store-password');pg.add_user(user)
    pg.session('old',time.time()+300,user['id'])
    assert pg.session_user('old')==user and pg.users()==[user]
    pg.update_user(user['id'],name='renamed');assert pg.valid_session('old')
    pg.update_user(user['id'],role='operator');assert not pg.valid_session('old')
    pg.session('second',time.time()+300,user['id']);pg.update_user(user['id'],disabled=True)
    assert not pg.valid_session('second') and pg.user(id=user['id'])['disabled']==1
    import psycopg
    duplicate={**user,'id':'different'}
    with pytest.raises(psycopg.IntegrityError):pg.add_user(duplicate)
    assert len(pg.users())==1
    pg.update_user(user['id'],disabled=False);pg.session('third',time.time()+300,user['id']);pg.logout('third')
    assert not pg.valid_session('third')


def test_native_audit_concurrent_store_instances_and_return_sequence(postgres,stores,tmp_path):
    _,pg=stores
    second=PostgresStore(postgres['dsn'],pg.schema)
    def event(i):(pg if i%2 else second).event('owned','owned %_ '+str(i),detail={'i':i})
    with ThreadPoolExecutor(max_workers=6) as workers:list(workers.map(event,range(30)))
    audit=pg.audit_integrity();assert audit['valid'] and audit['events']==30
    assert pg.audit_integrity(audit['checkpoint'])==audit
    assert len(pg.events(task_id='owned'))==30
    page=pg.event_page('owned',search='%_');assert page['total']==30 and len(page['items'])==25
    pg.event('owned','later');assert pg.event_page('owned',snapshot=page['snapshot'])['total']==30
    output=tmp_path/'returned'/'aegis.db'
    result=transfer.postgres_to_sqlite(postgres['dsn'],pg.schema,output)
    returned=Store(output);returned.event('owned','after-return')
    assert returned.audit_integrity()['events']==32 and returned.events()[-1]['seq']==32


def test_message_replay_conflict_and_audit_failure_roll_back_pair(stores,monkeypatch):
    _,pg=stores
    question={'id':'q','task_id':'owned','content':'question','mode':'ai','role':'user'}
    reply={'id':'r','task_id':'owned','role':'assistant','content':'reply','assistant_generation':{'model':'synthetic','outcome':'accepted'}}
    assert pg.put_message_exchange(question,reply)==reply
    assert pg.put_message_exchange(question,{**reply,'content':'must-not-overwrite'})==reply
    with pytest.raises(MessageRequestConflict):pg.put_message_exchange({**question,'content':'different'},reply)
    before=pg.audit_integrity()
    def fail(*args):raise RuntimeError('Owned final audit failure')
    monkeypatch.setattr(postgres_store,'append_event',fail)
    with pytest.raises(RuntimeError):pg.put_message_exchange({**question,'id':'q2'},{**reply,'id':'r2'})
    assert pg.get('messages','q2') is None and pg.get('messages','r2') is None and pg.audit_integrity()==before


def test_array_relationship_proofs_priority_and_compact_projection(stores):
    evidence={'id':'proof','task_id':'t','asset_id':'a','check':'security_headers','fingerprint':'same'}
    finding={'id':'f','title':'Owned','task_ids':['t'],'evidence_ids':['proof','foreign'],'asset_id':'a','check':'security_headers','fingerprint':'same','severity':'high'}
    seed(stores,[('findings',finding),('evidence',evidence),('evidence',{**evidence,'id':'foreign','asset_id':'different'}),('findings',{**finding,'id':'critical','severity':'critical'})])
    sqlite,pg=stores
    for kind,filters in [('findings',{'task_id':'t'}),('evidence',{'finding_id':'f'}),('findings',{'asset_id':'a'})]:
        assert pg.page(kind,filters=filters)==sqlite.page(kind,filters=filters)
    assert pg.page('findings',priority=True,compact_findings=True)==sqlite.page('findings',priority=True,compact_findings=True)
    assert pg.get('findings','f',compact_findings=True)==sqlite.get('findings','f',compact_findings=True)
    with pytest.raises(ValueError):pg.page('notes',filters={'state':'committed'})
    with pytest.raises(ValueError):pg.page('notes',archived=False)


def test_assets_observation_names_and_revision_coverage_match_sqlite(stores):
    sqlite,pg=stores
    asset={'id':'a','name':'자산 %_','url':'https://owned.invalid/','revision':2,'archived_at':None}
    task={'id':'t','name':'작업 %_','status':'completed','created_at':1,'approved_at':2,'asset_ids':['a'],'checks':['security_headers'],'scope_snapshot':[{**asset,'revision':1}]}
    seed(stores,[('assets',asset),('assets',{**asset,'id':'archived','archived_at':10}),('tasks',task),('coverage',{'id':'t:a:security_headers','asset_id':'a','task_id':'t','check':'security_headers','status':'completed'}),('observations',{'id':'o','asset_id':'a','task_id':'t','url':'https://owned.invalid/path'})])
    assert pg.page('observations',search='작업 %_')==sqlite.page('observations',search='작업 %_')
    assert pg.asset_url_exists(asset['url']) and pg.asset_has_tasks('a') and not pg.asset_has_tasks('a',active_only=True)
    assert pg.count('assets',active_assets=True)==1
    assert pg.page('assets',archived=False)==sqlite.page('assets',archived=False)
    with sqlite.connect() as db:expected=sqlite_coverage(db)
    with pg.transaction() as db:assert pg_coverage(db)==expected
    assert expected['counts']['stale']==1


def test_scheduler_and_unfinished_task_batches(stores):
    sqlite,pg=stores
    seed(stores,[('schedules',{'id':'s','enabled':True,'next_at':3,'task':{'name':'Owned','asset_ids':['a']}}),('schedules',{'id':'off','enabled':False,'next_at':1,'task':{'asset_ids':['a']}}),('tasks',{'id':'unfinished','status':'queued','asset_ids':['a']})])
    assert pg.due_schedules(4)==sqlite.due_schedules(4)
    assert list(pg.enabled_schedule_ids('a'))==list(sqlite.enabled_schedule_ids('a'))
    assert pg.page('schedules',filters={'enabled':True,'asset_id':'a'})==sqlite.page('schedules',filters={'enabled':True,'asset_id':'a'})
    assert list(pg.recovery_tasks())==list(sqlite.recovery_tasks())
    assert pg.asset_has_tasks('a',active_only=True)


def test_readonly_snapshot_and_constructor_do_not_change_sessions(stores,postgres):
    import psycopg
    _,pg=stores
    user=new_user('snapshot','Owned','viewer','owned-snapshot-password');pg.add_user(user)
    pg.session('keep',time.time()+300,user['id']);pg.put('notes',{'id':'n','title':'before'})
    before=pg.audit_integrity()
    other=PostgresStore(postgres['dsn'],pg.schema)
    assert other.valid_session('keep') and other.audit_integrity()==before
    with pg.transaction() as db:
        assert pg.get('notes','n',connection=db)['title']=='before'
        other.patch('notes','n',title='after')
        assert pg.get('notes','n',connection=db)['title']=='before'
    assert pg.get('notes','n')['title']=='after'
    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        with pg.transaction() as db:db.execute("DELETE FROM records WHERE id='n'")
    assert pg.get('notes','n')['title']=='after'


def test_observed_attempt_commit_and_planner_audit_failure_are_atomic(stores,monkeypatch):
    _,pg=stores
    pg.put('tasks',{'id':'t','name':'Owned','status':'completed'})
    detail={'call_id':'call','model':'synthetic','outcome':'accepted','tokens':{'total':3},'cost':None,'started_at':1,'observed_at':2}
    attempt={'id':'call','task_id':'t','source':'planner','state':'observed',**{k:v for k,v in detail.items() if k!='call_id'}}
    pg.put('llm_calls',attempt)
    with pytest.raises(RuntimeError):pg.record_planner_call('t',{**detail,'model':'wrong'},'Owned','info')
    assert pg.get('tasks','t').get('llm_usage') is None and pg.get('llm_calls','call')==attempt
    original=postgres_store.append_event
    def fail_after_append(db,values):
        original(db,values)
        raise RuntimeError('Owned failure after sequence allocation and audit write')
    monkeypatch.setattr(postgres_store,'append_event',fail_after_append)
    with pytest.raises(RuntimeError):pg.record_planner_call('t',detail,'Owned','info')
    assert pg.get('tasks','t').get('llm_usage') is None and pg.get('llm_calls','call')==attempt
    assert pg.audit_integrity()['events']==0
    monkeypatch.setattr(postgres_store,'append_event',original)
    pg.record_planner_call('t',detail,'Owned','info')
    assert pg.get('tasks','t')['llm_usage']==detail
    committed=pg.get('llm_calls','call')
    assert committed['state']=='committed' and committed['record_kind']=='tasks' and committed['record_id']=='t'
    assert pg.events()[0]['seq']==2 and pg.audit_integrity()['events']==1


def test_failed_identity_allocation_survives_dump_and_return(stores,postgres,tmp_path,monkeypatch):
    import subprocess
    _,pg=stores
    pg.event('owned','before');checkpoint=pg.audit_integrity()['checkpoint']
    original=postgres_store.append_event
    def fail_after_append(db,values):
        original(db,values)
        raise RuntimeError('Owned failed transaction')
    monkeypatch.setattr(postgres_store,'append_event',fail_after_append)
    with pytest.raises(RuntimeError):pg.event('owned','never committed')
    assert len(pg.events())==1 and pg.audit_integrity()['checkpoint']==checkpoint
    dump=tmp_path/'native.dump'
    # The fixture supplies only an owned UNIX socket, no external database.
    subprocess.run(['pg_dump','--dbname',postgres['dsn'],'--format=custom','--schema',pg.schema,'--file',str(dump)],check=True,capture_output=True)
    subprocess.run(['createdb','--maintenance-db',postgres['dsn'],pg.schema],check=True,capture_output=True)
    restored_dsn=postgres['dsn'].replace('dbname=postgres','dbname='+pg.schema)
    subprocess.run(['pg_restore','--exit-on-error','--dbname',restored_dsn,str(dump)],check=True,capture_output=True)
    output=tmp_path/'returned-gap'/'aegis.db'
    transfer.postgres_to_sqlite(restored_dsn,pg.schema,output)
    returned=Store(output);returned.event('owned','returned')
    assert returned.events()[-1]['seq']==3 and returned.audit_integrity()['events']==2
    monkeypatch.setattr(postgres_store,'append_event',original)
    pg.event('owned','continued')
    assert pg.audit_integrity(checkpoint)['events']==2 and pg.events()[-1]['seq']==3


def test_native_audit_checkpoint_and_tail_tampering_rejected(stores):
    from aegis.audit import AuditIntegrityError
    _,pg=stores;pg.event('owned','first');checkpoint=pg.audit_integrity()['checkpoint']
    pg.event('owned','second');assert pg.audit_integrity(checkpoint)['events']==2
    with pytest.raises(AuditIntegrityError):pg.audit_integrity({**checkpoint,'hash':'0'*64})
    with pg.transaction(write=True) as db:db.execute("UPDATE events SET message='tampered' WHERE seq=2")
    with pytest.raises(AuditIntegrityError):pg.audit_integrity()
    with pytest.raises(AuditIntegrityError):pg.event('owned','must not append')
    assert len(pg.events())==2
