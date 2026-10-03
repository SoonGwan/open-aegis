"""Human decisions must survive repeat observations and concurrent approved retests."""
from concurrent.futures import ThreadPoolExecutor
from tests.test_validation import client, lab, register, task, finish
from tests.test_identity import add, login


def observe(client, asset):
    plan=task(client,asset,['security_headers'])
    client.post('/api/tasks/'+plan['id']+'/approve')
    result=finish(client,plan['id'])
    return next(item for item in result['findings'] if item['code']=='missing-nosniff')


def patch(client, finding, **changes):
    return client.patch('/api/findings/'+finding['id'],json={'expected_revision':finding.get('triage_revision',1),**changes})


def test_history_search_is_scoped_literal_paged_and_authorized(client, monkeypatch):
    store = client.app.state.store
    store.put('findings', {'id': 'history-search'})
    literal = "%_ ' OR 1=1 --"
    def entry(index, finding_id='history-search'):
        return {'id': f'entry-{index}', 'finding_id': finding_id, 'action': 'triage',
                'actor': {'name': '합성 작성자', 'username': 'history_reviewer'},
                'reason': f'{literal} 검토 {index}', 'changes': {}, 'created_at': index}
    store.put_many([('finding_history', entry(i)) for i in range(60)] +
                   [('finding_history', entry(999, 'foreign'))])
    monkeypatch.setattr(store, 'all', lambda *_: (_ for _ in ()).throw(AssertionError('Unbounded history read')))
    path = '/api/findings/history-search/history'
    first = client.get(path, params={'search': literal}).json()
    assert first['total'] == 60 and len(first['items']) == 25 and first['has_more']
    assert {x['finding_id'] for x in first['items']} == {'history-search'}
    store.put('finding_history', entry(60))
    second = client.get(path, params={'search': literal, 'offset': 25, 'snapshot': first['snapshot']}).json()
    assert second['total'] == 60 and len(second['items']) == 25
    assert not {x['id'] for x in first['items']} & {x['id'] for x in second['items']}
    for text in ('합성 작성자', 'HISTORY_REVIEWER', 'triage', literal):
        assert client.get(path, params={'search': text}).json()['total'] == 61
    assert client.get(path, params={'search': 'no match'}).json()['total'] == 0
    assert client.get(path, params={'search': 'x'*201}).status_code == 422
    assert client.get('/api/findings/missing/history').status_code == 404
    viewer = add(client, 'viewer')
    with login(client.app, viewer['username']) as read:
        assert read.get(path, params={'search': literal}).json()['total'] == 61
    client.post('/api/auth/logout')
    assert client.get(path).status_code == 401


def test_reason_assignment_revision_and_actor_history(client,lab):
    asset=register(client,lab[0])
    finding=observe(client,asset)
    unchanged=patch(client,finding,status='open',assignee_id=None,acceptance_reason='',resolution_reason='').json()
    assert unchanged.get('triage_revision',1)==1
    assert client.get('/api/findings/'+finding['id']+'/history').json()['total']==1
    operator=add(client,'operator')
    viewer=add(client,'viewer')
    assert patch(client,finding,status='accepted').status_code==422
    assert patch(client,finding,status='resolved').status_code==422
    assert patch(client,finding,assignee_id=viewer['id']).status_code==422
    response=patch(client,finding,status='accepted',acceptance_reason='  Internal policy reviewed  ',assignee_id=operator['id'])
    assert response.status_code==200
    after=response.json()
    assert after['status']=='accepted' and after['assignee_name']=='operator'
    assert after['acceptance_reason']=='Internal policy reviewed' and after['triage_revision']==2
    entries=client.get('/api/findings/'+finding['id']+'/history').json()
    assert entries['total']==2 and entries['items'][0]['action']=='triage'
    assert entries['items'][0]['actor']['username']=='admin'
    assert 'password_hash' not in str(entries) and 'salt' not in str(entries)
    assert patch(client,finding,status='open').status_code==409
    assert patch(client,after,status='accepted',acceptance_reason='Internal policy reviewed',assignee_id=operator['id']).json()['triage_revision']==2
    assert client.get('/api/findings/'+finding['id']+'/history').json()['total']==2
    with login(client.app,viewer['username']) as read:
        assert read.get('/api/findings/'+finding['id']+'/history').status_code==200
        assert read.get('/api/assignees').status_code==200
        assert patch(read,after,status='open').status_code==403
    ids={item['id'] for item in client.get('/api/assignees').json()['items']}
    assert operator['id'] in ids and viewer['id'] not in ids
    client.patch('/api/users/'+operator['id'],json={'disabled':True})
    assert operator['id'] not in {item['id'] for item in client.get('/api/assignees').json()['items']}
    assert patch(client,after,assignee_id=None).json()['assignee_name']==''


