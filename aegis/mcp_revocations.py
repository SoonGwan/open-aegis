"""Durable cancellation-only outbox. Never resume a potentially dispatched call."""
from contextlib import nullcontext
import hashlib
import hmac
import json
import threading

from .maintenance import WorkspaceBusy
from .mcp_process import cancel
from .mcp_scope import ScopeClaim, sign_claim, verify_claim
from .remote_mcp import _digest, _encode
from .store_util import now

KIND = 'mcp_revocations'


def due_key(timestamp):
    return str(int(timestamp * 1000)).zfill(20)


def prepare(attempt, token, key, contract):
    claim = verify_claim(token, key, attempt['server_id'])
    return {'id': attempt['id'], 'task_id': attempt['task_id'], 'created_at': now(),
            'ready': False, 'due_key': due_key(now()), 'tries': 0,
            'claim': claim.model_dump(), 'grant_sha256': attempt['grant_sha256'],
            'connection_contract': contract['connection_contract'],
            'key_sha256': contract['key_sha256']}


def remove(store, id, db):
    marker = '%s' if getattr(store, 'backend', None) == 'postgres' else '?'
    db.execute(f'DELETE FROM records WHERE kind={marker} AND id={marker}', (KIND, id))


def activate(store, attempt, db):
    row = store.get(KIND, attempt['id'], connection=db)
    if row and row.get('task_id') == attempt['task_id']:
        store.put_many([(KIND, {**row, 'ready': True, 'due_key': due_key(now())})], connection=db)


def candidates(store, timestamp):
    """Only due pending rows, bounded in SQL; no historical payload materialization."""
    native = getattr(store, 'backend', None) == 'postgres'
    ready = "data::jsonb->>'ready'='true'" if native else "json_extract(data,'$.ready')=1"
    due = "coalesce(data::jsonb->>'due_key','')" if native else "coalesce(json_extract(data,'$.due_key'),'')"
    marker = '%s' if native else '?'
    with store.read_transaction() as db:
        rows = db.execute(f'SELECT data FROM records WHERE kind={marker} AND {ready} '
                          f'AND {due}<={marker} ORDER BY {due},id LIMIT 10', (KIND, due_key(timestamp))).fetchall()
        return [json.loads(row['data']) for row in rows]


def recover_pending(store):
    """Recover dispatch cleanup even if a task's failure already committed.

    Runtime ownership is acquired before this startup phase. No live call from
    this owner exists yet; a dormant row cannot authorize execution or a GET.
    """
    native = getattr(store, 'backend', None) == 'postgres'
    marker = '%s' if native else '?'
    dormant = "data::jsonb->>'ready'='false'" if native else "json_extract(data,'$.ready')=0"
    with store.read_transaction() as db:
        upper = db.execute(f'SELECT coalesce(max(rowid),0) AS upper_bound FROM records WHERE kind={marker}', (KIND,)).fetchone()['upper_bound']
    before = upper + 1
    while True:
        with store.read_transaction() as db:
            rows = db.execute(f'SELECT rowid,id FROM records WHERE kind={marker} AND rowid<{marker} '
                              f'AND {dormant} ORDER BY rowid DESC LIMIT 100', (KIND, before)).fetchall()
        if not rows:return
        before = rows[-1]['rowid']
        with store.lock, store.write_transaction() as db:
            for row in rows:
                queue = store.get(KIND, row['id'], connection=db)
                if not queue or queue.get('ready') is not False:continue
                attempt = store.get('mcp_execution_attempts', row['id'], connection=db)
                if attempt and attempt.get('state') in ('dispatching', 'unconfirmed'):
                    if attempt['state'] == 'dispatching':
                        store.put_many([('mcp_execution_attempts', {**attempt, 'state': 'unconfirmed',
                            'finished_at': now(), 'termination_reason': 'source_restart'})], connection=db)
                    activate(store, attempt, db)
                    store.event(attempt['task_id'], '재시작 전 남은 원격 취소 의도를 복구했습니다.', 'warning',
                                {'attempt_id': row['id'], 'server_id': attempt.get('server_id')}, connection=db)
                else:
                    remove(store, row['id'], db)


