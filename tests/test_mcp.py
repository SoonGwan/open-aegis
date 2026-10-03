import json
from aegis.mcp import Reader, dispatch
from aegis.store import Store


def test_mcp_only_exposes_readonly_records(tmp_path):
    store=Store(tmp_path/'aegis.db')
    store.put('assets',{'id':'asset','name':'Fixture','url':'https://example.invalid/'})
    store.put('settings',{'id':'auth','password_hash':'DO-NOT-EXPOSE'})
    reader=Reader(store.path)
    catalog=dispatch({'jsonrpc':'2.0','id':1,'method':'tools/list'},reader)
    assert all(t['annotations']['readOnlyHint'] for t in catalog['result']['tools'])
    result=dispatch({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'list_assets','arguments':{}}},reader)
    assert json.loads(result['result']['content'][0]['text'])['items'][0]['id'] == 'asset'
    assert 'DO-NOT-EXPOSE' not in json.dumps(result)
    denied=dispatch({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'run_command','arguments':{'command':'anything'}}},reader)
    assert denied['result']['isError']
    assert dispatch({'jsonrpc':'2.0','method':'notifications/initialized'},reader) is None
    assert dispatch({'jsonrpc':'2.0','id':4,'method':'unknown'},reader)['error']['code'] == -32601


def test_mcp_handles_encoded_database_filename_without_mutation(tmp_path):
    path = tmp_path/'자료 ?reader.db'
    store = Store(path)
    store.put('assets', {'id':'fixture','name':'Encoded path'})
    before = path.read_bytes()
    assert Reader(path).call('list_assets', {})['items'][0]['name'] == 'Encoded path'
    assert path.read_bytes() == before


def test_mcp_task_reports_missing_legacy_check_without_writing(tmp_path, monkeypatch):
    store = Store(tmp_path/'coverage.db')
    store.put('tasks', {'id':'t', 'status':'completed', 'created_at':1,
                        'scope_snapshot':[{'id':'asset'}], 'checks':['security_headers']})
    reader = Reader(store.path)
    before = store.path.read_bytes()
    monkeypatch.setattr(reader, 'all', lambda *_: (_ for _ in ()).throw(AssertionError('Unbounded read')), raising=False)
    result = reader.call('get_task', {'id':'t'})
    assert result['coverage'][0]['status'] == 'not_recorded'
    assert store.get('coverage', result['coverage'][0]['id']) is None
    assert store.path.read_bytes() == before
