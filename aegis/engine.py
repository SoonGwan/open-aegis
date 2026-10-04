import concurrent.futures
import json
import os
import threading
import time
from contextlib import nullcontext
from .maintenance import WorkspaceBusy
from .runtime import ExecutionPolicy, TaskControl, OriginLimiter
from .dns import resolver

from .checks import CATALOG, CHECK_IDS, run_check
from .tool_contracts import require_contracts, validate_result, ToolContractMismatch
from .network import Transport
from .costs import price_snapshot, estimate
from . import call_ledger
from .llm import completion, token_usage
from .store import identifier, now
from .coverage import slot, finish_remaining
from .findings import record_observation, apply_retest
from .worker_observations import record_link
from .worker_dependencies import validate as validate_dependencies, evidence_inputs, contract as dependency_contract, require_contract as require_dependency_contract, WorkerDependencyMismatch


class Engine:
    def __init__(self, store, allow_private=False, policy=None):
        self.store = store
        self.allow_private = allow_private
        self.policy = policy or ExecutionPolicy.from_env()
        self.limiter = OriginLimiter(self.policy)
        self.owner=None;self.pool=None
        self.stops = {}
        self.lock = threading.RLock()
        self.futures = {}
        self.queue_stop = threading.Event()
        self.closed = False
        self.queue_errors = 0
        self.queue_last_error_at = None
        try:
            if getattr(store,'backend',None)=='postgres':self.owner=store.acquire_runtime()
            self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=self.policy.concurrent_tasks,thread_name_prefix='aegis-task')
            if self.owner:call_ledger.recover(store)
            for task in store.recovery_tasks():
                if task['status'] in ('running', 'queued', 'stopping'):
                    finish_remaining(store, task, 'interrupted', '서버 재시작으로 실행 결과를 확인할 수 없습니다.')
                    store.patch('tasks', task['id'], status='interrupted', finished_at=now())
                    store.event(task['id'], '서버 재시작으로 작업이 중단되었습니다. 새 승인 작업으로 다시 실행하세요.', 'warning')
            self.queue_thread = threading.Thread(target=self.watch_queue,daemon=True,name='aegis-queue-deadline')
            self.queue_thread.start()
        except BaseException:
            if self.pool:self.pool.shutdown(wait=True,cancel_futures=True)
            if self.owner:self.owner.close()
            raise

    def metrics(self):
        recorded=self.store.task_metrics();oldest=recorded['oldest_queued_at']
        return {'policy':self.policy.public(),'tasks':recorded['tasks'],'oldest_queue_seconds':max(0,now()-oldest) if oldest else 0,
                'timeouts':recorded['timeouts'],'requests':self.limiter.snapshot(),'dns':resolver().snapshot(),
                'queue_watchdog':{'alive':self.queue_thread.is_alive(),'errors':self.queue_errors,'last_error_at':self.queue_last_error_at},
                'generated_at':now(),'counter_scope':'server_process'}

    def watch_queue(self):
        while not self.queue_stop.wait(.25):
            try:
                for id in self.store.overdue_task_ids(now()-self.policy.queue_timeout):
                    with self.lock:
                        task=self.store.get('tasks',id)
                        if not task or task['status']!='queued':continue
                        future=self.futures.get(task['id'])
                        if future and not future.cancel():continue
                        if task.get('retest_of'):apply_retest(self.store,task,'inconclusive')
                        finish_remaining(self.store,task,'failed','대기열 시간 제한을 초과했습니다.')
                        self.stops.pop(task['id'],None)
                        self.store.patch('tasks',task['id'],status='failed',finished_at=now(),errors=1,termination_reason='queue_timeout')
                        self.store.event(task['id'],'대기열 시간 제한을 초과했습니다. 새 승인 계획으로 다시 실행하세요.','warning')
            except Exception as exc:
                # Do not expose exception content, SQL values or target data.
                with self.lock:
                    self.queue_errors += 1
                    self.queue_last_error_at = now()
                    if isinstance(exc,WorkspaceBusy):
                        self.closed=True
                        for stop in self.stops.values():stop.set()
                        self.queue_stop.set()

    def start(self, task_id):
        with self.lock:
            if self.closed:raise ValueError('서버가 종료 중입니다. 재시작 후 승인하세요.')
            task = self.store.get('tasks', task_id)
            if task['status'] != 'pending':
                raise ValueError('승인 대기 중인 작업만 실행할 수 있습니다.')
            require_contracts(task)
            validate_dependencies(task['asset_ids'], task.get('worker_dependencies', {}))
            if task.get('execution_policy') and task['execution_policy'] != self.policy.public():
                raise ValueError('서버 실행 정책이 변경되었습니다. 현재 정책으로 새 계획을 만드세요.')
            for snapshot in task['scope_snapshot']:
                current = self.store.get('assets', snapshot['id'])
                if not current or current.get('archived_at'):
                    raise ValueError('보관된 자산은 승인할 수 없습니다. 활성 자산으로 새 계획을 만드세요.')
                if current.get('revision', 1) != snapshot.get('revision', 1):
                    raise ValueError('계획 생성 후 자산이 수정되었습니다. 현재 범위로 새 계획을 만드세요.')
            self.stops[task_id] = threading.Event()
            self.store.patch('tasks', task_id, status='queued', approved_at=now(), execution_policy=self.policy.public(),
                             worker_dependency_contract=dependency_contract(task))
            self.store.event(task_id, '등록된 범위와 검증 도구를 승인했습니다.', detail={'checks': task['checks'], 'asset_ids': task['asset_ids'], 'tool_contracts': task['tool_contracts']})
            future=self.pool.submit(self.run, task_id)
            self.futures[task_id]=future
            def cleanup(_):
                with self.lock:self.futures.pop(task_id,None)
            future.add_done_callback(cleanup)

    def stop(self, task_id):
        with self.lock:
            task = self.store.get('tasks', task_id)
            if task['status'] in ('completed', 'failed', 'stopped', 'interrupted', 'rejected'):
                return task
            if task_id in self.stops:
                self.stops[task_id].set()
            future = self.futures.get(task_id)
            cancelled_queue = task['status']=='queued' and future is not None and future.cancel()
            status = 'rejected' if task['status'] == 'pending' else 'stopped' if cancelled_queue else 'stopping'
            if cancelled_queue:
                finish_remaining(self.store,task,'cancelled','실행 전에 중지되었습니다.')
                if task.get('retest_of'):apply_retest(self.store,task,'inconclusive')
                self.store.patch('tasks',task_id,finished_at=now(),termination_reason='shutdown' if self.closed else 'operator_stop')
                self.stops.pop(task_id,None)
            if status == 'rejected':
                finish_remaining(self.store, task, 'cancelled', '실행 승인이 거절되었습니다.')
            self.store.patch('tasks', task_id, status=status)
            self.store.event(task_id, '작업 중지 요청을 기록했습니다.', 'warning')
            return self.store.get('tasks', task_id)

    def plan(self, task, control=None):
        checks = task['checks']
        if task['planner'] != 'ai':
            return checks
        key = os.environ.get('AEGIS_LLM_API_KEY')
        model = os.environ.get('AEGIS_LLM_MODEL')
        base = os.environ.get('AEGIS_LLM_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
        if not key or not model:
            self.store.event(task['id'], 'LLM 환경변수가 없어 규칙 기반 계획을 사용합니다.', 'warning')
            return checks
        # Only asset names, check names, and operator goal are sent, never target bodies or credentials.
        prompt = {'goal': task['goal'], 'checks': checks,
                  'assets': [{'name': a['name'], 'type': a['type']} for a in task['scope_snapshot']]}
        payload = {'model': model, 'messages': [
            {'role': 'system', 'content': 'Return JSON only: {"checks": [check ids]}. Order all supplied checks by relevance. Never invent tools, URLs, commands, or omit checks.'},
            {'role': 'user', 'content': json.dumps(prompt, ensure_ascii=False)}], 'temperature': 0}
        started_at = now()
        price = price_snapshot(model, base, started_at)
        call_id=call_ledger.start(self.store,'planner',task['id'],model,base,started_at,price)
        usage = token_usage(None)
        outcome = 'request_failed'
        proposed = checks
        try:
            with getattr(self.store,'execution_permit',nullcontext)():
                raw = completion(base, key, payload, allow_local=self.allow_private, control=control, timeout=self.policy.request_timeout)
            outcome = 'invalid_plan'
            usage = token_usage(raw.get('usage') if isinstance(raw, dict) else None)
            text = raw['choices'][0]['message']['content'].strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
            proposed = json.loads(text)['checks']
            if not isinstance(proposed, list) or len(proposed) != len(checks) or set(proposed) != set(checks):
                raise ValueError('invalid plan')
            outcome = 'accepted'
        except Exception:
            proposed = checks
        accepted = outcome == 'accepted'
        observed_at = now()
        detail={
            'model':model, 'outcome':outcome, 'observed_at':observed_at, 'started_at':started_at,
            'tokens':usage, 'cost':estimate(usage, price, observed_at),
            'checks':proposed, 'call_id':call_id,
        }
        call_ledger.observe(self.store,call_id,detail)
        try:
            self.store.record_planner_call(task['id'], detail, 'AI가 승인된 검증 도구의 실행 순서를 계획했습니다.' if accepted else
               'AI 계획을 검증하지 못해 규칙 기반 계획으로 진행합니다.',
               'info' if accepted else 'warning')
        except BaseException:
            try:
                call_ledger.abandon(self.store,call_id)
            except Exception:
                pass  # Durable observation remains unresolved; startup recovery will flag it.
            raise
        return proposed

    def run(self, task_id):
        task = self.store.get('tasks', task_id)
        with self.lock:
            if task['status'] not in ('queued','stopping'):return
            stop = self.stops[task_id]
        if stop.is_set():
            finish_remaining(self.store, task, 'cancelled', '실행 전에 중지되었습니다.')
            if task.get('retest_of'):apply_retest(self.store,task,'inconclusive')
            self.store.patch('tasks', task_id, status='stopped', finished_at=now(), termination_reason='shutdown' if self.closed else 'operator_stop')
            with self.lock:
                self.stops.pop(task_id, None)
            return
        if now() - (task.get('approved_at') or now()) > self.policy.queue_timeout:
            finish_remaining(self.store, task, 'failed', '대기열 시간 제한을 초과했습니다. 새 승인 계획으로 다시 실행하세요.')
            if task.get('retest_of'):apply_retest(self.store,task,'inconclusive')
            self.store.patch('tasks', task_id, status='failed', finished_at=now(), errors=1, termination_reason='queue_timeout')
            self.store.event(task_id, '대기열 시간 제한을 초과했습니다.', 'warning')
            with self.lock:self.stops.pop(task_id, None)
            return
        control = TaskControl(stop, time.monotonic()+self.policy.task_timeout)
        task['started_at'] = now()
        self.store.patch('tasks', task_id, status='running', started_at=task['started_at'], queue_wait_ms=round((task['started_at']-(task.get('approved_at') or task['started_at']))*1000))
        self.store.event(task_id, 'Planner가 검증 계획을 준비합니다.')
        try:
            require_contracts(task)
            require_dependency_contract(task)
            checks = self.plan(task, control)
            control.check()
            self.store.patch('tasks', task_id, plan=checks)
            self.store.event(task_id, '검증 작업을 병렬 Worker에 배정합니다.', detail={'workers': task['workers'], 'checks': checks})
            outcomes = self.run_workers(task, checks, control)
            timed_out = control.expired() and not stop.is_set()
            status = 'stopped' if stop.is_set() else 'failed' if timed_out or all(not o['completed_checks'] for o in outcomes) else 'completed'
            errors = max(1 if timed_out else 0, sum(len(o['errors']) for o in outcomes))
            if task.get('retest_of'):
                finding = self.store.get('findings', task['retest_of'])
                relevant = next((o for o in outcomes if o['asset_id'] == finding['asset_id']), None)
                if not relevant or finding['check'] not in relevant['completed_checks'] or stop.is_set() or timed_out:
                    conclusion = 'inconclusive'
                elif finding['fingerprint'] in relevant['fingerprints']:
                    conclusion = 'reproduced'
                else:
                    conclusion = 'resolved'
                apply_retest(self.store, task, conclusion)
                self.store.event(task_id, '재검증 결과를 기록했습니다.', detail={'conclusion': conclusion})
            finish_remaining(self.store, task, 'cancelled' if status == 'stopped' else 'failed',
                             '중지되어 실행하지 못했습니다.' if status == 'stopped' else '작업 종료 전 결과를 기록하지 못했습니다.')
            self.store.patch('tasks', task_id, status=status, finished_at=now(), errors=errors, termination_reason='timeout' if timed_out else ('shutdown' if self.closed else 'operator_stop') if stop.is_set() else None)
            self.store.event(task_id, '작업 종료: ' + status, 'warning' if errors else 'info', {'errors': errors})
        except Exception as exc:
            timed_out = control.expired() and not stop.is_set()
            stopped = stop.is_set()
            dependency_changed = isinstance(exc, WorkerDependencyMismatch)
            contract_changed = isinstance(exc, (ToolContractMismatch, WorkerDependencyMismatch))
            contract_message = '승인한 Worker 의존 관계가 변경되어 실행하지 않았습니다. 새 계획을 만드세요.' if dependency_changed else '검증 도구 계약이 변경되어 실행하지 않았습니다. 새 승인 계획을 만드세요.'
            finish_remaining(self.store, task, 'cancelled' if stopped else 'failed',
                             '작업이 중지되었습니다.' if stopped else '작업 실행 시간 제한을 초과했습니다.' if timed_out else
                             contract_message if contract_changed else '내부 오류로 검증 결과를 기록하지 못했습니다.')
            if task.get('retest_of'):
                apply_retest(self.store, task, 'inconclusive')
            current = self.store.get('tasks', task_id)
            self.store.patch('tasks', task_id, status='stopped' if stopped else 'failed', finished_at=now(),
                             errors=max(1, current['errors']), termination_reason=('shutdown' if self.closed else 'operator_stop') if stopped else 'timeout' if timed_out else 'worker_dependency_changed' if dependency_changed else 'tool_contract_changed' if contract_changed else 'internal_error')
            self.store.event(task_id, '작업 실행 시간 제한을 초과했습니다.' if timed_out else '작업이 중지되었습니다.' if stopped else contract_message if contract_changed else '작업 실행 중 내부 오류가 발생했습니다. 서버 로그를 확인하세요.', 'warning' if stopped or timed_out or contract_changed else 'error')
        finally:
            with self.lock:
                self.stops.pop(task_id, None)

    def run_workers(self, task, checks, control):
        dependencies = validate_dependencies(task['asset_ids'], task.get('worker_dependencies', {}))
        pending = {asset['id']: asset for asset in task['scope_snapshot']}
        outcomes, running = {}, {}
        def finished(outcome):
            outcomes[outcome['asset_id']] = outcome
            with self.lock:
                current = self.store.get('tasks', task['id'])
                self.store.patch('tasks', task['id'], done=current['done'] + 1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=task['workers']) as workers:
            while pending or running:
                if control.stop.is_set() or control.expired():
                    pending.clear()
                for id, asset in list(pending.items()):
                    if control.stop.is_set() or control.expired():break
                    parents = dependencies.get(id, [])
                    if not all(parent in outcomes for parent in parents):continue
                    if len(running) >= task['workers']:break
                    try:
                        inputs = evidence_inputs(self.store, task, parents) if parents else []
                    except ValueError:
                        for check in checks:
                            self.store.put('coverage', {**slot(task, asset, check), 'status': 'failed',
                                'reason': '선행 Worker의 검증 완료 근거가 없어 실행하지 않았습니다.',
                                'error_type': 'WorkerDependencyBlocked', 'finished_at': now()})
                        self.store.event(task['id'], '선행 Worker 입력을 검증하지 못해 실행하지 않았습니다.', 'warning',
                            {'asset_id': id, 'worker_id': task['id']+':'+id, 'dependencies': parents})
                        finished({'asset_id': id, 'completed_checks': [], 'fingerprints': [], 'errors': ['dependency_blocked']})
                    else:
                        args = (task, asset, checks, control, inputs) if inputs else (task, asset, checks, control)
                        running[workers.submit(self.validate_asset, *args)] = id
                    del pending[id]
                if running:
                    done, _ = concurrent.futures.wait(running, timeout=.05,
                        return_when=concurrent.futures.FIRST_COMPLETED)
                    for future in done:
                        del running[future]
                        finished(future.result())
                elif pending:
                    # A validated DAG must always expose a ready node.
                    if control.stop.is_set() or control.expired():pending.clear()
                    else:raise ValueError('Worker 의존 단계의 진행 근거를 확인할 수 없습니다.')
        return list(outcomes.values())

    def validate_asset(self, task, asset, checks, control, inputs=None):
        stop = control.stop
        task_id = task['id']
        worker_id = task_id + ':' + asset['id']
        def event(message, level='info', detail=None):
            self.store.event(task_id, message, level, {**(detail or {}), 'asset_id': asset['id'], 'worker_id': worker_id})
        outcome = {'asset_id': asset['id'], 'completed_checks': [], 'fingerprints': [], 'errors': []}
        def coverage(check, status, **details):
            record = self.store.get('coverage', f"{task_id}:{asset['id']}:{check}") or slot(task, asset, check)
            return self.store.put('coverage', {**record, 'status': status, 'updated_at': now(), **details})
        def record(entry):
            self.store.put('traffic', dict(entry, id=identifier(), task_id=task_id, asset_id=asset['id'], created_at=now()))
        transport = Transport(asset['url'], self.allow_private, record, stop.is_set, policy=self.policy, limiter=self.limiter, control=control,
                              execution_permit=getattr(self.store,'execution_permit',None))
        if inputs:
            event('승인된 선행 Worker의 완료 근거와 관찰 참조를 받았습니다.', detail={'dependency_inputs': inputs})
        event('Worker 시작: ' + asset['name'], detail={'asset_id': asset['id']})
        try:
            require_contracts(task)
            response = transport.get()
            if not 200 <= response['status'] < 300:
                raise ValueError('기본 응답이 2xx가 아니어서 설정 검증을 완료할 수 없습니다.')
        except Exception as exc:
            outcome['errors'].append(type(exc).__name__)
            event('대상 연결 또는 범위 검증 실패: ' + asset['name'], 'error', {'error_type': type(exc).__name__, 'asset_id': asset['id']})
            for check in checks:
                coverage(check, 'cancelled' if stop.is_set() else 'failed',
                         reason='요청이 중지되었습니다.' if stop.is_set() else '작업 실행 시간 제한을 초과했습니다.' if control.expired() else '기본 응답 또는 연결을 확인하지 못했습니다.', error_type=type(exc).__name__)
            return outcome
        for check in checks:
            if stop.is_set() or control.expired():
                for remaining in checks[checks.index(check):]:
                    coverage(remaining, 'cancelled' if stop.is_set() else 'failed', reason='작업 중지로 실행하지 못했습니다.' if stop.is_set() else '작업 실행 시간 제한을 초과했습니다.', error_type='InterruptedError' if stop.is_set() else 'TaskDeadline')
                break
            coverage(check, 'running', reason='검증 실행 중입니다.', started_at=now())
            event('검증 실행: ' + check, detail={'asset_id': asset['id'], 'check': check})
            try:
                findings, observed, skipped = validate_result(check, asset, run_check(check, asset, transport, response))
                if skipped:
                    coverage(check, 'skipped', reason=skipped, finished_at=now())
                    event(skipped, 'warning', {'check': check, 'asset_id': asset['id']})
                    continue
                for item in findings:
                    finding, evidence, _ = record_observation(self.store, task, asset, item)
                    outcome['fingerprints'].append(finding['fingerprint'])
                    event(item['title'], 'finding', {'finding_id': finding['id'], 'severity': item['severity'], 'asset_id': asset['id']})
                for url in observed:
                    record_link(self.store, task, asset, check, url)
                coverage(check, 'completed', reason='승인된 검증을 완료했습니다.', finished_at=now())
                outcome['completed_checks'].append(check)
            except Exception as exc:
                outcome['errors'].append(check)
                coverage(check, 'cancelled' if stop.is_set() else 'failed',
                         reason='요청이 중지되었습니다.' if stop.is_set() else '작업 실행 시간 제한을 초과했습니다.' if control.expired() else '검증 결과를 확인하지 못했습니다.',
                         error_type=type(exc).__name__, finished_at=now())
                event('검증 결과를 확인할 수 없습니다.', 'warning', {'check': check, 'asset_id': asset['id'], 'error_type': type(exc).__name__})
        event('Worker 종료: ' + asset['name'], detail={'completed_checks': outcome['completed_checks'], 'asset_id': asset['id']})
        return outcome

    def shutdown(self):
        try:
            self._shutdown()
        except WorkspaceBusy:
            pass  # Lost owner cannot write shutdown state; next owner recovers it.
        finally:
            with self.lock:
                self.stops.clear();self.futures.clear()
            if self.owner:self.owner.close()

    def _shutdown(self):
        with self.lock:self.closed = True
        self.queue_stop.set()
        self.queue_thread.join()
        for stop in list(self.stops.values()):
            stop.set()
        self.pool.shutdown(wait=True, cancel_futures=True)
        with self.lock:
            for task_id in list(self.stops):
                task=self.store.get('tasks',task_id)
                if task and task['status'] in ('queued','running','stopping'):
                    finish_remaining(self.store,task,'cancelled','서버 종료로 실행하지 못했습니다.')
                    if task.get('retest_of'):apply_retest(self.store,task,'inconclusive')
                    self.store.patch('tasks',task_id,status='stopped',finished_at=now(),termination_reason='shutdown')
            self.stops.clear()
            self.futures.clear()
