from tests.test_validation import client
from aegis.store import compact_finding


def seed(store):
    finding={'id':'large','title':'큰 이력','status':'open','severity':'low','triage_revision':1,
             'asset_id':'asset','task_ids':['task']*10000,'evidence_ids':['proof']*10000}
    store.put('findings',finding)
    return finding


def test_http_reads_omit_related_arrays_without_changing_stored_history(client):
    store=client.app.state.store
    original=seed(store)
    responses=[client.get('/api/records/findings?task_id=task').json()['items'][0],
               client.get('/api/overview').json()['findings'][0],
               client.get('/api/findings').json()[0],
               client.get('/api/findings/large').json()['finding']]
    for record in responses:
        assert 'task_ids' not in record and 'evidence_ids' not in record
        assert record['task_count']==record['evidence_reference_count']==10000
        assert record['related_ids_omitted'] is True
    response=client.get('/api/findings/large')
    assert len(response.content)<2000
    assert store.get('findings','large')==original


def test_triage_compact_response_preserves_associations_and_revision(client):
    store=client.app.state.store
    original=seed(store)
    response=client.patch('/api/findings/large',json={'expected_revision':1,'status':'accepted','acceptance_reason':'조치 검수'})
    assert response.status_code==200
    result=response.json()
    assert result['triage_revision']==2 and result['evidence_reference_count']==10000
    assert 'evidence_ids' not in result
    saved=store.get('findings','large')
    assert saved['task_ids']==original['task_ids'] and saved['evidence_ids']==original['evidence_ids']
    assert saved['status']=='accepted'


def test_compact_decision_is_a_non_mutating_snapshot():
    committed={'id':'finding','status':'accepted','triage_revision':2,'task_ids':['task'],'evidence_ids':['proof']}
    result=compact_finding(committed)
    assert result['status']=='accepted' and result['triage_revision']==2
    assert committed['task_ids']==['task'] and committed['evidence_ids']==['proof']
