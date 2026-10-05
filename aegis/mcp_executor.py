"""Execution-side scope enforcement for the reviewed MCP GET profile."""
import hashlib
import os
from pathlib import Path
import sqlite3
import threading
import time

from .checks import run_check
from .mcp_scope import FORMAT, RequestLimits, ScopeGrantError, _key, verify_claim
from .network import Transport
from .remote_mcp import _encode
from .runtime import OriginLimiter, TaskControl
from .store import ClosingConnection
from .tool_contracts import PACKAGE_SHA256, validate_result


class ExecutionRejected(ValueError):
    pass


class NonceLedger:
    """Consume before network; retain through the whole approval authority window."""
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS consumed(nonce TEXT PRIMARY KEY, retain_until INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS cancelled(nonce TEXT PRIMARY KEY, retain_until INTEGER NOT NULL)')
        self.path.chmod(0o600)

    def connect(self):
        return sqlite3.connect(self.path, timeout=2, factory=ClosingConnection)

    def consume(self, claim):
        try:
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('DELETE FROM consumed WHERE retain_until<=?', (time.time(),))
                db.execute('DELETE FROM cancelled WHERE retain_until<=?', (time.time(),))
                if db.execute('SELECT count(*) FROM consumed').fetchone()[0] >= 10000:
                    raise ExecutionRejected('nonce_capacity')
                db.execute('INSERT INTO consumed(nonce,retain_until) VALUES (?,?)',
                           (claim.nonce, claim.authorization_expires_at))
        except sqlite3.IntegrityError:
            raise ExecutionRejected('scope_grant_consumed') from None
        except sqlite3.Error:
            raise ExecutionRejected('nonce_storage') from None

    def cancel(self, claim):
        try:
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('DELETE FROM consumed WHERE retain_until<=?', (time.time(),))
                db.execute('DELETE FROM cancelled WHERE retain_until<=?', (time.time(),))
                exists = db.execute('SELECT 1 FROM consumed WHERE nonce=?', (claim.nonce,)).fetchone()
                if not exists and db.execute('SELECT count(*) FROM consumed').fetchone()[0] >= 10000:
                    raise ExecutionRejected('nonce_capacity')
                db.execute('INSERT INTO consumed(nonce,retain_until) VALUES (?,?) '
                           'ON CONFLICT(nonce) DO UPDATE SET retain_until=max(retain_until,excluded.retain_until)',
                           (claim.nonce, claim.authorization_expires_at))
                db.execute('INSERT INTO cancelled(nonce,retain_until) VALUES (?,?) '
                           'ON CONFLICT(nonce) DO UPDATE SET retain_until=max(retain_until,excluded.retain_until)',
                           (claim.nonce, claim.authorization_expires_at))
        except sqlite3.Error:
            raise ExecutionRejected('nonce_storage') from None

    def cancelled(self, nonce):
        try:
            with sqlite3.connect(self.path, timeout=.1, factory=ClosingConnection) as db:
                return db.execute('SELECT 1 FROM cancelled WHERE nonce=?', (nonce,)).fetchone() is not None
        except sqlite3.Error:
            raise InterruptedError('원격 취소 상태를 확인할 수 없습니다.') from None


class CancellationControl(TaskControl):
    def __init__(self, runner, claim, deadline):
        super().__init__(deadline=deadline)
        self.runner, self.nonce = runner, claim.nonce
        self.poll_lock = threading.Lock()

    def check(self):
        super().check()
        if self.runner.stop.is_set():
            raise InterruptedError('원격 서버가 중지됐습니다.')
        with self.poll_lock:
            if self.runner.ledger.cancelled(self.nonce):
                self.stop.set()
                raise InterruptedError('원격 작업이 취소됐습니다.')


class Runner:
    def __init__(self, server_id, key, ledger_path, *, allow_private=False, credential_envs=(), ceiling=None, protected_values=()):
        self.server_id, self._key = server_id, _key(key)
        self.ledger = NonceLedger(ledger_path)
        self.allow_private = allow_private
        self.credential_envs = frozenset(credential_envs)
        self._protected_values = tuple(protected_values)
        self.ceiling = ceiling or RequestLimits()
        self.limiter = OriginLimiter(self.ceiling.execution_policy())
        self.stop = threading.Event()
        self.gate = threading.Lock()

    def cancel(self, token):
        try:
            claim = verify_claim(token, self._key, self.server_id)
        except ScopeGrantError:
            raise ExecutionRejected('scope_authority') from None
        self.ledger.cancel(claim)
        return {'format': 'aegis-mcp-cancellation-v1',
                'grant_sha256': hashlib.sha256(token.encode()).hexdigest(), 'cancelled': True}

    def execute(self, name, arguments):
        if not isinstance(arguments, dict) or set(arguments) != {'grant'}:
            raise ExecutionRejected('execution_arguments')
        try:
            claim = verify_claim(arguments['grant'], self._key, self.server_id)
        except ScopeGrantError:
            raise ExecutionRejected('scope_authority') from None
        if name != 'validate_' + claim.check_id:
            raise ExecutionRejected('scope_tool')
        names = {rule.credential_env for rule in claim.asset.authorization_rules if rule.credential_env}
        if not names <= self.credential_envs:
            raise ExecutionRejected('credential_permission')
        protected = [self._key.decode('utf-8', errors='ignore'), *self._protected_values]
        for env in names:
            value = os.environ.get(env, '')
            if (not value or len(value) > 4096 or any(not 32 <= ord(c) <= 126 for c in value)
                    or any(secret and secret in value for secret in protected)):
                raise ExecutionRejected('credential_configuration')
        if not self.gate.acquire(blocking=False):
            raise ExecutionRejected('execution_busy')
        try:
            limits = claim.limits.effective(self.ceiling)
            # The execution gate serializes jobs, so the shared origin clock can
            # safely use this job's tighter limits while retaining prior starts.
            self.limiter.policy = limits.execution_policy()
            control = CancellationControl(self, claim,
                time.monotonic() + min(limits.task_timeout, claim.expires_at - time.time()))
            control.check()
            self.ledger.consume(claim)
            # Scope, DNS pinning, TLS and redirect checks apply to every GET,
            # including requests made by API authorization validation.
            traffic = []
            def record(row):
                traffic.append({k: row[k] for k in ('url', 'method', 'status', 'elapsed_ms', 'bytes',
                                                   'body_sha256', 'truncated', 'address', 'attempt') if k in row})
            asset = claim.asset.model_dump()
            transport = Transport(asset['url'], self.allow_private and claim.allow_private,
                                  record=record, control=control, policy=limits.execution_policy(),
                                  limiter=self.limiter)
            response = transport.get()
            if not 200 <= response['status'] < 300:
                raise ExecutionRejected('target_unconfirmed')
            result = validate_result(claim.check_id, asset, run_check(claim.check_id, asset, transport, response))
            control.check()
            output = {'format': FORMAT, 'grant_sha256': hashlib.sha256(arguments['grant'].encode()).hexdigest(),
                      'task_id': claim.task_id, 'asset_id': asset['id'], 'asset_revision': asset['revision'],
                      'check_id': claim.check_id, 'scope_url': asset['url'], 'package_sha256': PACKAGE_SHA256,
                      'allow_private': self.allow_private and claim.allow_private,
                      'effective_limits': limits.model_dump(), 'result': list(result), 'traffic': traffic}
            # Do not emit known server secrets reflected by a target response.
            secrets = [self._key.decode('utf-8', errors='ignore'), *self._protected_values,
                       *[os.environ.get(env, '') for env in names]]
            stack = [output]
            while stack:
                item = stack.pop()
                if isinstance(item, str) and any(secret and secret in item for secret in secrets):
                    raise ExecutionRejected('secret_reflection')
                if isinstance(item, dict):
                    stack.extend(item.keys()); stack.extend(item.values())
                elif isinstance(item, list):
                    stack.extend(item)
            _encode(output)
            return output
        except ExecutionRejected:
            raise
        except Exception:
            raise ExecutionRejected('execution_unconfirmed') from None
        finally:
            self.gate.release()
