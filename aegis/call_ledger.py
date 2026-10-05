"""Durable provider attempts, separate from committed planner/message records."""
import json
from contextlib import contextmanager
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


@contextmanager
def write(store):
    native=getattr(store,'backend',None)=='postgres'
    with store.lock:
        if native:
            with store.transaction(write=True) as db:
                yield db,True
        else:
            with store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                yield db,False


def save(db, record, *, postgres=False):
    query=("UPDATE records SET data=%s WHERE kind='llm_calls' AND id=%s" if postgres else
           "UPDATE records SET data=? WHERE kind='llm_calls' AND id=?")
    db.execute(query,(json.dumps(record,ensure_ascii=False,allow_nan=False),record['id']))


def event(db, record, message, *, postgres=False):
    append=append_event
    if postgres:
        from .postgres_store import append_event as append
    append(db,(now(),record['task_id'],'info',message,json.dumps(record,ensure_ascii=False,allow_nan=False)))


def start(store, source, task_id, model, base, started_at, price, actor_id=None, *, prompt_snapshot=None, model_profile_snapshot=None):
    record = {'id':identifier(), 'source':source, 'task_id':task_id, 'actor_id':actor_id,
              'model':model, 'provider_origin':origin(base), 'started_at':started_at,
              'observed_at':started_at, 'state':'started', 'outcome':'unknown',
              'tokens':token_usage(None)}
    if prompt_snapshot is not None:
        record['prompt_snapshot']=prompt_snapshot
    if model_profile_snapshot is not None:
        record['model_profile_snapshot']=model_profile_snapshot
    record['cost']=estimate(record['tokens'],price,started_at)
    with write(store) as (db,native):
        query=("INSERT INTO records(kind,id,data) VALUES ('llm_calls',%s,%s)" if native else
               "INSERT INTO records(kind,id,data) VALUES ('llm_calls',?,?)")
        db.execute(query,(record['id'],json.dumps(record,ensure_ascii=False,allow_nan=False)))
        event(db,record,'AI 호출 시도 시작',postgres=native)
    return record['id']


def observe(store, call_id, detail):
    with write(store) as (db,native):
        record=load(db,call_id,postgres=native)
        if record['state']!='started':
            raise RuntimeError('Provider attempt is not awaiting observation')
        if (detail['model']!=record['model'] or detail['started_at']!=record['started_at'] or
                detail.get('prompt_snapshot') != record.get('prompt_snapshot') or
                detail.get('model_profile_snapshot') != record.get('model_profile_snapshot')):
            raise RuntimeError('Provider attempt metadata mismatch')
        record.update({key:detail[key] for key in ('outcome','tokens','cost','observed_at')})
        record['state']='observed'
        save(db,record,postgres=native)
        event(db,record,'AI 호출 응답 관찰 기록',postgres=native)


def load(db, call_id, *, postgres=False):
    query=("SELECT data FROM records WHERE kind='llm_calls' AND id=%s" if postgres else
           "SELECT data FROM records WHERE kind='llm_calls' AND id=?")
    row=db.execute(query,(call_id,)).fetchone()
    if row is None:
        raise RuntimeError('Provider attempt is missing')
    return json.loads(row['data'] if postgres else row[0])


def commit(db, detail, task_id, source, record_kind, record_id, *, postgres=False):
    call_id=detail.get('call_id')
    if not call_id:
        return  # Legacy, explicitly stored synthetic fixtures have no attempt record.
    record=load(db,call_id,postgres=postgres)
    if (record['state']!='observed' or record['task_id']!=task_id or record['source']!=source or
            detail.get('prompt_snapshot') != record.get('prompt_snapshot') or
            detail.get('model_profile_snapshot') != record.get('model_profile_snapshot') or
            any(record[key]!=detail[key] for key in ('model','outcome','tokens','cost','started_at','observed_at'))):
        raise RuntimeError('Committed result does not match provider attempt')
    record.update(state='committed',record_kind=record_kind,record_id=record_id,settled_at=now())
    save(db,record,postgres=postgres)  # Planner/message audit commits in this transaction.


def abandon(store, call_id):
    if not call_id:
        return
    with write(store) as (db,native):
        record=load(db,call_id,postgres=native)
        if record['state'] not in ('started','observed'):
            return
        record.update(state='uncommitted',settled_at=now(),settlement_reason='result_not_committed')
        save(db,record,postgres=native)
        event(db,record,'AI 호출 결과를 계획·답변에 저장하지 못했습니다.',postgres=native)


def recover(store):
    """Only under the server's exclusive startup lease; never in Store constructors."""
    while True:
        with write(store) as (db,native):
            state="data::jsonb->>'state'" if native else "json_extract(data,'$.state')"
            rows=db.execute("SELECT data FROM records WHERE kind='llm_calls' AND "+state+
                            " IN ('started','observed') ORDER BY rowid LIMIT 100").fetchall()
            for row in rows:
                record=json.loads(row['data'] if native else row[0])
                record.update(state='interrupted',settled_at=now(),settlement_reason='server_restart')
                save(db,record,postgres=native)
                event(db,record,'재시작으로 AI 호출 결과 저장 여부를 확인할 수 없습니다.',postgres=native)
        if not rows:
            return
