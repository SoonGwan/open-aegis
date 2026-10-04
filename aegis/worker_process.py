"""Bounded reads of one task/asset Worker; stored evidence grants no execution rights."""
from contextlib import nullcontext

from .checks import CHECK_IDS
from .coverage import task_rows
from .worker_observations import provenance


class WorkerMissing(ValueError):
    pass


def _task(store, task_id, db):
    task = store.get('tasks', task_id, connection=db)
    if task is None:
        raise WorkerMissing('작업이 없습니다.')
    if not isinstance(task, dict) or task.get('id') != task_id:
        raise WorkerMissing('저장 키와 작업 출처 ID가 일치하지 않습니다.')
    scopes = task.get('scope_snapshot')
    checks = task.get('checks')
    if (not isinstance(scopes, list) or not 1 <= len(scopes) <= 20
            or not isinstance(checks, list) or not 1 <= len(checks) <= 6
            or any(type(c) is not str or c not in CHECK_IDS for c in checks)
            or len(set(checks)) != len(checks)
            or any(not isinstance(a, dict) or type(a.get('id')) is not str for a in scopes)
            or len({a['id'] for a in scopes}) != len(scopes)):
        raise WorkerMissing('작업의 Worker 범위 기록을 확인할 수 없습니다.')
    return task


def _worker(store, task_id, asset_id, db):
    task = _task(store, task_id, db)
    asset = next((a for a in task['scope_snapshot'] if a['id'] == asset_id), None)
    if asset is None:
        raise WorkerMissing('작업 범위에 해당 Worker가 없습니다.')
    return task, asset


def list_workers(store, task_id, *, connection=None):
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        task = _task(store, task_id, db)
        return {'task_id': task_id, 'task_status': task.get('status'), 'items': [
            {'id': task_id + ':' + a['id'], 'asset_id': a['id'], 'asset_name': a.get('name'),
             'scope_url': a.get('url'), 'scope_revision': a.get('revision', 1)}
            for a in task['scope_snapshot']], 'total': len(task['scope_snapshot'])}


def _collection(store, task, asset, kind, db, **options):
    if kind == 'events':
        result = store.event_page(task['id'], asset_id=asset['id'], connection=db, **options)
        for row in result['items']:
            detail = row.get('detail')
            matched = isinstance(detail, dict) and detail.get('worker_id') == task['id'] + ':' + asset['id']
            row['worker_provenance'] = {'status': 'matched' if matched else 'unconfirmed',
                                        'basis': 'stored_task_asset_worker_metadata'}
        return result
    if kind == 'observations':
        result = store.page('observations', filters={'task_id': task['id'], 'asset_id': asset['id']},
                            connection=db, **options)
        for row in result['items']:
            row['provenance'] = provenance(row, task)
        return result
    raise ValueError('알 수 없는 Worker 조회 종류입니다.')


def collection(store, task_id, asset_id, kind, *, connection=None, **options):
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        task, asset = _worker(store, task_id, asset_id, db)
        return _collection(store, task, asset, kind, db, **options)


def get_process(store, task_id, asset_id, *, connection=None):
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        task, asset = _worker(store, task_id, asset_id, db)
        def get_record(kind, id):
            getter = getattr(store, 'get_optional', store.get)
            return getter(kind, id, connection=db)
        rows = task_rows(store, {**task, 'created_at': task.get('created_at', 0), 'scope_snapshot': [asset]},
                         get_record=get_record)
        for row in rows:
            if type(row.get('asset_revision')) is not int or row['asset_revision'] != asset.get('revision', 1):
                row.update(status='not_recorded', reason='승인 범위 revision과 일치하지 않는 결과 기록입니다.')
        return {'format': 'aegis-worker-process-v1',
                'worker': {'id': task_id + ':' + asset_id, 'task_id': task_id, 'asset_id': asset_id,
                           'asset_name': asset.get('name'), 'scope_url': asset.get('url'),
                           'scope_revision': asset.get('revision', 1)},
                'task_status': task.get('status'), 'approved_at': task.get('approved_at'),
                'coverage': rows, 'events': _collection(store, task, asset, 'events', db),
                'observations': _collection(store, task, asset, 'observations', db),
                'execution_authorized': False, 'provenance_basis': 'stored_metadata_consistency'}


def search_events(store, *, connection=None, **options):
    """Workspace-wide SQL page with bounded source point reads in the same snapshot."""
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        page = store.worker_event_page(connection=db, **options)
        cache = {}
        for row in page['items']:
            asset_id = row['detail']['asset_id']
            key = (row['task_id'], asset_id)
            if key not in cache:
                try:
                    task, asset = _worker(store, *key, db)
                    cache[key] = {'available': True, 'task_id': key[0], 'asset_id': asset_id,
                                  'task_name': task.get('name'), 'asset_name': asset.get('name'),
                                  'scope_url': asset.get('url'), 'scope_revision': asset.get('revision', 1)}
                except (WorkerMissing, ValueError):
                    cache[key] = {'available': False, 'task_id': key[0], 'asset_id': asset_id}
            row['worker_source'] = cache[key]
            matched = cache[key]['available'] and row['detail'].get('worker_id') == key[0]+':'+asset_id
            row['worker_provenance'] = {'status': 'matched' if matched else 'unconfirmed',
                                        'basis': 'stored_task_asset_worker_metadata'}
        return {**page, 'execution_authorized': False}
