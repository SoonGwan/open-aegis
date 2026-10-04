"""Finding observations and human decisions share one serialized, atomic write path."""
import hashlib
from .store_util import identifier, now


class TriageConflict(ValueError):
    pass


def public_actor(user=None, task_id=None):
    if user:
        return {'kind':'user', **{key:user[key] for key in ('id','username','name','role')}}
    return {'kind':'system','name':'검증 엔진','task_id':task_id}


def value(record, key):
    if key == 'status':
        return record.get(key)
    return record.get(key) or None


def history(finding, action, actor, before, after, reason='', **details):
    changes = {key:{'before':before.get(key),'after':after.get(key)}
               for key in ('status','assignee_id','assignee_name','assignee_username','acceptance_reason','resolution_reason')
               if value(before,key)!=value(after,key)}
    return {'id':identifier(),'finding_id':finding['id'],'action':action,'actor':actor,
            'changes':changes,'reason':reason,'created_at':now(), **details}


def update_triage(store, finding_id, changes, user):
    with store.lock, store.write_transaction() as db:
        before = store.get('findings', finding_id,connection=db)
        if before is None:
            raise KeyError(finding_id)
        revision = before.get('triage_revision', 1)
        expected = changes.pop('expected_revision', None)
        if expected is None:
            raise ValueError('현재 조치 기록의 기준 버전을 함께 보내세요.')
        if expected != revision:
            raise TriageConflict('다른 사용자 또는 재검증이 조치 상태를 변경했습니다. 최신 기록을 확인한 뒤 다시 저장하세요.')
        after = {**before, **changes}
        if after.get('status') == 'accepted' and not after.get('acceptance_reason', '').strip():
            raise ValueError('위험을 수용하는 사유를 입력하세요.')
        if changes.get('status') == 'accepted' and before['status'] != 'accepted' and not changes.get('acceptance_reason'):
            raise ValueError('이번 위험 수용 결정의 사유를 입력하세요.')
        if changes.get('status') == 'resolved' and before['status'] != 'resolved' and not changes.get('resolution_reason'):
            raise ValueError('수동으로 해결 처리하는 사유를 입력하세요. 검증 결과는 재검증으로 확인할 수 있습니다.')
        if 'assignee_id' in changes and changes['assignee_id'] != before.get('assignee_id'):
            assignee = store.user(id=changes['assignee_id'],connection=db) if changes['assignee_id'] else None
            if changes['assignee_id'] and (not assignee or assignee['disabled'] or assignee['role'] not in ('admin','operator')):
                raise ValueError('활성 관리자 또는 운영자를 담당자로 선택하세요.')
            after['assignee_name'] = assignee['name'] if assignee else ''
            after['assignee_username'] = assignee['username'] if assignee else ''
        meaningful = any(value(before,key) != value(after,key) for key in changes)
        if not meaningful:
            return before
        after.update(triage_revision=revision+1, triage_updated_at=now(), updated_at=now())
        reason = after.get('acceptance_reason','') if after['status']=='accepted' else after.get('resolution_reason','') if after['status']=='resolved' else '운영자가 조치 기록을 변경했습니다.'
        entry = history(after,'triage',public_actor(user),before,after,reason)
        store.put_many([('findings',after),('finding_history',entry)],connection=db)
        return after


def record_observation(store, task, asset, item):
    fingerprint = hashlib.sha256(f"{asset['id']}:{item['check']}:{item['code']}".encode()).hexdigest()
    with store.lock, store.write_transaction() as db:
        previous = store.finding_by_fingerprint(fingerprint,connection=db)
        proof = {'id':identifier(),'task_id':task['id'],'asset_id':asset['id'],'check':item['check'],
                 'observation':item['evidence'],'created_at':now(),'fingerprint':fingerprint}
        finding = {**(previous or {}), **item, 'id':previous['id'] if previous else identifier(),
                   'asset_id':asset['id'],'asset_name':asset['name'],'fingerprint':fingerprint,
                   'status':previous['status'] if previous else 'open',
                   'task_ids':list(dict.fromkeys((previous.get('task_ids',[]) if previous else [])+[task['id']])),
                   'evidence_ids':(previous.get('evidence_ids',[]) if previous else [])+[proof['id']],
                   'created_at':previous['created_at'] if previous else now(),'updated_at':now(),
                   'triage_revision':previous.get('triage_revision',1) if previous else 1}
        reason = '같은 발견을 다시 관찰했습니다.' if previous else '새 발견과 원본 증거를 기록했습니다.'
        action = 'observed' if previous else 'detected'
        if previous and previous['status']=='resolved' and task.get('retest_of')!=previous['id']:
            if previous.get('triage_updated_at',0) <= (task.get('approved_at') or task['created_at']):
                finding.update(status='open',triage_revision=finding['triage_revision']+1,triage_updated_at=now())
                action, reason = 'reopened','동일한 발견이 다시 관찰되어 미조치 상태로 돌렸습니다.'
            else:
                reason = '작업 승인 이후의 조치 결정을 보존하고 관찰 증거만 추가했습니다.'
        entry = history(finding,action,public_actor(task_id=task['id']),previous or {},finding,reason,
                        task_id=task['id'],evidence_id=proof['id'])
        store.put_many([('evidence',proof),('findings',finding),('finding_history',entry)],connection=db)
    return finding, proof, entry


def apply_retest(store, task, conclusion):
    with store.lock, store.write_transaction() as db:
        before = store.get('findings', task['retest_of'],connection=db)
        if before is None:
            raise KeyError(task['retest_of'])
        after = dict(before)
        effect, note = 'unchanged','판정 결과를 기록하고 기존 조치 상태를 유지했습니다.'
        if conclusion != 'inconclusive':
            expected = task.get('retest_triage_revision')
            if expected is None or expected != before.get('triage_revision',1):
                effect, note = 'conflict','계획 생성 이후 조치 상태가 변경되었거나 기준 버전이 없어 판정 결과만 기록했습니다.'
            elif conclusion=='resolved':
                if before['status']!='resolved':
                    after.update(status='resolved',resolution_reason='승인된 재검증에서 해당 발견이 다시 관찰되지 않았습니다.')
                else:
                    note='재검증에서도 해결된 상태를 확인했습니다. 기존 조치 사유를 유지했습니다.'
            elif before['status']=='accepted':
                note = '문제가 재현되었으며 기존 위험 수용 결정을 유지했습니다.'
            else:
                after['status']='open'
        if after['status'] != before['status']:
            after.update(triage_revision=before.get('triage_revision',1)+1,triage_updated_at=now(),updated_at=now())
            effect, note = 'changed','재검증의 관찰 결과에 따라 조치 상태를 변경했습니다.'
        retest = {'id':identifier(),'finding_id':before['id'],'task_id':task['id'],'conclusion':conclusion,
                  'created_at':now(),'triage_effect':effect,'state_note':note}
        entry = history(after,'retest',public_actor(task_id=task['id']),before,after,note,
                        task_id=task['id'],retest_id=retest['id'],conclusion=conclusion,triage_effect=effect)
        store.put_many([('findings',after),('retests',retest),('finding_history',entry)],connection=db)
        return retest