def test_accepted_decision_survives_scan_and_reproduced_retest(client,lab):
    asset=register(client,lab[0])
    finding=observe(client,asset)
    accepted=patch(client,finding,status='accepted',acceptance_reason='Reviewed compensating control').json()
    again=observe(client,asset)
    assert again['id']==finding['id'] and again['status']=='accepted'
    assert again['triage_revision']==accepted['triage_revision'] and again['acceptance_reason']==accepted['acceptance_reason']
    retest=client.post('/api/findings/'+finding['id']+'/retest').json()
    client.post('/api/tasks/'+retest['id']+'/approve')
    finish(client,retest['id'])
    detail=client.get('/api/findings/'+finding['id']).json()
    assert detail['finding']['status']=='accepted'
    assert detail['retests'][0]['conclusion']=='reproduced' and detail['retests'][0]['triage_effect']=='unchanged'
    assert len(detail['evidence'])==3


def test_positive_new_scan_reopens_resolved_but_does_not_erase_reason_owner(client,lab):
    asset=register(client,lab[0])
    finding=observe(client,asset)
    owner=add(client,'operator')
    resolved=patch(client,finding,status='resolved',resolution_reason='Deployment fixed',assignee_id=owner['id']).json()
    reopened=observe(client,asset)
    assert reopened['status']=='open' and reopened['triage_revision']==resolved['triage_revision']+1
    assert reopened['assignee_id']==owner['id'] and reopened['resolution_reason']=='Deployment fixed'
    entries=client.get('/api/findings/'+finding['id']+'/history').json()['items']
    assert entries[0]['action']=='reopened' and entries[0]['actor']['kind']=='system'


def test_retest_result_is_kept_but_later_human_decision_is_not_overwritten(client,lab):
    url,handler=lab
    asset=register(client,url)
    finding=observe(client,asset)
    retest=client.post('/api/findings/'+finding['id']+'/retest').json()
    accepted=patch(client,finding,status='accepted',acceptance_reason='Decision made after plan').json()
    handler.hardened=True
    client.post('/api/tasks/'+retest['id']+'/approve')
    finish(client,retest['id'])
    detail=client.get('/api/findings/'+finding['id']).json()
    assert detail['finding']['status']=='accepted' and detail['finding']['triage_revision']==accepted['triage_revision']
    assert detail['retests'][0]['conclusion']=='resolved' and detail['retests'][0]['triage_effect']=='conflict'
    current=client.post('/api/findings/'+finding['id']+'/retest').json()
    client.post('/api/tasks/'+current['id']+'/approve')
    finish(client,current['id'])
    latest=client.get('/api/findings/'+finding['id']).json()
    assert latest['finding']['status']=='resolved' and latest['retests'][0]['triage_effect']=='changed'


def test_two_human_updates_from_same_revision_only_one_succeeds(client,lab):
    asset=register(client,lab[0])
    finding=observe(client,asset)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda reason:patch(client,finding,status='accepted',acceptance_reason=reason).status_code,['First','Second']))
    assert sorted(results)==[200,409]
    assert client.get('/api/findings/'+finding['id']+'/history').json()['total']==2


def test_retest_creation_is_idempotent_under_concurrent_requests(client,lab):
    asset=register(client,lab[0])
    finding=observe(client,asset)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _:client.post('/api/findings/'+finding['id']+'/retest'),range(2)))
    assert all(response.status_code==200 for response in responses)
    assert len({response.json()['id'] for response in responses})==1


def test_history_pagination_validation_and_export(client,lab):
    finding=observe(client,register(client,lab[0]))
    path='/api/findings/'+finding['id']
    assert client.patch(path,json={'status':'open'}).status_code==422
    assert patch(client,finding,status=None).status_code==422
    assert patch(client,finding,acceptance_reason='x'*4001).status_code==422
    for index in range(28):
        finding=patch(client,finding,status='accepted',acceptance_reason=f'Review {index}').json()
    first=client.get(path+'/history?limit=25').json()
    assert first['total']==29 and len(first['items'])==25 and first['has_more']
    finding=patch(client,finding,acceptance_reason='After snapshot').json()
    second=client.get(path+f"/history?limit=25&offset=25&snapshot={first['snapshot']}").json()
    assert second['total']==29 and len(second['items'])==4
    assert not ({v['id'] for v in first['items']} & {v['id'] for v in second['items']})
    export=client.get('/api/reports/export?format=json').json()
    assert len([entry for entry in export['finding_history'] if entry['finding_id']==finding['id']])==30
    assert 'After snapshot' in client.get('/api/reports/export?format=markdown').text


def test_observation_from_earlier_approved_plan_preserves_later_resolution(client,lab):
    from aegis.findings import record_observation
    from aegis.store_util import now
    asset=register(client,lab[0]); finding=observe(client,asset)
    earlier={'id':'earlier-approved-task','created_at':now()-10,'approved_at':now()-5}
    resolved=patch(client,finding,status='resolved',resolution_reason='Later human decision').json()
    store=client.app.state.store
    item={key:finding[key] for key in ('check','code','title','severity','confidence','remediation','evidence')}
    observed,proof,entry=record_observation(store,earlier,asset,item)
    assert observed['status']=='resolved' and observed['triage_revision']==resolved['triage_revision']
    assert proof['id'] in observed['evidence_ids'] and entry['action']=='observed'
