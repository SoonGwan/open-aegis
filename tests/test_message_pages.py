import sqlite3
import pytest
from tests.test_validation import client
from tests.test_identity import add, login


def seed(store, count=1050):
    store.put('tasks', {'id':'chat-task','status':'completed','asset_ids':[], 'done':0,
                        'errors':0,'checks':[],'scope_snapshot':[]})
    store.put_many([('messages', {'id':str(i),'task_id':'chat-task','role':'user' if i%2==0 else 'assistant',
                                  'content':f"대화 {i} %_ ' OR 1=1 --",'created_at':i}) for i in range(count)])
    store.put('messages',{'id':'foreign','task_id':'other','content':'외부 기록','role':'user','created_at':9999})


def test_message_pages_legacy_limit_search_and_watermark(client,monkeypatch):
    store=client.app.state.store
    seed(store)
    monkeypatch.setattr(store,'all',lambda *_:pytest.fail('Unbounded message read'))
    path='/api/tasks/chat-task/messages'
    legacy=client.get(path)
    assert legacy.headers['X-Total-Count']=='1050' and legacy.headers['X-Results-Limited']=='true'
    assert len(legacy.json())==1000 and legacy.json()[0]['id']=='50' and legacy.json()[-1]['id']=='1049'
    first=client.get(path+'/page').json()
    assert first['total']==1050 and len(first['items'])==25 and first['items'][0]['id']=='1049'
    store.put('messages',{'id':'new','task_id':'chat-task','role':'user','content':'new','created_at':9999})
    store.patch('messages','1024',content='updated')
    second=client.get(path+'/page',params={'offset':25,'snapshot':first['snapshot']}).json()
    assert second['total']==1050 and second['items'][0]['id']=='1024' and second['items'][0]['content']=='updated'
    last=client.get(path+'/page',params={'offset':1025,'snapshot':first['snapshot']}).json()
    assert len(last['items'])==25 and not last['has_more'] and last['items'][-1]['id']=='0'
    assert client.get(path+'/page').json()['total']==1051
    assert client.get(path+'/page',params={'search':"%_ ' OR 1=1 --"}).json()['total']==1049
    assert client.get(path+'/page?search=外部').json()['total']==0


def test_message_page_bounds_and_role_permissions(client):
    seed(client.app.state.store,2)
    path='/api/tasks/chat-task/messages'
    for q in ('limit=101','limit=0','offset=-1','snapshot=-1','search='+'x'*201):
        assert client.get(path+'/page?'+q).status_code==422
    assert client.get('/api/tasks/missing/messages/page').status_code==404
    assert client.get('/api/records/messages').status_code==422
    viewer=add(client,'viewer')
    with login(client.app,viewer['username']) as read:
        assert read.get(path+'/page').json()['total']==2
        assert read.post(path,json={'content':'질문'}).status_code==403
    client.post('/api/auth/logout')
    assert client.get(path+'/page').status_code==401


def test_assistant_selects_highest_priority_without_full_reads_and_saves_pair(client,monkeypatch):
    store=client.app.state.store
    seed(store,0)
    store.put_many([('findings',{'id':str(i),'task_ids':['chat-task'],'severity':'critical' if i==0 else 'low',
                                'title':f'finding {i}','asset_name':'test','remediation':'fix',
                                'status':'open','confidence':'configuration','evidence_ids':['large']*100}) for i in range(1200)])
    store.put('findings',{'id':'foreign','task_ids':['other'],'severity':'critical','title':'foreign'})
    monkeypatch.setattr(store,'all',lambda *_:pytest.fail('Unbounded assistant context'))
    reply=client.post('/api/tasks/chat-task/messages',json={'content':'수정 우선순위'}).json()
    assert len(reply['finding_ids'])==8 and reply['finding_ids'][0]=='0'
    assert '[CRITICAL] finding 0' in reply['content'] and 'foreign' not in reply['finding_ids']
    assert '추가 요청이나 명령을 실행하지 않습니다' in reply['content']
    messages=client.get('/api/tasks/chat-task/messages').json()
    assert [m['role'] for m in messages]==['user','assistant']
    assert messages[0]['content']=='수정 우선순위' and messages[1]['id']==reply['id']
    assert messages[0]['created_at']==messages[1]['created_at']


