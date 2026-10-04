import json
import os
import subprocess
import sys
import sqlite3

import pytest
from aegis.mcp import Reader, dispatch, MAX_TOOL_BYTES
from aegis.store import Store
from tests.test_finding_records import populate


def test_mcp_pages_compact_findings_and_provenance_without_writes(tmp_path, monkeypatch):
    store = Store(tmp_path / 'workspace.db')
    populate(store, 1200)
    store.put_many([('assets', {'id':str(i),'name':f'Asset {i}'}) for i in range(1050)])
    store.put('evidence', {'id':'foreign','asset_id':'other','task_id':'task-a','check':'security_headers','fingerprint':'fingerprint-a'})
    store.patch('findings','finding-a',evidence_ids=[f'proof-{i}' for i in range(1200)] + ['foreign'])
    reader = Reader(store.path)
    before = store.path.read_bytes()
    monkeypatch.setattr(reader,'all',lambda *_: pytest.fail('Unbounded MCP read'),raising=False)
    first = reader.call('list_assets',{})
    assert first['total']==1050 and len(first['items'])==25 and first['has_more']
    assert reader.call('list_assets',{'offset':1025,'snapshot':first['snapshot']})['has_more'] is False
    finding = reader.call('list_findings',{})['items'][0]
    assert 'evidence_ids' not in finding and 'task_ids' not in finding
    assert finding['evidence_reference_count']==1201 and finding['task_count']==1 and finding['related_ids_omitted']
    detail = reader.call('get_finding',{'id':'finding-a'})
    assert len(detail['evidence'])==len(detail['retests'])==25
    assert detail['evidence_page']['total']==1200
    assert reader.call('list_finding_evidence',{'id':'finding-a','offset':1175})['total']==1200
    assert reader.call('list_finding_retests',{'id':'finding-a','search':"%_ ' OR 1=1 --"})['total']==1200
    with reader.connect() as db:
        with pytest.raises(sqlite3.OperationalError, match='readonly'):
            db.execute("DELETE FROM records")
    assert store.path.read_bytes()==before


@pytest.mark.parametrize('args', [{'limit':True},{'limit':101},{'offset':-1},{'snapshot':None},
                                 {'snapshot':9007199254740992},{'search':'x'*201},
                                 {'archived':'false'},{'sql':'SELECT 1'}])
def test_mcp_rejects_invalid_values_without_echoing_input(tmp_path,args):
    reader=Reader(tmp_path/'missing.db')
    result=dispatch({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'list_assets','arguments':args}},reader)
    assert result['result']['isError']
    assert result['result']['content'][0]['text']=='Tool unavailable, record missing, or arguments invalid.'


def test_events_latest_pages_keep_new_events_out_of_walk(tmp_path):
    store=Store(tmp_path/'events.db')
    store.put('tasks',{'id':'task','status':'completed','created_at':1,'scope_snapshot':[],'checks':[]})
    for i in range(60):
        store.event('task',str(i))
    reader=Reader(store.path)
    first=reader.call('list_task_events',{'id':'task'})
    store.event('task','new')
    second=reader.call('list_task_events',{'id':'task','offset':25,'snapshot':first['snapshot']})
    assert first['items'][0]['message']=='59' and second['items'][0]['message']=='34'
    assert second['total']==60
    detail=reader.call('get_task',{'id':'task'})
    assert len(detail['events'])==25 and detail['events_page']['total']==61
    assert detail['events'][0]['message']=='new'


def test_stdio_real_process_catalog_pages_bounds_and_no_mutation(tmp_path):
    store=Store(tmp_path/'aegis.db')
    store.put('assets',{'id':'asset','name':'Fixture'})
    before=store.path.read_bytes()
    messages=[{'jsonrpc':'2.0','id':1,'method':'initialize'},
              {'jsonrpc':'2.0','id':2,'method':'tools/list'},
              {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'list_assets','arguments':{}}},
              [{'jsonrpc':'2.0','id':i,'method':'ping'} for i in range(17)]]
    result=subprocess.run([sys.executable,'-m','aegis.mcp'],input='\n'.join(json.dumps(m) for m in messages)+'\n',
                          text=True,capture_output=True,timeout=5,env={**os.environ,'AEGIS_DATA_DIR':str(tmp_path)})
    assert result.returncode==0 and not result.stderr
    output=[json.loads(line) for line in result.stdout.splitlines()]
    assert output[0]['result']['protocolVersion']=='2025-03-26'
    names={tool['name'] for tool in output[1]['result']['tools']}
    assert names=={'list_assets','list_findings','get_task','get_finding','list_finding_evidence','list_finding_retests','list_task_observations','list_task_events','get_worker','list_worker_events','list_worker_observations'}
    assert json.loads(output[2]['result']['content'][0]['text'])['total']==1
    assert output[3]['error']['code']==-32700
    assert store.path.read_bytes()==before


def test_mcp_oversized_tool_result_is_rejected(tmp_path):
    store=Store(tmp_path/'large.db')
    store.put('assets',{'id':'asset','name':'x'*(MAX_TOOL_BYTES+1)})
    result=dispatch({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'list_assets','arguments':{}}},Reader(store.path))
    assert result['result']['isError']
    assert len(json.dumps(result))<512
