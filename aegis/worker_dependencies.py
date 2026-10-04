"""Approved acyclic Worker dependencies and bounded, task-local evidence handoffs."""
import json
from .worker_process import get_process


class WorkerDependencyMismatch(ValueError):
    pass


def validate(asset_ids, dependencies):
    if type(asset_ids) is not list or not 1 <= len(asset_ids) <= 20 or any(type(x) is not str for x in asset_ids):
        raise ValueError('Worker 자산 목록을 확인하세요.')
    if type(dependencies) is not dict or len(dependencies) > 20:
        raise ValueError('Worker 의존 관계는 최대 20개 자산의 객체여야 합니다.')
    edges = 0
    for child, parents in dependencies.items():
        if (type(child) is not str or child not in asset_ids or type(parents) is not list
                or len(parents) > 20 or any(type(p) is not str or p not in asset_ids or p == child for p in parents)
                or len(set(parents)) != len(parents)):
            raise ValueError('의존 관계에는 선택한 서로 다른 자산만 사용할 수 있습니다.')
        edges += len(parents)
    if edges > 40:
        raise ValueError('Worker 의존 연결은 최대 40개입니다.')
    visited, active = set(), set()
    def visit(id):
        if id in active:raise ValueError('Worker 의존 관계에 순환이 있습니다.')
        if id in visited:return
        active.add(id)
        for parent in dependencies.get(id, []):visit(parent)
        active.remove(id);visited.add(id)
    for id in asset_ids:visit(id)
    return dependencies


def evidence_inputs(store, task, parents):
    """A handoff verifies persisted completion; observations remain untrusted references."""
    result=[]
    with store.read_transaction() as db:
        current=store.get('tasks',task['id'],connection=db)
        if not current or current.get('id')!=task['id']:
            raise ValueError('선행 작업의 출처를 확인할 수 없습니다.')
        for field in ('asset_ids','scope_snapshot','checks','tool_contracts','approved_at','worker_dependencies','worker_dependency_contract'):
            default={} if field=='worker_dependencies' else None
            if json.dumps(current.get(field,default),sort_keys=True,allow_nan=False)!=json.dumps(task.get(field,default),sort_keys=True,allow_nan=False):
                raise ValueError('승인된 Worker 입력 계약이 변경되었습니다.')
        for parent in parents:
            process=get_process(store,task['id'],parent,connection=db)
            if (len(process['coverage'])!=len(task['checks'])
                    or any(row['status']!='completed' for row in process['coverage'])):
                raise ValueError('선행 Worker의 모든 검증 완료 근거가 필요합니다.')
            observations=process['observations']
            refs=[row['id'] for row in observations['items'] if row['provenance']['status']=='matched'][:10]
            result.append({'format':'aegis-worker-handoff-v1','source_worker_id':process['worker']['id'],
                           'task_id':task['id'],'asset_id':parent,'scope_revision':process['worker']['scope_revision'],
                           'checks_completed':list(task['checks']), 'package_sha256':task['tool_contracts']['package_sha256'],
                           'observation_ids':refs,'observations_total':observations['total'],
                           'observations_omitted':observations['total']>len(refs)})
    return result


def contract(task):
    dependencies=validate(task['asset_ids'],task.get('worker_dependencies',{}))
    return {'format':'aegis-worker-dependencies-v1','asset_ids':task['asset_ids'],'dependencies':dependencies}


def require_contract(task):
    try:
        expected=contract(task)
        stored=task.get('worker_dependency_contract')
        if stored is None and not expected['dependencies']:return  # Legacy independent Worker plans.
        matched=json.dumps(stored,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False)
    except (ValueError,TypeError,KeyError):
        matched=False
    if not matched:
        raise WorkerDependencyMismatch('승인 후 Worker 의존 계약이 변경되었습니다.')