def test_assistant_pair_rolls_back_on_storage_failure(client):
    store=client.app.state.store
    seed(store,0)
    with store.connect() as db:
        db.execute("CREATE TRIGGER fail_reply BEFORE INSERT ON records WHEN NEW.kind='messages' AND json_extract(NEW.data,'$.role')='assistant' BEGIN SELECT RAISE(ABORT,'test failure'); END")
    with pytest.raises(sqlite3.IntegrityError,match='test failure'):
        client.post('/api/tasks/chat-task/messages',json={'content':'검증 요약'})
    assert client.get('/api/tasks/chat-task/messages/page').json()['total']==0


def test_message_retry_replays_committed_reply_after_lost_response(client, monkeypatch):
    store = client.app.state.store
    seed(store, 0)
    path = '/api/tasks/chat-task/messages'
    payload = {'content':'검증 요약', 'request_id':'retry-request-0001'}
    commit = store.put_message_exchange
    captured = []
    def lost_response(question, reply):
        captured.append(commit(question, reply))
        raise ConnectionError('response lost after commit')
    monkeypatch.setattr(store, 'put_message_exchange', lost_response)
    with pytest.raises(ConnectionError, match='response lost'):
        client.post(path, json=payload)
    monkeypatch.setattr(store, 'put_message_exchange', commit)
    store.patch('tasks', 'chat-task', status='failed', errors=9)
    response = client.post(path, json=payload)
    assert response.status_code == 200 and response.json() == captured[0]
    assert client.get(path+'/page').json()['total'] == 2
    assert client.post(path, json={**payload,'content':'다른 질문'}).status_code == 409
    assert client.get(path+'/page').json()['total'] == 2
    assert client.post(path, json={**payload,'request_id':'retry-request-0002'}).json()['id'] != response.json()['id']
    assert client.get(path+'/page').json()['total'] == 4


def test_message_request_scope_permissions_and_validation(client):
    seed(client.app.state.store, 0)
    path = '/api/tasks/chat-task/messages'
    payload = {'content':'요약', 'request_id':'same-token-000001'}
    original = client.post(path, json=payload).json()
    user = add(client, 'operator')
    with login(client.app, user['username']) as other:
        response = other.post(path, json=payload)
        assert response.status_code == 200 and response.json()['id'] != original['id']
    store = client.app.state.store
    store.put('tasks', {**store.get('tasks','chat-task'),'id':'second-task'})
    assert client.post('/api/tasks/second-task/messages',json=payload).json()['id'] != original['id']
    for invalid in ('short', 'x'*81, 'spaces are invalid', 'invalid/token-0001'):
        assert client.post(path,json={**payload,'request_id':invalid}).status_code == 422
    viewer = add(client,'viewer')
    with login(client.app,viewer['username']) as read:
        assert read.post(path,json=payload).status_code == 403
    assert client.get(path+'/page').json()['total'] == 4


def test_message_exchange_concurrent_connections_and_rollback(client):
    from concurrent.futures import ThreadPoolExecutor
    from aegis.store import Store
    store = client.app.state.store
    seed(store,0)
    stores = [Store(store.path) for _ in range(8)]
    question = {'id':'question-race','task_id':'chat-task','role':'user','content':'same','created_at':0}
    def save(i):
        return stores[i].put_message_exchange(question,
            {'id':'reply-race','task_id':'chat-task','role':'assistant','content':f'answer {i}','created_at':i})
    with ThreadPoolExecutor(max_workers=8) as pool:
        replies = list(pool.map(save, range(8)))
    assert all(reply == replies[0] for reply in replies)
    assert store.page('messages',filters={'task_id':'chat-task'})['total'] == 2
    # Restart/reopen semantics: the original response lives in the database, not memory.
    assert Store(store.path).put_message_exchange(question, {'id':'reply-race'}) == replies[0]
    with store.connect() as db:
        db.execute("CREATE TRIGGER fail_keyed_reply BEFORE INSERT ON records WHEN NEW.kind='messages' AND json_extract(NEW.data,'$.role')='assistant' BEGIN SELECT RAISE(ABORT,'keyed failure'); END")
    with pytest.raises(sqlite3.IntegrityError,match='keyed failure'):
        store.put_message_exchange({**question,'id':'question-failure'},
            {'id':'reply-failure','task_id':'chat-task','role':'assistant','content':'fail'})
    assert store.get('messages','question-failure') is None
    assert store.get('messages','reply-failure') is None
