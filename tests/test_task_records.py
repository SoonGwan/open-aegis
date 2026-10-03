import pytest
from tests.test_validation import client
from tests.test_identity import add, login


def populate(store, count=1050):
    store.put('tasks', {'id':'task','status':'completed','created_at':1,'scope_snapshot':[],'checks':[]})
    store.put_many([('findings',{'id':str(i),'title':f'Finding {i}','task_ids':['task'],
                               'evidence_ids':['proof'],'severity':'low','status':'open'}) for i in range(count)])
    store.put_many([('findings',{'id':'other-'+str(i),'title':'foreign','task_ids':['other']}) for i in range(50)])
    for i in range(count):
        store.event('task',f"기록 {i} %_ ' OR 1=1 --",detail={'index':i})
    store.event('other','foreign')


def test_task_detail_and_collections_are_bounded_complete_and_compact(client,monkeypatch):
    store=client.app.state.store
    populate(store)
    monkeypatch.setattr(store,'all',lambda *_:pytest.fail('Unbounded task detail read'))
    detail=client.get('/api/tasks/task').json()
    for collection in ('findings','events'):
        assert len(detail[collection])==25
        assert detail[collection+'_page']['total']==1050
        assert detail[collection+'_page']['has_more']
        last=client.get('/api/tasks/task/'+collection+'?offset=1025').json()
        assert len(last['items'])==25 and last['total']==1050 and not last['has_more']
    assert detail['events'][0]['detail']['index']==1049
    assert all('task_ids' not in f and f['task_count']==1 for f in detail['findings'])
    assert client.get('/api/tasks/task/events',params={'search':"%_ ' OR 1=1 --"}).json()['total']==1050
    assert client.get('/api/tasks/task/findings?search=foreign').json()['total']==0


@pytest.mark.parametrize('collection',['findings','events'])
def test_task_walk_new_insert_watermark_and_live_updates(client,collection):
    store=client.app.state.store
    populate(store,60)
    path='/api/tasks/task/'+collection
    first=client.get(path).json()
    if collection=='findings':
        store.put('findings',{'id':'new','task_ids':['task'],'title':'new'})
        store.patch('findings','34',title='updated')
    else:
        store.event('task','new')
    pages=[first]+[client.get(path,params={'offset':offset,'snapshot':first['snapshot']}).json() for offset in (25,50)]
    key='id' if collection=='findings' else 'seq'
    values=[item[key] for page in pages for item in page['items']]
    assert len(values)==len(set(values))==60 and all(page['total']==60 for page in pages)
    if collection=='findings':
        assert pages[1]['items'][0]['title']=='updated'
    else:
        assert all(item['message']!='new' for page in pages for item in page['items'])
    assert client.get(path).json()['total']==61


def test_task_page_bounds_auth_and_existing_message_route(client):
    populate(client.app.state.store,1)
    assert client.get('/api/tasks/task/messages').status_code==200
    assert client.get('/api/tasks/task/messages').json()==[]
    for collection in ('events','findings'):
        for query in ('limit=101','offset=-1','snapshot=-1','search='+'x'*201):
            assert client.get('/api/tasks/task/'+collection+'?'+query).status_code==422
        assert client.get('/api/tasks/missing/'+collection).status_code==404
    viewer=add(client,'viewer')
    with login(client.app,viewer['username']) as read:
        assert read.get('/api/tasks/task/findings').json()['total']==1
        assert read.get('/api/tasks/task/events').json()['total']==1
    client.post('/api/auth/logout')
    assert client.get('/api/tasks/task/events').status_code==401
