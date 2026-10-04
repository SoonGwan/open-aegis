from concurrent.futures import ThreadPoolExecutor
import pytest
from tests.test_postgres_transfer import postgres,schema
from tests.test_postgres_store import stores
from tests.test_todos import seed,payload,ACTOR
from aegis import todos
from aegis.mcp import Reader,PostgresReader


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_shared_family_paging_idempotency_and_readonly_mcp(stores,backend,monkeypatch):
    store=stores[backend=='postgres'];root,child=seed(store)
    monkeypatch.setattr(store,'all',lambda *_:pytest.fail('Unbounded todos'))
    rows=[todos.create(store,child['id'],payload(title=f'Owned todo {i:02d}'),ACTOR) for i in range(30)]
    first=todos.page(store,root['id']);second=todos.page(store,child['id'],offset=25,snapshot=first['snapshot'])
    assert first['total']==30 and len(first['items'])==25 and len(second['items'])==5
    assert {r['id'] for r in first['items']}.isdisjoint(r['id'] for r in second['items'])
    assert todos.page(store,root['id'],search='todo 29')['total']==1
    changed=todos.update(store,root['id'],rows[0]['id'],{'expected_revision':1,'status':'done','resolution_note':'Manual review'},ACTOR)
    assert changed['revision']==2
    with pytest.raises(ValueError):todos.update(store,root['id'],rows[0]['id'],{'expected_revision':2,'resolution_note':''},ACTOR)
    assert store.get('todos',rows[0]['id'])==changed
    reopened=todos.update(store,child['id'],rows[0]['id'],{'expected_revision':2,'status':'open'},ACTOR)
    assert reopened['revision']==3 and reopened['resolution_note']==''
    before=store.audit_integrity()
    reader=PostgresReader(store._dsn,store.schema) if backend=='postgres' else Reader(store.path)
    assert reader.call('list_task_todos',{'id':child['id']})==todos.page(store,child['id'])
    assert reader.call('list_todo_history',{'id':root['id'],'todo_id':rows[0]['id']})['total']==3
    assert store.audit_integrity()==before and before['valid'] and store.count('traffic')==0


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_todo_concurrent_create_and_stale_update_serialize(stores,backend):
    store=stores[backend=='postgres'];root,child=seed(store);data=payload()
    from aegis.store import Store
    from aegis.postgres_store import PostgresStore
    other=PostgresStore(store._dsn,store.schema) if backend=='postgres' else Store(store.path)
    writers=(store,other)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a,b=list(pool.map(lambda index:todos.create(writers[index],(root['id'],child['id'])[index],data,ACTOR),(0,1)))
    assert a['id']==b['id'] and store.count('todos')==store.count('todo_history')==1
    def update(index):
        try:return todos.update(writers[index],root['id'],a['id'],{'expected_revision':1,'title':('First','Second')[index]},ACTOR)['revision']
        except todos.TodoConflict:return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(update,(0,1)))
    assert sorted(str(r) for r in results)==['2','conflict']
    assert store.count('todo_history')==2 and store.audit_integrity()['valid']


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_todo_atomic_rollback_after_record_writes(stores,backend,monkeypatch):
    store=stores[backend=='postgres'];root,_=seed(store);row=todos.create(store,root['id'],payload(),ACTOR)
    before=store.audit_integrity()
    def fail(*args,**kwargs):raise RuntimeError('Owned rollback probe after todo/history writes')
    monkeypatch.setattr(store,'event',fail)
    with pytest.raises(RuntimeError):todos.update(store,root['id'],row['id'],{'expected_revision':1,'title':'Must rollback'},ACTOR)
    assert store.get('todos',row['id'])==row and store.count('todo_history')==1 and store.audit_integrity()==before


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_audit_head_failure_rolls_back_todo_history_event_and_hash(stores,backend):
    store=stores[backend=='postgres'];root,_=seed(store);before=store.audit_integrity()
    if backend=='sqlite':
        import sqlite3
        with store.connect() as db:db.execute("CREATE TRIGGER fail_todo_head BEFORE UPDATE ON audit_state WHEN EXISTS(SELECT 1 FROM records WHERE kind='todos') AND EXISTS(SELECT 1 FROM event_hashes) BEGIN SELECT RAISE(ABORT,'Owned late audit rollback'); END")
        error=sqlite3.IntegrityError
    else:
        import psycopg
        from psycopg import sql
        name=sql.Identifier(store.schema)
        with store.transaction(write=True) as db:
            db.execute(sql.SQL('CREATE SEQUENCE {}.todo_head_probe').format(name))
            db.execute(sql.SQL("CREATE FUNCTION {}.fail_todo_head() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF EXISTS(SELECT 1 FROM records WHERE kind='todos') AND EXISTS(SELECT 1 FROM event_hashes) THEN PERFORM nextval((TG_TABLE_SCHEMA || '.todo_head_probe')::regclass); RAISE EXCEPTION 'Owned late audit rollback'; END IF; RETURN NEW; END $$").format(name))
            db.execute(sql.SQL('CREATE TRIGGER fail_todo_head BEFORE UPDATE ON {}.audit_state FOR EACH ROW EXECUTE FUNCTION {}.fail_todo_head()').format(name,name))
        error=psycopg.errors.RaiseException
    with pytest.raises(error):todos.create(store,root['id'],payload(),ACTOR)
    if backend=='postgres':
        with store.read_transaction() as db:assert db.execute('SELECT last_value,is_called FROM todo_head_probe').fetchone()=={'last_value':1,'is_called':True}
    assert store.count('todos')==store.count('todo_history')==0
    assert store.audit_integrity()==before


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_todo_assignment_requires_active_operator_and_preserves_snapshot(stores,backend):
    from aegis.auth import new_user
    store=stores[backend=='postgres'];root,_=seed(store)
    operator=store.add_user(new_user('todo-operator','Owned assignee','operator','owned-todo-password-only'))
    viewer=store.add_user(new_user('todo-viewer','Owned viewer','viewer','owned-todo-password-only'))
    row=todos.create(store,root['id'],payload(assignee_id=operator['id']),ACTOR)
    assert row['assignee_name']=='Owned assignee' and row['assignee_id']==operator['id']
    store.update_user(operator['id'],disabled=1,name='Changed profile')
    assert todos.page(store,root['id'])['items'][0]['assignee_name']=='Owned assignee'
    for user_id in (operator['id'],viewer['id']):
        with pytest.raises(ValueError):todos.create(store,root['id'],payload(assignee_id=user_id),ACTOR)
    cleared=todos.update(store,root['id'],row['id'],{'expected_revision':1,'assignee_id':None},ACTOR)
    assert cleared['revision']==2 and cleared['assignee_name'] is None
    assert store.count('todos')==1


@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_corrupt_todo_payload_id_cannot_overwrite_foreign_decision(stores,backend):
    import json
    store=stores[backend=='postgres'];root,_=seed(store)
    row=todos.create(store,root['id'],payload(),ACTOR)
    foreign=todos.create(store,root['id'],payload(title='Foreign decision'),ACTOR)
    corrupted={**row,'id':foreign['id']}
    if backend=='sqlite':
        with store.connect() as db:db.execute("UPDATE records SET data=? WHERE kind='todos' AND id=?",(json.dumps(corrupted),row['id']))
    else:
        with store.transaction(write=True) as db:db.execute("UPDATE records SET data=%s WHERE kind='todos' AND id=%s",(json.dumps(corrupted),row['id']))
    before=store.audit_integrity()
    with pytest.raises(todos.TodoConflict):todos.update(store,root['id'],row['id'],{'expected_revision':1,'title':'Wrong target'},ACTOR)
    assert store.get('todos',foreign['id'])==foreign and store.audit_integrity()==before
