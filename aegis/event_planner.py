"""Durable event-driven proposal preparation; never creates or approves a task."""
import hashlib
import json
import threading

from . import next_plan, planning_history, observation_todos
from .maintenance import WorkspaceBusy
from .store_util import now

STATE_ID = 'event-planner'
FORMAT = 'aegis-event-planner-v1'
AUTOMATION_REVISION = 'observed-failure-notes-v1'
PAGE_SIZE = 25


class EventPlanner:
    def __init__(self, store, policy):
        self.store, self.policy = store, policy
        self.stop_event = threading.Event()
        self.thread = None
        self.errors = 0
        self.last_error_at = None

    def start(self):
        self.thread = threading.Thread(target=self.watch, name='aegis-event-planner', daemon=True)
        self.thread.start()

    def close(self):
        self.stop_event.set()
        if self.thread: self.thread.join()

    def metrics(self):
        return {'alive': bool(self.thread and self.thread.is_alive()), 'errors': self.errors,
                'last_error_at': self.last_error_at, 'execution_authorized': False}

    def watch(self):
        while not self.stop_event.is_set():
            try:
                progressed = self.step()
            except WorkspaceBusy:
                self.stop_event.set()
                return
            except Exception:
                # Retry the same durable position; do not leak SQL or human text.
                self.errors += 1
                self.last_error_at = now()
                progressed = False
            self.stop_event.wait(.02 if progressed else .25)

    def targets(self, task_id, db):
        task = self.store.get('tasks', task_id, connection=db)
        if task is None: return []
        history = planning_history.history(self.store, task_id, connection=db)
        candidates = {row['id']: row for row in history}
        current = history[0]
        while True:
            following, _ = planning_history.continuation(self.store, current, connection=db)
            if following is None: break
            if following['id'] in candidates or len(candidates) >= planning_history.MAX_HISTORY:
                raise planning_history.PlanningConflict('계획 연결의 한도를 확인하세요.')
            candidates[following['id']] = following
            current = following
        return [id for id, row in candidates.items()
                if row.get('approved_at') and row.get('status') in next_plan.TERMINAL]

    def prepare(self, task_id, event, policy, db):
        try:
            targets = self.targets(task_id, db)
        except (planning_history.PlanningConflict, LookupError):
            targets = [task_id]
        for id in targets:
            review = {'id': id, 'format': FORMAT, 'source_task_id': id,
                      'event_seq': event['seq'], 'prepared_at': now(),
                      'execution_authorized': False, 'proposal': None}
            try:
                review['proposal'] = next_plan.propose(self.store, id, policy, connection=db)
                review['automatic_todo']=observation_todos.ensure(self.store,id,review['proposal'],db)
                if review['automatic_todo']['status']=='created':
                    review['proposal']=next_plan.propose(self.store,id,policy,connection=db)
                review['status'] = 'ready' if review['proposal']['available'] else 'no_proposal'
            except (planning_history.PlanningConflict, LookupError):
                review.update(status='blocked', reason='계획 근거·범위·공유 할 일을 확인하세요.')
            self.store.put_many([('plan_reviews', review)], connection=db)

    def step(self):
        """Commit at most one event or25 asset-related tasks with its resume position."""
        policy = self.policy()
        digest = hashlib.sha256(json.dumps({'policy':policy,'automation_revision':AUTOMATION_REVISION}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with self.store.read_transaction() as db:
            saved = self.store.get('planner_state', STATE_ID, connection=db)
            if (saved is not None and saved.get('format') == FORMAT and type(saved.get('after')) is int
                    and saved['after'] >= 0 and saved.get('policy_fingerprint') == digest
                    and not self.store.events(after=saved['after'], limit=1, connection=db)):
                return False
        with self.store.write_transaction() as db:
            state = self.store.get('planner_state', STATE_ID, connection=db)
            if state is not None and (state.get('format') != FORMAT or type(state.get('after')) is not int
                                      or state['after'] < 0):
                raise ValueError('Invalid saved event planner position')
            if state is None or state.get('policy_fingerprint') != digest:
                state = {'id': STATE_ID, 'format': FORMAT, 'after': 0,
                         'policy_fingerprint': digest, 'fanout': None}
            events = self.store.events(after=state['after'], limit=1, connection=db)
            if not events:
                # Persist an empty initial position too, but do not write every idle poll.
                if self.store.get('planner_state', STATE_ID, connection=db) != state:
                    self.store.put_many([('planner_state', state)], connection=db)
                return False
            event = events[0]
            if event.get('task_id'):
                self.prepare(event['task_id'], event, policy, db)
                state['fanout'] = None
            elif isinstance(event.get('detail'), dict) and isinstance(event['detail'].get('asset_id'), str):
                fanout = state.get('fanout') or {'event_seq': event['seq'], 'offset': 0, 'snapshot': None}
                if (fanout.get('event_seq') != event['seq'] or type(fanout.get('offset')) is not int
                        or fanout['offset'] < 0 or (fanout.get('snapshot') is not None
                            and (type(fanout['snapshot']) is not int or fanout['snapshot'] < 0))):
                    raise ValueError('Invalid saved event planner fanout')
                page = self.store.page('tasks', limit=PAGE_SIZE, offset=fanout['offset'],
                                       snapshot=fanout['snapshot'], filters={'asset_id': event['detail']['asset_id']}, connection=db)
                for task in page['items']: self.prepare(task['id'], event, policy, db)
                if fanout['offset'] + len(page['items']) < page['total']:
                    state['fanout'] = {'event_seq': event['seq'], 'offset': fanout['offset'] + len(page['items']),
                                       'snapshot': page['snapshot']}
                    self.store.put_many([('planner_state', state)], connection=db)
                    return True
                state['fanout'] = None
            else:
                state['fanout'] = None
            state['after'] = event['seq']
            self.store.put_many([('planner_state', state)], connection=db)
            return True

    def review(self, task_id):
        """Readonly freshness check: a stored proposal never authorizes acceptance."""
        with self.store.read_transaction() as db:
            if self.store.get('tasks', task_id, connection=db) is None:
                raise LookupError('작업이 없습니다.')
            review = self.store.get('plan_reviews', task_id, connection=db)
            if review is None:
                return {'format': FORMAT, 'source_task_id': task_id, 'status': 'waiting',
                        'proposal': None, 'execution_authorized': False}
            if (review.get('format') != FORMAT or review.get('id') != task_id
                    or review.get('source_task_id') != task_id
                    or review.get('status') not in ('ready', 'no_proposal', 'blocked')
                    or type(review.get('event_seq')) is not int or review['event_seq'] < 1):
                return {'format': FORMAT, 'source_task_id': task_id, 'status': 'blocked',
                        'reason': '저장된 자동 계획 근거를 확인하세요.', 'proposal': None,
                        'stale': True, 'execution_authorized': False}
            try:
                fresh = next_plan.propose(self.store, task_id, self.policy(), connection=db)
                stale = not review.get('proposal') or fresh['fingerprint'] != review['proposal']['fingerprint']
            except (planning_history.PlanningConflict, LookupError):
                stale = review.get('status') != 'blocked'
            return {**review, 'stale': stale}
