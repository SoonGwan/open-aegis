"""Hash-linked audit records. Integrity evidence, not a signature or authorization proof."""
import hashlib
import json
import math
import secrets
import sqlite3

GENESIS = '0' * 64
FORMAT = 'aegis-audit-v1'


class AuditIntegrityError(ValueError):
    pass


def hexadecimal(value, length):
    return isinstance(value, str) and len(value) == length and all(c in '0123456789abcdef' for c in value)


def validate_state(state):
    if (not state or not hexadecimal(state['chain_id'], 32) or
        not hexadecimal(state['head_hash'], 64) or
        type(state['last_seq']) is not int or state['last_seq'] < 0 or
        type(state['sealed_legacy_until']) is not int or
        not 0 <= state['sealed_legacy_until'] <= state['last_seq']):
        raise AuditIntegrityError('감사 로그 기준 기록의 형식이 올바르지 않습니다.')


def event_hash(row, previous):
    if type(row['seq']) is not int or row['seq'] <= 0:
        raise AuditIntegrityError('감사 로그 seq는 양의 정수여야 합니다.')
    if (not hexadecimal(previous, 64) or type(row['ts']) not in (int, float) or
        not math.isfinite(row['ts']) or
        any(row[key] is not None and not isinstance(row[key], str)
            for key in ('task_id', 'level', 'message', 'detail'))):
        raise AuditIntegrityError(f"감사 로그 기록 형식이 올바르지 않습니다: seq={row['seq']}")
    payload = [previous, *[row[key] for key in ('seq', 'ts', 'task_id', 'level', 'message', 'detail')]]
    try:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    except (TypeError, ValueError, UnicodeError) as exc:
        raise AuditIntegrityError(f"감사 로그 기록을 인코딩할 수 없습니다: seq={row['seq']}") from exc
    return hashlib.sha256(encoded).hexdigest()


def initialize_chain(db):
    db.execute('CREATE TABLE audit_state (id INTEGER PRIMARY KEY CHECK(id=1), chain_id TEXT NOT NULL, last_seq INTEGER NOT NULL, head_hash TEXT NOT NULL, sealed_legacy_until INTEGER NOT NULL)')
    db.execute('CREATE TABLE event_hashes (seq INTEGER PRIMARY KEY REFERENCES events(seq), previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL)')
    previous, last = GENESIS, 0
    db.row_factory = sqlite3.Row
    for row in db.execute('SELECT * FROM events ORDER BY seq'):
        digest = event_hash(row, previous)
        db.execute('INSERT INTO event_hashes VALUES (?,?,?)', (row['seq'], previous, digest))
        previous, last = digest, row['seq']
    db.execute('INSERT INTO audit_state VALUES (1,?,?,?,?)', (secrets.token_hex(16), last, previous, last))


def append_event(db, values):
    # A database write transaction covers sequence allocation, link and local head.
    db.execute('BEGIN IMMEDIATE')
    state = db.execute('SELECT * FROM audit_state WHERE id=1').fetchone()
    validate_state(state)
    tail = db.execute('SELECT * FROM events ORDER BY seq DESC LIMIT 1').fetchone()
    last = tail['seq'] if tail else 0
    link = db.execute('SELECT * FROM event_hashes WHERE seq=?', (last,)).fetchone()
    if state['last_seq'] != last or state['head_hash'] != (link['event_hash'] if link else GENESIS):
        raise AuditIntegrityError('감사 로그의 마지막 기록이 일치하지 않습니다.')
    if tail:
        prior = db.execute('SELECT h.event_hash FROM events e LEFT JOIN event_hashes h ON h.seq=e.seq WHERE e.seq<? ORDER BY e.seq DESC LIMIT 1', (last,)).fetchone()
        previous = prior['event_hash'] if prior else GENESIS
        if not link or link['previous_hash'] != previous or event_hash(tail, previous) != link['event_hash']:
            raise AuditIntegrityError(f'감사 로그의 마지막 연결이 일치하지 않습니다: seq={last}')
    cursor = db.execute('INSERT INTO events(ts,task_id,level,message,detail) VALUES (?,?,?,?,?)', values)
    row = db.execute('SELECT * FROM events WHERE seq=?', (cursor.lastrowid,)).fetchone()
    digest = event_hash(row, state['head_hash'])
    db.execute('INSERT INTO event_hashes VALUES (?,?,?)', (row['seq'], state['head_hash'], digest))
    db.execute('UPDATE audit_state SET last_seq=?,head_hash=? WHERE id=1', (row['seq'], digest))


def verify_chain(db, checkpoint=None):
    """Caller owns a consistent read transaction; stream rows without collecting history."""
    state = db.execute('SELECT * FROM audit_state WHERE id=1').fetchone()
    validate_state(state)
    if checkpoint is not None:
        if (not isinstance(checkpoint, dict) or checkpoint.get('format') != FORMAT or
            checkpoint.get('chain_id') != state['chain_id'] or
            type(checkpoint.get('seq')) is not int or checkpoint['seq'] < 0 or
            not hexadecimal(checkpoint.get('hash'), 64)):
            raise AuditIntegrityError('외부 체크포인트 형식 또는 로그 ID가 일치하지 않습니다.')
    previous, last, count = GENESIS, 0, 0
    matched = checkpoint is None or (checkpoint['seq'] == 0 and checkpoint['hash'] == GENESIS)
    legacy_found = state['sealed_legacy_until'] == 0
    for row in db.execute('SELECT e.*,h.previous_hash,h.event_hash FROM events e LEFT JOIN event_hashes h ON h.seq=e.seq ORDER BY e.seq'):
        digest = event_hash(row, previous)
        if row['previous_hash'] != previous or row['event_hash'] != digest:
            raise AuditIntegrityError(f"감사 로그 연결 검증에 실패했습니다: seq={row['seq']}")
        previous, last, count = digest, row['seq'], count + 1
        if row['seq'] == state['sealed_legacy_until']:
            legacy_found = True
        if checkpoint is not None and row['seq'] == checkpoint['seq']:
            matched = digest == checkpoint['hash']
    if state['last_seq'] != last or state['head_hash'] != previous:
        raise AuditIntegrityError('감사 로그 기준과 마지막 기록이 일치하지 않습니다.')
    if not legacy_found:
        raise AuditIntegrityError('감사 로그 봉인 기준에 해당하는 기록이 없습니다.')
    if db.execute('SELECT 1 FROM event_hashes h LEFT JOIN events e ON e.seq=h.seq WHERE e.seq IS NULL LIMIT 1').fetchone():
        raise AuditIntegrityError('원본이 없는 감사 로그 연결이 있습니다.')
    if not matched:
        raise AuditIntegrityError('외부 체크포인트를 현재 로그에서 확인할 수 없습니다.')
    return {'valid': True, 'events': count, 'sealed_legacy_until': state['sealed_legacy_until'],
            'checkpoint': {'format': FORMAT, 'chain_id': state['chain_id'], 'seq': last, 'hash': previous}}
