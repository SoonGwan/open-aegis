import concurrent.futures
import hashlib
import json
import os
import threading

from .checks import CATALOG, CHECK_IDS, run_check
from .network import Transport
from .llm import completion
from .store import identifier, now
from .coverage import slot, finish_remaining
from .findings import record_observation, apply_retest


class Engine:
    def __init__(self, store, allow_private=False):
        self.store = store
        self.allow_private = allow_private
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix='aegis-task')
        self.stops = {}
        self.lock = threading.RLock()
        for task in store.all('tasks'):
            if task['status'] in ('running', 'queued', 'stopping'):
                finish_remaining(store, task, 'interrupted', '서버 재시작으로 실행 결과를 확인할 수 없습니다.')
                store.patch('tasks', task['id'], status='interrupted', finished_at=now())
                store.event(task['id'], '서버 재시작으로 작업이 중단되었습니다. 새 승인 작업으로 다시 실행하세요.', 'warning')

    def start(self, task_id):
        with self.lock:
            task = self.store.get('tasks', task_id)
            if task['status'] != 'pending':
                raise ValueError('승인 대기 중인 작업만 실행할 수 있습니다.')
            for snapshot in task['scope_snapshot']:
                current = self.store.get('assets', snapshot['id'])
                if not current or current.get('archived_at'):
                    raise ValueError('보관된 자산은 승인할 수 없습니다. 활성 자산으로 새 계획을 만드세요.')
                if current.get('revision', 1) != snapshot.get('revision', 1):
                    raise ValueError('계획 생성 후 자산이 수정되었습니다. 현재 범위로 새 계획을 만드세요.')
            self.stops[task_id] = threading.Event()
            self.store.patch('tasks', task_id, status='queued', approved_at=now())
            self.store.event(task_id, '등록된 범위와 검증 도구를 승인했습니다.', detail={'checks': task['checks'], 'asset_ids': task['asset_ids']})
            self.pool.submit(self.run, task_id)

    def stop(self, task_id):
        with self.lock:
            task = self.store.get('tasks', task_id)
            if task['status'] in ('completed', 'failed', 'stopped', 'interrupted', 'rejected'):
                return task
            if task_id in self.stops:
                self.stops[task_id].set()
            status = 'rejected' if task['status'] == 'pending' else 'stopping'
            if status == 'rejected':
                finish_remaining(self.store, task, 'cancelled', '실행 승인이 거절되었습니다.')
            self.store.patch('tasks', task_id, status=status)
            self.store.event(task_id, '작업 중지 요청을 기록했습니다.', 'warning')
            return self.store.get('tasks', task_id)

    def plan(self, task):
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
        try:
            raw = completion(base, key, payload, allow_local=self.allow_private)
            text = raw['choices'][0]['message']['content'].strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
            proposed = json.loads(text)['checks']
            if not isinstance(proposed, list) or len(proposed) != len(checks) or set(proposed) != set(checks):
                raise ValueError('invalid plan')
            self.store.event(task['id'], 'AI가 승인된 검증 도구의 실행 순서를 계획했습니다.', detail={'checks': proposed, 'model': model, 'tokens': raw.get('usage', {})})
            return proposed
        except Exception:
            self.store.event(task['id'], 'AI 계획을 검증하지 못해 규칙 기반 계획으로 진행합니다.', 'warning')
            return checks

    def run(self, task_id):
        task = self.store.get('tasks', task_id)
        stop = self.stops[task_id]
        if stop.is_set():
            finish_remaining(self.store, task, 'cancelled', '실행 전에 중지되었습니다.')
            self.store.patch('tasks', task_id, status='stopped', finished_at=now())
            with self.lock:
                self.stops.pop(task_id, None)
            return
        self.store.patch('tasks', task_id, status='running', started_at=now())
        self.store.event(task_id, 'Planner가 검증 계획을 준비합니다.')
        try:
            checks = self.plan(task)
            self.store.patch('tasks', task_id, plan=checks)
            self.store.event(task_id, '검증 작업을 병렬 Worker에 배정합니다.', detail={'workers': task['workers'], 'checks': checks})
            outcomes = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=task['workers']) as workers:
                futures = [workers.submit(self.validate_asset, task, asset, checks, stop) for asset in task['scope_snapshot']]
                for future in concurrent.futures.as_completed(futures):
                    outcomes.append(future.result())
                    with self.lock:
                        current = self.store.get('tasks', task_id)
                        self.store.patch('tasks', task_id, done=current['done'] + 1)
            status = 'stopped' if stop.is_set() else 'failed' if all(not o['completed_checks'] for o in outcomes) else 'completed'
            errors = sum(len(o['errors']) for o in outcomes)
            if task.get('retest_of'):
                finding = self.store.get('findings', task['retest_of'])
                relevant = next((o for o in outcomes if o['asset_id'] == finding['asset_id']), None)
                if not relevant or finding['check'] not in relevant['completed_checks'] or stop.is_set():
                    conclusion = 'inconclusive'
                elif finding['fingerprint'] in relevant['fingerprints']:
                    conclusion = 'reproduced'
                else:
                    conclusion = 'resolved'
                apply_retest(self.store, task, conclusion)
                self.store.event(task_id, '재검증 결과를 기록했습니다.', detail={'conclusion': conclusion})
            finish_remaining(self.store, task, 'cancelled' if status == 'stopped' else 'failed',
                             '중지되어 실행하지 못했습니다.' if status == 'stopped' else '작업 종료 전 결과를 기록하지 못했습니다.')
            self.store.patch('tasks', task_id, status=status, finished_at=now(), errors=errors)
            self.store.event(task_id, '작업 종료: ' + status, 'warning' if errors else 'info', {'errors': errors})
        except Exception:
            finish_remaining(self.store, task, 'failed', '내부 오류로 검증 결과를 기록하지 못했습니다.')
            current = self.store.get('tasks', task_id)
            self.store.patch('tasks', task_id, status='failed', finished_at=now(), errors=max(1, current['errors']))
            self.store.event(task_id, '작업 실행 중 내부 오류가 발생했습니다. 서버 로그를 확인하세요.', 'error')
        finally:
            with self.lock:
                self.stops.pop(task_id, None)

    def validate_asset(self, task, asset, checks, stop):
        task_id = task['id']
        outcome = {'asset_id': asset['id'], 'completed_checks': [], 'fingerprints': [], 'errors': []}
        def coverage(check, status, **details):
            record = self.store.get('coverage', f"{task_id}:{asset['id']}:{check}") or slot(task, asset, check)
            return self.store.put('coverage', {**record, 'status': status, 'updated_at': now(), **details})
        def record(entry):
            self.store.put('traffic', dict(entry, id=identifier(), task_id=task_id, asset_id=asset['id'], created_at=now()))
        transport = Transport(asset['url'], self.allow_private, record, stop.is_set)
        self.store.event(task_id, 'Worker 시작: ' + asset['name'], detail={'asset_id': asset['id']})
        try:
            response = transport.get()
            if not 200 <= response['status'] < 300:
                raise ValueError('기본 응답이 2xx가 아니어서 설정 검증을 완료할 수 없습니다.')
        except Exception as exc:
            outcome['errors'].append(type(exc).__name__)
            self.store.event(task_id, '대상 연결 또는 범위 검증 실패: ' + asset['name'], 'error', {'error_type': type(exc).__name__, 'asset_id': asset['id']})
            for check in checks:
                coverage(check, 'cancelled' if stop.is_set() else 'failed',
                         reason='요청이 중지되었습니다.' if stop.is_set() else '기본 응답 또는 연결을 확인하지 못했습니다.', error_type=type(exc).__name__)
            return outcome
        for check in checks:
            if stop.is_set():
                for remaining in checks[checks.index(check):]:
                    coverage(remaining, 'cancelled', reason='작업 중지로 실행하지 못했습니다.')
                break
            coverage(check, 'running', reason='검증 실행 중입니다.', started_at=now())
            self.store.event(task_id, '검증 실행: ' + check, detail={'asset_id': asset['id'], 'check': check})
            try:
                findings, observed, skipped = run_check(check, asset, transport, response)
                if skipped:
                    coverage(check, 'skipped', reason=skipped, finished_at=now())
                    self.store.event(task_id, skipped, 'warning', {'check': check, 'asset_id': asset['id']})
                    continue
                for item in findings:
                    finding, evidence, _ = record_observation(self.store, task, asset, item)
                    outcome['fingerprints'].append(finding['fingerprint'])
                    self.store.event(task_id, item['title'], 'finding', {'finding_id': finding['id'], 'severity': item['severity'], 'asset_id': asset['id']})
                for url in observed:
                    self.store.put('observations', {'id': hashlib.sha256((asset['id'] + url).encode()).hexdigest()[:16],
                        'asset_id': asset['id'], 'task_id': task_id, 'url': url, 'created_at': now(), 'verified': False})
                coverage(check, 'completed', reason='승인된 검증을 완료했습니다.', finished_at=now())
                outcome['completed_checks'].append(check)
            except Exception as exc:
                outcome['errors'].append(check)
                coverage(check, 'cancelled' if stop.is_set() else 'failed',
                         reason='요청이 중지되었습니다.' if stop.is_set() else '검증 결과를 확인하지 못했습니다.',
                         error_type=type(exc).__name__, finished_at=now())
                self.store.event(task_id, '검증 결과를 확인할 수 없습니다.', 'warning', {'check': check, 'asset_id': asset['id'], 'error_type': type(exc).__name__})
        self.store.event(task_id, 'Worker 종료: ' + asset['name'], detail={'completed_checks': outcome['completed_checks'], 'asset_id': asset['id']})
        return outcome

    def shutdown(self):
        for stop in list(self.stops.values()):
            stop.set()
        self.pool.shutdown(wait=True, cancel_futures=True)
