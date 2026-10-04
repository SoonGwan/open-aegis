"""Real continuation creation must preserve rounds and historical completion."""
from tests.test_validation import client, lab, finish
from tests.test_next_plan import completed


def followup(client, lab):
    original,path=completed(client,lab)
    proposal=client.get(path).json()
    child=client.post(path,json={'fingerprint':proposal['fingerprint']}).json()
    return original,proposal,child,path


def test_replan_followup_keeps_round_origin_and_accepted_lookup(client,lab):
    original,proposal,child,path=followup(client,lab)
    response=client.post('/api/tasks/'+child['id']+'/replan')
    assert response.status_code==200
    fresh=response.json()
    assert fresh.get('planning_round')==1
    assert fresh.get('followup_of')==original['id']
    assert fresh.get('followup_fingerprint')==proposal['fingerprint']
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).json()['id']==fresh['id']
    assert client.get(path).json()['accepted_task_id']==fresh['id']
    assert client.post('/api/tasks/'+fresh['id']+'/approve').status_code==200
    finish(client,fresh['id'])
    following=client.get('/api/tasks/'+fresh['id']+'/next-plan')
    assert following.status_code==200
    assert following.json()['reason']=='no_remaining_checks'
    assert lab[1].requests==['/','/']


def test_retry_followup_keeps_round_and_prior_completion(client,lab):
    original,proposal,child,path=followup(client,lab)
    # Failure fixture follows actual approval and executes only the owned loopback.
    engine=client.app.state.engine
    from aegis.runtime import ExecutionPolicy,OriginLimiter
    engine.policy=ExecutionPolicy(request_retries=0)
    engine.limiter=OriginLimiter(engine.policy)
    # Child was created with old policy: refresh its pending plan first.
    child=client.post('/api/tasks/'+child['id']+'/replan').json()
    lab[1].fault=True
    assert client.post('/api/tasks/'+child['id']+'/approve').status_code==200
    assert finish(client,child['id'])['task']['status']=='failed'
    lab[1].fault=False
    fresh=client.post('/api/tasks/'+child['id']+'/retry').json()
    assert fresh.get('planning_round')==1
    assert fresh.get('followup_of')==original['id']
    assert client.post('/api/tasks/'+fresh['id']+'/approve').status_code==200
    finish(client,fresh['id'])
    following=client.get('/api/tasks/'+fresh['id']+'/next-plan')
    assert following.status_code==200
    assert following.json()['reason']=='no_remaining_checks'


def test_multiple_replacements_resolve_one_current_pending_attempt(client,lab):
    original,proposal,child,path=followup(client,lab)
    first=client.post('/api/tasks/'+child['id']+'/replan').json()
    second=client.post('/api/tasks/'+first['id']+'/replan').json()
    assert second['planning_round']==1 and second['followup_of']==original['id']
    assert client.post('/api/tasks/'+child['id']+'/replan').json()['id']==second['id']
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).json()['id']==second['id']
    assert client.get(path).json()['accepted_task_id']==second['id']
    assert client.app.state.store.get('tasks',original['id'])['next_plan_id']==child['id']
    assert lab[1].requests==['/']


def test_retry_and_next_plan_race_creates_one_continuation(client,lab):
    from concurrent.futures import ThreadPoolExecutor
    from aegis.runtime import ExecutionPolicy,OriginLimiter
    from tests.test_validation import register,task
    engine=client.app.state.engine
    engine.policy=ExecutionPolicy(request_retries=0);engine.limiter=OriginLimiter(engine.policy)
    lab[1].fault=True
    source=task(client,register(client,lab[0]),['security_headers'])
    client.post('/api/tasks/'+source['id']+'/approve')
    assert finish(client,source['id'])['task']['status']=='failed'
    path='/api/tasks/'+source['id']
    proposal=client.get(path+'/next-plan').json()
    def action(kind):return client.post(path+kind,json={'fingerprint':proposal['fingerprint']} if kind=='/next-plan' else None)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(action,['/retry','/next-plan']))
    assert sorted(r.status_code for r in replies)==[200,409]
    stored=client.app.state.store.get('tasks',source['id'])
    assert bool(stored.get('next_plan_id')) != bool(stored.get('retry_successor'))
    assert client.app.state.store.count('tasks')==2
    assert lab[1].requests==['/']
    lookup=client.get(path+'/next-plan').json()
    assert not lookup['available'] and lookup['reason']=='already_accepted'
    assert lookup['accepted_kind'] in ('retry','followup')


