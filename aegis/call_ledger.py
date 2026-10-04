"""Durable provider attempts, separate from committed planner/message records."""
import json
from urllib.parse import urlsplit
from .audit import append_event
from .store_util import identifier, now
from .llm import token_usage
from .costs import estimate


def origin(base):
    try:
        parsed = urlsplit(base)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            return None
        host = '['+parsed.hostname+']' if ':' in parsed.hostname else parsed.hostname
        return parsed.scheme+'://'+host+(':'+str(parsed.port) if parsed.port else '')
    except ValueError:
        return None


def save(db, record):
    db.execute("UPDATE records SET data=? WHERE kind='llm_calls' AND id=?",
               (json.dumps(record,ensure_ascii=False),record['id']))


def event(db, record, message):
    append_event(db,(now(),record['task_id'],'info',message,json.dumps(record,ensure_ascii=False)))


def start(store, source, task_id, model, base, started_at, price, actor_id=None):
    record = {'id':identifier(), 'source':source, 'task_id':task_id, 'actor_id':actor_id,
              'model':model, 'provider_origin':origin(base), 'started_at':started_at,
              'observed_at':started_at, 'state':'started', 'outcome':'unknown',
              'tokens':token_usage(None)}
    record['cost']=estimate(record['tokens'],price,started_at)
    with store.lock, store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute("INSERT INTO records VALUES ('llm_calls',?,?)",
                   (record['id'],json.dumps(record,ensure_ascii=False)))
        event(db,record,'AI 호출 시도 시작')
    return record['id']


def observe(store, call_id, detail):
    with store.lock, store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        record=load(db,call_id)
        if record['state']!='started':
            raise RuntimeError('Provider attempt is not awaiting observation')
        if detail['model']!=record['model'] or detail['started_at']!=record['started_at']:
            raise RuntimeError('Provider attempt metadata mismatch')
        record.update({key:detail[key] for key in ('outcome','tokens','cost','observed_at')})
        record['state']='observed'
        save(db,record)
        event(db,record,'AI 호출 응답 관찰 기록')


def load(db, call_id):
    row=db.execute("SELECT data FROM records WHERE kind='llm_calls' AND id=?",(call_id,)).fetchone()
    if row is None:
        raise RuntimeError('Provider attempt is missing')
    return json.loads(row[0])


def commit(db, detail, task_id, source, record_kind, record_id):
    call_id=detail.get('call_id')
    if not call_id:
        return  # Legacy, explicitly stored synthetic fixtures have no attempt record.
    record=load(db,call_id)
    if (record['state']!='observed' or record['task_id']!=task_id or record['source']!=source or
            any(record[key]!=detail[key] for key in ('model','outcome','tokens','cost','started_at','observed_at'))):
        raise RuntimeError('Committed result does not match provider attempt')
    record.update(state='committed',record_kind=record_kind,record_id=record_id,settled_at=now())
    save(db,record)  # Existing planner/message audit event commits in this same transaction.


def abandon(store, call_id):
    if not call_id:
        return
    with store.lock, store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        record=load(db,call_id)
        if record['state'] not in ('started','observed'):
            return
        record.update(state='uncommitted',settled_at=now(),settlement_reason='result_not_committed')
        save(db,record)
        event(db,record,'AI 호출 결과를 계획·답변에 저장하지 못했습니다.')


def recover(store):
    """Only under the server's exclusive startup lease; never in Store constructors."""
    while True:
        with store.lock, store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows=db.execute("SELECT data FROM records WHERE kind='llm_calls' "
                            "AND json_extract(data,'$.state') IN ('started','observed') LIMIT 100").fetchall()
            for row in rows:
                record=json.loads(row[0])
                record.update(state='interrupted',settled_at=now(),settlement_reason='server_restart')
                save(db,record)
                event(db,record,'재시작으로 AI 호출 결과 저장 여부를 확인할 수 없습니다.')
        if not rows:
            return
