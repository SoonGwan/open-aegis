"""Coverage must explain missing proof and never equate one completed tool with 100%."""
import threading
from aegis.coverage import latest_summary, slot, task_rows
from aegis.store import Store
from aegis.engine import Engine
from tests.test_validation import client, lab, register, task, finish


def summary(client):
    return client.get('/api/overview').json()['coverage_summary']


def test_full_catalog_denominator_and_skipped_rule(client, lab):
    url, handler = lab
    asset = register(client, url)
    plan = client.post('/api/tasks', json={'name': 'Whole catalog', 'asset_ids': [asset['id']]}).json()
    pending = client.get('/api/tasks/' + plan['id']).json()
    assert len(pending['coverage']) == 6
    assert {row['status'] for row in pending['coverage']} == {'not_started'}
    assert handler.requests == []
    assert summary(client)['counts']['not_started'] == 6
    client.post('/api/tasks/' + plan['id'] + '/approve')
    result = finish(client, plan['id'])
    counts = summary(client)
    assert counts['expected'] == 6 and counts['completed'] == 5 and counts['percent'] == 83
    assert counts['counts']['skipped'] == 1
    assert next(row for row in result['coverage'] if row['check'] == 'api_authorization')['reason']
    assert sum(counts['counts'].values()) == 6
    card = client.get('/api/records/assets').json()['items'][0]
    assert card['coverage_summary']['completed'] == 5
    report = client.get('/api/reports/export', params={'format': 'json', 'task_id': plan['id']}).json()
    assert len(report['coverage']) == 6
    markdown = client.get('/api/reports/export', params={'task_id': plan['id']}).text
    assert '검증 완료: 5/6' in markdown and 'skipped' in markdown


def test_pending_or_rejected_plan_does_not_replace_approved_evidence(client, lab):
    url, handler = lab
    asset = register(client, url)
    approved = task(client, asset, ['security_headers'])
    client.post('/api/tasks/' + approved['id'] + '/approve')
    finish(client, approved['id'])
    assert summary(client)['completed'] == 1 and summary(client)['percent'] == 17
    pending = task(client, asset, ['security_headers'])
    client.post('/api/tasks/' + pending['id'] + '/stop')
    assert summary(client)['completed'] == 1
    rejected = client.get('/api/tasks/' + pending['id']).json()
    assert rejected['coverage'][0]['status'] == 'cancelled'
    assert handler.requests == ['/']


def test_revision_change_marks_old_proof_stale_and_new_check_only_replaces_its_cell(client, lab):
    url, _ = lab
    asset = register(client, url)
    approved = task(client, asset, ['security_headers', 'cookie_policy'])
    client.post('/api/tasks/' + approved['id'] + '/approve')
    finish(client, approved['id'])
    changed = client.put('/api/assets/' + asset['id'], json={**asset, 'owner': 'New owner'}).json()
    assert summary(client)['completed'] == 0
    assert summary(client)['counts']['stale'] == 2
    newer = task(client, changed, ['security_headers'])
    client.post('/api/tasks/' + newer['id'] + '/approve')
    finish(client, newer['id'])
    assert summary(client)['completed'] == 1
    assert summary(client)['counts']['stale'] == 1
    client.post('/api/assets/' + asset['id'] + '/archive', json={'archived': True})
    assert summary(client)['expected'] == 0
    client.post('/api/assets/' + asset['id'] + '/archive', json={'archived': False})
    assert summary(client)['expected'] == 6 and summary(client)['completed'] == 0
    assert summary(client)['counts']['stale'] == 2


def test_baseline_failure_records_every_selected_check(client, lab):
    url, handler = lab
    handler.fault = True
    asset = register(client, url)
    plan = task(client, asset, ['security_headers', 'cookie_policy'])
    client.post('/api/tasks/' + plan['id'] + '/approve')
    result = finish(client, plan['id'])
    assert result['task']['status'] == 'failed'
    assert len(result['coverage']) == 2
    assert {row['status'] for row in result['coverage']} == {'failed'}
    assert summary(client)['counts']['failed'] == 2 and summary(client)['completed'] == 0


def test_stop_keeps_completed_proof_and_cancels_unrun_checks(client, lab, monkeypatch):
    url, _ = lab
    entered, release = threading.Event(), threading.Event()
    def delayed_check(*args):
        entered.set()
        assert release.wait(4)
        return [], [], None
    monkeypatch.setattr('aegis.engine.run_check', delayed_check)
    asset = register(client, url)
    plan = task(client, asset, ['security_headers', 'cookie_policy'])
    client.post('/api/tasks/' + plan['id'] + '/approve')
    assert entered.wait(3)
    try:
        client.post('/api/tasks/' + plan['id'] + '/stop')
    finally:
        release.set()
    result = finish(client, plan['id'])
    assert result['task']['status'] == 'stopped'
    assert [row['status'] for row in result['coverage']] == ['completed', 'cancelled']
    assert summary(client)['counts']['cancelled'] == 1
    client.app.state.engine.pool.shutdown(wait=True)
    assert not client.app.state.engine.stops


def seed_task(store, asset, id, created, checks, status='completed'):
    row = {'id': id, 'created_at': created, 'approved_at': created, 'status': status,
           'scope_snapshot': [asset], 'checks': checks}
    store.put('tasks', row)
    return row


