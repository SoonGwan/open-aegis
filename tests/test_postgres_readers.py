"""Native MCP/audit readers: safe selection, read-only roles and one snapshot."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest
from aegis import mcp,postgres_transfer as transfer
from aegis.postgres_store import PostgresStore
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_store import stores
from tests.test_finding_records import populate


def message(name,args=None):
    return {'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':args or {}}}


def env(pg,folder):
    return {**os.environ,'AEGIS_STORAGE_BACKEND':'postgres','AEGIS_POSTGRES_DSN':pg._dsn,
            'AEGIS_POSTGRES_SCHEMA':pg.schema,'AEGIS_DATA_DIR':str(folder)}


def run(pg,folder,module,args=(),input=None,extra=None):
    return subprocess.run([sys.executable,'-m',module,*args],input=input,text=True,capture_output=True,
                          timeout=10,env={**env(pg,folder),**(extra or {})})


def test_native_mcp_all_tools_pages_provenance_and_no_writes(stores,monkeypatch):
    import aegis.store,aegis.postgres_store,aegis.coverage
    monkeypatch.setattr(aegis.store,'now',lambda:123.)
    monkeypatch.setattr(aegis.postgres_store,'now',lambda:123.)
    monkeypatch.setattr(aegis.coverage,'now',lambda:123.)
    sqlite,pg=stores
    for store in stores:
        populate(store,30)
        store.put('assets',{'id':'asset-a','name':'Owned fixture'})
        store.put('tasks',{'id':'task-a','status':'completed','created_at':1,'scope_snapshot':[{'id':'asset-a'}],'checks':['security_headers']})
        for i in range(60):store.event('task-a',str(i))
        store.put('settings',{'id':'auth','password_hash':'DO-NOT-EXPOSE'})
    reader=mcp.PostgresReader(pg._dsn,pg.schema);control=mcp.Reader(sqlite.path)
    with pg.transaction() as db:before=transfer.postgres_manifest(db)
    cases=[('list_assets',{}),('list_findings',{}),('get_task',{'id':'task-a'}),('get_finding',{'id':'finding-a'}),
           ('list_finding_evidence',{'id':'finding-a','offset':25}),('list_finding_retests',{'id':'finding-a'}),
           ('list_task_events',{'id':'task-a'}),('list_task_events',{'id':'task-a','offset':25,'snapshot':60})]
    for name,args in cases:
        assert reader.call(name,args)==control.call(name,args)
        assert 'DO-NOT-EXPOSE' not in json.dumps(mcp.dispatch(message(name,args),reader))
    assert reader.call('get_task',{'id':'task-a'})['coverage'][0]['status']=='not_recorded'
    for name,args in [('run_command',{'command':'must refuse'}),('list_assets',{'limit':True}),('list_assets',{'sql':'DELETE FROM records'})]:
        assert mcp.dispatch(message(name,args),reader)['result']['isError']
    with pg.transaction() as db:assert transfer.postgres_manifest(db)==before


def test_native_mcp_result_bounds_and_snapshot_during_proof_change(stores,monkeypatch):
    _,pg=stores;populate(pg,1200)
    reader=mcp.PostgresReader(pg._dsn,pg.schema)
    detail=reader.call('get_finding',{'id':'finding-a'})
    assert len(detail['evidence'])==len(detail['retests'])==25 and detail['evidence_page']['total']==1200
    assert 'evidence_ids' not in detail['finding'] and 'task_ids' not in detail['finding']
    original=reader.get;changed=[]
    def get(kind,id,**options):
        result=original(kind,id,**options)
        if kind=='findings' and not changed:
            changed.append(True);pg.patch('evidence','proof-1199',asset_id='foreign')
        return result
    monkeypatch.setattr(reader,'get',get)
    assert reader.call('get_finding',{'id':'finding-a'})==detail
    later=reader.call('get_finding',{'id':'finding-a'})
    assert later['evidence_page']['total']==1199 and all(row['id']!='proof-1199' for row in later['evidence'])
    pg.put('assets',{'id':'large','name':'x'*(mcp.MAX_TOOL_BYTES+1)})
    result=mcp.dispatch(message('list_assets'),reader)
    assert result['result']['isError'] and len(json.dumps(result))<512


def test_native_stdio_and_audit_cli_use_selected_database_without_sqlite(stores,tmp_path):
    _,pg=stores;pg.put('assets',{'id':'owned','name':'Native fixture'});pg.event('owned','private-event-marker')
    folder=tmp_path/'unused';checkpoint=tmp_path/'checkpoint.json'
    with pg.transaction() as db:before=transfer.postgres_manifest(db)
    process=run(pg,folder,'aegis.mcp',input='\n'.join(json.dumps(m) for m in [
        {'jsonrpc':'2.0','id':1,'method':'initialize'},message('list_assets'),message('run_command',{'command':'x'})])+'\n')
    assert process.returncode==0 and not process.stderr
    output=[json.loads(line) for line in process.stdout.splitlines()]
    assert output[0]['result']['protocolVersion']=='2025-03-26'
    assert json.loads(output[1]['result']['content'][0]['text'])['items'][0]['id']=='owned'
    assert output[2]['result']['isError']
    verified=run(pg,folder,'aegis.cli.audit',['--output',str(checkpoint)])
    assert verified.returncode==0 and json.loads(verified.stdout)['events']==1 and 'private-event-marker' not in verified.stdout
    assert checkpoint.stat().st_mode&0o777==0o600
    with pg.transaction() as db:assert transfer.postgres_manifest(db)==before
    assert not folder.exists()
    pg.event('owned','later')
    assert run(pg,folder,'aegis.cli.audit',['--checkpoint',str(checkpoint)]).returncode==0
    original=checkpoint.read_bytes();assert run(pg,folder,'aegis.cli.audit',['--output',str(checkpoint)]).returncode==2
    assert checkpoint.read_bytes()==original
    output=tmp_path/'must-not-exist.json'
    wrong={**json.loads(original),'hash':'f'*64};bad=tmp_path/'bad.json';bad.write_text(json.dumps(wrong))
    failed=run(pg,folder,'aegis.cli.audit',['--checkpoint',str(bad),'--output',str(output)])
    assert failed.returncode==2 and 'Traceback' not in failed.stderr and not output.exists()
    with pg.transaction(write=True) as db:db.execute("UPDATE events SET message='DO-NOT-EXPOSE-TAMPER' WHERE seq=1")
    failed=run(pg,folder,'aegis.cli.audit',['--output',str(output)])
    assert failed.returncode==2 and 'seq=1' in failed.stderr and 'DO-NOT-EXPOSE' not in failed.stderr and not output.exists()


def test_native_reader_ordinary_select_role_cannot_write_or_read_users(stores,postgres):
    import psycopg
    _,pg=stores;pg.put('assets',{'id':'owned','name':'Read only'})
    role='reader_'+uuid.uuid4().hex[:12]
    with transfer.connect(postgres['dsn']) as db:
        db.execute(f'CREATE ROLE {role} LOGIN')
        db.execute(f'GRANT USAGE ON SCHEMA {pg.schema} TO {role}')
        db.execute(f'GRANT SELECT ON {pg.schema}.records,{pg.schema}.events,{pg.schema}.event_hashes,{pg.schema}.audit_state,{pg.schema}.storage_metadata TO {role}')
    dsn=pg._dsn+' user='+role
    reader=mcp.PostgresReader(dsn,pg.schema)
    assert reader.call('list_assets',{})['items'][0]['id']=='owned'
    from tests.test_worker_process import seed
    source,asset,_=seed(pg,1)
    history=reader.call('search_worker_events',{'task_id':source['id'],'asset_id':asset['id']})
    assert history['total']==1 and history['items'][0]['worker_provenance']['status']=='matched'
    from tests.test_todos import seed as todo_seed,payload,ACTOR
    from aegis import todos
    root,_=todo_seed(pg)
    shared=todos.create(pg,root['id'],payload(),ACTOR)
    assert reader.call('list_task_todos',{'id':root['id']})['items'][0]['id']==shared['id']
    assert reader.call('list_todo_history',{'id':root['id'],'todo_id':shared['id']})['total']==1
    assert PostgresStore(dsn,pg.schema).audit_integrity()['valid']
    with reader.connect() as db:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):db.execute('DELETE FROM records')
    with reader.connect() as db:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):db.execute('SELECT * FROM users')


@pytest.mark.parametrize('patch',[{'AEGIS_STORAGE_BACKEND':'unknown'},{'AEGIS_POSTGRES_SCHEMA':'missing'},
                                  {'AEGIS_POSTGRES_DSN':'host=127.0.0.1 port=1 password=DO-NOT-EXPOSE'},])
def test_native_reader_startup_errors_never_fallback_or_echo_credentials(stores,tmp_path,patch):
    _,pg=stores;folder=tmp_path/'unused'
    for module in ['aegis.mcp','aegis.cli.audit']:
        failed=run(pg,folder,module,input=json.dumps(message('list_assets'))+'\n',extra=patch)
        assert failed.returncode==2 and 'Traceback' not in failed.stderr and 'DO-NOT-EXPOSE' not in failed.stderr
        assert not folder.exists()