class Recovery:
    def __init__(self, executors):
        self.executors, self.store = executors, executors.store
        self.stop = threading.Event()
        self.thread = None
        self.errors = 0
        self.last_error_at = None

    def start(self):
        if self.executors.configurations and self.thread is None:
            self.thread = threading.Thread(target=self.run, name='aegis-mcp-revocation', daemon=True)
            self.thread.start()

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join()

    def metrics(self):
        return {'alive': bool(self.thread and self.thread.is_alive()), 'errors': self.errors,
                'last_error_at': self.last_error_at, 'counter_scope': 'server_process'}

    def run(self):
        while not self.stop.is_set():
            try:
                for row in candidates(self.store, now()):
                    if self.stop.is_set():break
                    self.process(row)
            except Exception as error:
                self.errors += 1
                self.last_error_at = now()
                if isinstance(error, WorkspaceBusy):self.stop.set()
            self.stop.wait(.5)

    def process(self, row):
        """Reconstruct only the identical grant, bound to the original endpoint/key."""
        result, terminal, timestamp = None, None, now()
        original_attempt = None
        try:
            claim = ScopeClaim(**row['claim'])
            attempt = self.store.get('mcp_execution_attempts', row['id'])
            original_attempt = attempt
            if (not attempt or attempt.get('state') != 'unconfirmed' or row['ready'] is not True
                    or row['id'] != attempt['id'] or row['task_id'] != claim.task_id
                    or claim.task_id != attempt['task_id'] or claim.asset.id != attempt['asset_id']
                    or claim.check_id != attempt['check'] or claim.server_id != attempt['server_id']
                    or row['grant_sha256'] != attempt['grant_sha256']
                    or type(row['tries']) is not int or not 0 <= row['tries'] <= 8):
                raise ValueError('revocation_authority_changed')
            if claim.expires_at <= timestamp:
                terminal = 'authority_expired'
            elif row['tries'] >= 8:
                terminal = 'retry_limit'
            else:
                endpoint = self.executors.registry.connections[claim.server_id]
                key = self.executors._key(self.executors.configurations[claim.server_id])
                token = sign_claim(claim, key)
                if (row['connection_contract'] != self.executors.registry._contract(endpoint)
                        or row['key_sha256'] != hashlib.sha256(key).hexdigest()
                        or not hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), row['grant_sha256'])):
                    raise ValueError('revocation_configuration_changed')
                # Native runtime ownership must cover outbound cleanup too.
                with self.store.execution_permit() if getattr(self.store, 'backend', None) == 'postgres' else nullcontext():
                    if self.stop.is_set():return
                    try:
                        result = cancel(endpoint, token, stop=self.stop)
                        expected = {'format': 'aegis-mcp-cancellation-v1', 'grant_sha256': row['grant_sha256'], 'cancelled': True}
                        if _encode(result) != _encode(expected):raise RuntimeError('revocation_unconfirmed')
                    except WorkspaceBusy:
                        raise
                    except Exception:
                        raise RuntimeError('revocation_unconfirmed') from None
        except (ValueError, KeyError, TypeError, AttributeError):
            terminal = 'authority_or_configuration_changed'
        except WorkspaceBusy:
            raise
        except Exception:
            result = None
        if self.stop.is_set():return
        with self.store.lock, self.store.write_transaction() as db:
            current = self.store.get(KIND, row['id'], connection=db)
            attempt = self.store.get('mcp_execution_attempts', row['id'], connection=db)
            if current is None or _digest(current) != _digest(row):return
            if not attempt or attempt.get('state') != 'unconfirmed':
                remove(self.store, row['id'], db)
                return
            if original_attempt is not None and _digest(attempt) != _digest(original_attempt):return
            tries = row.get('tries', 0)
            tries = tries if type(tries) is int and 0 <= tries <= 8 else 0
            cancellation = {**attempt.get('cancellation', {}), 'state': 'unconfirmed',
                            'requested_at': now(), 'recovery_tries': tries + (0 if terminal else 1)}
            if result is not None:
                cancellation.update(state='acknowledged', acknowledged_at=now(), recovered=True)
            elif terminal:
                cancellation.update(recovery_reason=terminal)
            elif tries + 1 >= 8:
                terminal = 'retry_limit'
                cancellation.update(recovery_reason=terminal)
            self.store.put_many([('mcp_execution_attempts', {**attempt, 'cancellation': cancellation})], connection=db)
            if result is not None or terminal:
                remove(self.store, row['id'], db)
            else:
                self.store.put_many([(KIND, {**row, 'tries': tries + 1,
                    'due_key': due_key(min(claim.expires_at, now() + min(8, 2 ** tries)))})], connection=db)
            self.store.event(attempt['task_id'], '원격 취소 복구 확인을 기록했습니다.' if result is not None
                else '원격 취소 복구 확인을 받지 못했습니다.', 'info' if result is not None else 'warning',
                {'attempt_id': row['id'], 'server_id': attempt.get('server_id'), 'cancellation': cancellation}, connection=db)