def test_newer_attempt_wins_even_when_old_attempt_finishes_later(tmp_path):
    store = Store(tmp_path / 'coverage.db')
    asset = {'id': 'a', 'revision': 1}
    store.put('assets', asset)
    old = seed_task(store, asset, 'old', 1, ['security_headers', 'cookie_policy'])
    newer = seed_task(store, asset, 'new', 2, ['security_headers'], 'failed')
    store.put('coverage', slot(newer, asset, 'security_headers', 'failed', updated_at=2))
    store.put('coverage', slot(old, asset, 'security_headers', 'completed', updated_at=100))
    store.put('coverage', slot(old, asset, 'cookie_policy', 'completed', updated_at=100))
    with store.connect() as db:
        data = latest_summary(db)
    assert data['completed'] == 1 and data['counts']['failed'] == 1
    assert data['counts']['not_started'] == 4
    assert data['covered_assets'] == 1 and data['fully_covered_assets'] == 0
    assert data['assets'] == {}  # Whole-workspace summary does not materialize all asset summaries.


def test_legacy_missing_results_are_unknown_and_recovery_preserves_finished_checks(tmp_path):
    store = Store(tmp_path / 'coverage.db')
    asset = {'id': 'a', 'revision': 1}
    store.put('assets', asset)
    old = seed_task(store, asset, 'old', 1, ['security_headers'])
    assert task_rows(store, old)[0]['status'] == 'not_recorded'
    with store.connect() as db:
        assert latest_summary(db)['counts']['not_recorded'] == 1
    interrupted = seed_task(store, asset, 'restart', 2, ['security_headers', 'cookie_policy'], 'running')
    store.put('coverage', slot(interrupted, asset, 'security_headers', 'completed'))
    store.put('coverage', slot(interrupted, asset, 'cookie_policy', 'running'))
    engine = Engine(store)
    try:
        assert store.get('tasks', interrupted['id'])['status'] == 'interrupted'
        rows = task_rows(store, store.get('tasks', interrupted['id']))
        assert [row['status'] for row in rows] == ['completed', 'interrupted']
        with store.connect() as db:
            assert latest_summary(db)['counts']['interrupted'] == 1
    finally:
        engine.shutdown()


def test_approval_order_defines_latest_attempt_not_creation_order(tmp_path):
    store = Store(tmp_path / 'approval.db')
    asset = {'id': 'a', 'revision': 1}
    store.put('assets', asset)
    older_plan = seed_task(store, asset, 'older-plan', 1, ['security_headers'])
    recent_plan = seed_task(store, asset, 'recent-plan', 2, ['security_headers'])
    store.patch('tasks', 'older-plan', approved_at=3)
    store.put('coverage', slot(recent_plan, asset, 'security_headers', 'completed'))
    store.put('coverage', slot(older_plan, asset, 'security_headers', 'failed'))
    with store.connect() as db:
        result = latest_summary(db)
    assert result['completed'] == 0 and result['counts']['failed'] == 1


def test_large_workspace_summary_stays_bounded_and_exact(tmp_path, monkeypatch):
    import json
    from aegis.checks import CHECK_IDS
    store = Store(tmp_path / 'large-coverage.db')
    records = []
    for index in range(2000):
        asset = {'id': f'a{index}', 'revision': 1}
        plan = {'id': f't{index}', 'created_at': index + 1, 'approved_at': index + 1,
                'status': 'completed', 'scope_snapshot': [asset], 'checks': sorted(CHECK_IDS)}
        records.extend([('assets', asset), ('tasks', plan)])
        records.extend(('coverage', slot(plan, asset, check, 'completed' if index % 2 else 'failed')) for check in CHECK_IDS)
    store.put_many(records)
    monkeypatch.setattr(store, 'all', lambda *_: (_ for _ in ()).throw(AssertionError('Unbounded read')))
    with store.connect() as db:
        result = latest_summary(db)
    assert result['expected'] == 12000 and result['completed'] == 6000
    assert result['counts']['failed'] == 6000 and result['percent'] == 50
    assert result['fully_covered_assets'] == 1000
    assert len(json.dumps(result).encode()) < 1000
    page = store.page('assets')
    assert len(page['items']) == 25 and page['total'] == 2000
    assert sum(item['coverage_summary']['completed'] for item in page['items']) == 13 * 6


def test_queued_stop_cancels_all_cells_without_target_request(client, lab, monkeypatch):
    from concurrent.futures import Future
    url, handler = lab
    engine = client.app.state.engine
    # Hold the queue so a stop can arrive before the task thread starts.
    monkeypatch.setattr(engine.pool, 'submit', lambda *_: Future())
    asset = register(client, url)
    plan = task(client, asset, ['security_headers', 'cookie_policy'])
    assert client.post('/api/tasks/' + plan['id'] + '/approve').status_code == 200
    assert client.post('/api/tasks/' + plan['id'] + '/stop').json()['status'] == 'stopped'
    engine.run(plan['id'])
    result = client.get('/api/tasks/' + plan['id']).json()
    assert result['task']['status'] == 'stopped'
    assert [row['status'] for row in result['coverage']] == ['cancelled', 'cancelled']
    assert handler.requests == [] and not engine.stops


def test_internal_planning_failure_records_all_cells_and_sanitizes_error(client, lab, monkeypatch):
    url, handler = lab
    engine = client.app.state.engine
    def fail_plan(_,control=None):
        raise RuntimeError('DO-NOT-LOG-PRIVATE-PLANNER-DATA')
    monkeypatch.setattr(engine, 'plan', fail_plan)
    asset = register(client, url)
    plan = task(client, asset, ['security_headers', 'cookie_policy'])
    client.post('/api/tasks/' + plan['id'] + '/approve')
    result = finish(client, plan['id'])
    assert result['task']['status'] == 'failed' and result['task']['errors'] == 1
    assert {row['status'] for row in result['coverage']} == {'failed'}
    assert summary(client)['counts']['failed'] == 2
    import json
    assert 'DO-NOT-LOG-PRIVATE-PLANNER-DATA' not in json.dumps(result)
    assert handler.requests == [] and not engine.stops