def test_finished_retry_remains_idempotent_and_root_history_is_kept(client,lab):
    from tests.test_validation import register,task
    from aegis.runtime import ExecutionPolicy,OriginLimiter
    engine=client.app.state.engine
    engine.policy=ExecutionPolicy(request_retries=0);engine.limiter=OriginLimiter(engine.policy)
    lab[1].fault=True
    source=task(client,register(client,lab[0]),['security_headers'])
    client.post('/api/tasks/'+source['id']+'/approve');finish(client,source['id'])
    lab[1].fault=False
    path='/api/tasks/'+source['id']+'/retry'
    fresh=client.post(path).json()
    assert fresh['planning_round']==0 and fresh['retry_of']==source['id']
    client.post('/api/tasks/'+fresh['id']+'/approve');finish(client,fresh['id'])
    assert client.post(path).json()['id']==fresh['id']
    p=client.get('/api/tasks/'+fresh['id']+'/next-plan').json()
    assert p['available'] and p['planning_round']==1 and p['history_count']==2
    assert p['basis']['retry_checks']==[]
    assert lab[1].requests==['/','/']


def test_old_root_attempt_adopts_active_preupgrade_retry(client,lab):
    from tests.test_validation import register,task
    store=client.app.state.store
    source=task(client,register(client,lab[0]),['security_headers'])
    store.patch('tasks',source['id'],status='interrupted')
    first=client.post('/api/tasks/'+source['id']+'/retry').json()
    # Simulate the old format which had only a backward retry_of link.
    row=store.get('tasks',source['id']);row.pop('retry_successor');store.put('tasks',row)
    assert client.post('/api/tasks/'+source['id']+'/retry').json()['id']==first['id']
    assert store.get('tasks',source['id'])['retry_successor']==first['id']
    assert store.count('tasks')==2 and lab[1].requests==[]


def test_history_cap_bounds_unapproved_replacements_without_resetting_round(client,lab):
    original,proposal,child,path=followup(client,lab)
    current=child
    # Original root plus child count as two records; exactly30 replacements fit.
    for _ in range(30):
        r=client.post('/api/tasks/'+current['id']+'/replan')
        assert r.status_code==200,r.text
        current=r.json()
        assert current['planning_round']==1
    assert client.post('/api/tasks/'+current['id']+'/replan').status_code==409
    assert client.app.state.store.count('tasks')==32
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).json()['id']==current['id']
    assert lab[1].requests==['/']
    assert client.post('/api/tasks/'+current['id']+'/approve').status_code==200
    finish(client,current['id'])
    result=client.get('/api/tasks/'+current['id']+'/next-plan')
    assert result.status_code==200 and result.json()['reason']=='history_limit'
    assert not result.json()['available']
    assert lab[1].requests==['/','/']


def test_retry_source_pointer_failure_rolls_back_child_and_coverage(client,lab):
    import sqlite3,pytest
    from tests.test_validation import register,task
    store=client.app.state.store
    original=task(client,register(client,lab[0]),['security_headers'])
    store.patch('tasks',original['id'],status='interrupted')
    before=store.get('tasks',original['id'])
    with store.connect() as db:
        db.execute("CREATE TRIGGER reject_retry BEFORE INSERT ON records WHEN NEW.kind='tasks' AND json_extract(NEW.data,'$.retry_successor') IS NOT NULL BEGIN SELECT RAISE(ABORT,'retry rollback'); END")
    with pytest.raises(sqlite3.IntegrityError,match='retry rollback'):
        client.post('/api/tasks/'+original['id']+'/retry')
    assert store.get('tasks',original['id'])==before
    assert store.count('tasks')==1 and store.count('coverage')==1
    assert lab[1].requests==[]


def test_corrupt_forward_reference_does_not_redirect_or_create_work(client,lab):
    original,proposal,child,path=followup(client,lab)
    store=client.app.state.store
    store.patch('tasks',original['id'],next_plan_id='missing')
    assert client.get(path).status_code==409
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).status_code==409
    assert store.count('tasks')==2 and lab[1].requests==['/']


def test_conflicting_forward_links_are_refused(client,lab):
    original,proposal,child,path=followup(client,lab)
    store=client.app.state.store
    store.patch('tasks',original['id'],retry_successor=child['id'])
    assert client.get(path).status_code==409
    assert client.post(path,json={'fingerprint':proposal['fingerprint']}).status_code==409
    assert store.count('tasks')==2 and lab[1].requests==['/']


def test_replan_refuses_mismatched_storage_key_without_replacing_another_task(client,lab):
    from tests.test_validation import register,task
    from aegis.store import Store
    store=client.app.state.store
    asset=register(client,lab[0])
    original=task(client,asset,['security_headers'])
    other=task(client,asset,['security_headers'])
    with store.write_transaction() as db:
        if isinstance(store,Store):
            db.execute("UPDATE records SET data=json_set(data,'$.id',?) WHERE kind='tasks' AND id=?",(other['id'],original['id']))
        else:
            db.execute("UPDATE records SET data=jsonb_set(data::jsonb,'{id}',to_jsonb(%s::text))::text WHERE kind='tasks' AND id=%s",(other['id'],original['id']))
    corrupted=store.get('tasks',original['id'])
    assert client.post('/api/tasks/'+original['id']+'/replan').status_code==409
    assert store.get('tasks',other['id'])==other
    assert store.get('tasks',original['id'])==corrupted
    assert store.count('tasks')==2 and lab[1].requests==[]
