"""Recorded, cited summaries. This reader never executes tools or calls a provider."""
import json
from .coverage import iter_task_rows
from .store_util import now


def summarize_task(store, task_id, content):
    # An insertion watermark is insufficient: concurrent updates to existing rows
    # must not mix a task state from one moment with findings from another.
    with store.connect() as db:
        db.execute('BEGIN')
        task = store.get('tasks', task_id, connection=db)
        if task is None:
            return None
        observed_at = now()
        findings_page = store.page('findings', limit=8, filters={'task_id':task_id},
                                   compact_findings=True, priority=True, connection=db)
        findings = findings_page['items']
        completed_checks = sum(row['status'] == 'completed' for row in iter_task_rows(
            store, task, get_record=lambda kind, key: store.get(kind, key, connection=db)))
        task_snapshot = {'status':task['status'], 'assets':len(task['asset_ids']),
                         'done':task['done'], 'completed_checks':completed_checks,
                         'errors':task['errors']}
        citations = [{'label':'작업', 'kind':'task', 'id':task_id,
                      'title':task.get('name', task_id), 'snapshot':task_snapshot}]
        answer = [f"[작업] 작업 상태: {task['status']}. {len(task['asset_ids'])}개 자산 중 {task['done']}개 처리, {completed_checks}개 검증 완료, {task['errors']}개 오류입니다."]
        if task['status'] == 'pending':
            answer.append('아직 대상 요청을 보내지 않았습니다. 실행 범위를 확인한 후 승인하세요.')
        remediation = any(word in content for word in ('수정', '조치', '우선', '해결'))
        for index, finding in enumerate(findings, 1):
            label = f'발견 {index}'
            fields = ('severity', 'asset_name', 'remediation') if remediation else ('severity', 'confidence', 'status')
            proofs = store.page('evidence', limit=1,
                                filters={'finding_id':finding['id'], 'task_id':task_id},
                                connection=db)
            evidence = None
            if proofs['items']:
                proof = proofs['items'][0]
                if (type(proof.get('observation')) is dict and
                        all(type(proof.get(key)) is str for key in ('id','task_id','asset_id','check')) and
                        type(proof.get('created_at')) in (int,float) and
                        0 <= proof['created_at'] <= 8_640_000_000_000):
                    excerpt = json.dumps(proof['observation'], ensure_ascii=False, indent=2)
                    evidence = {key:proof[key] for key in ('id', 'task_id', 'asset_id', 'check', 'created_at')}
                    evidence.update(label=f'증거 {index}', excerpt=excerpt[:4096],
                                    truncated=len(excerpt)>4096, matching_count=proofs['total'])
            citations.append({'label':label, 'kind':'finding', 'id':finding['id'],
                              'title':finding['title'],
                              'snapshot':{key:finding[key] for key in fields}, 'evidence':evidence})
            if remediation:
                answer.append(f"[{label}] [{finding['severity'].upper()}] {finding['title']} ({finding['asset_name']}): {finding['remediation']}")
            else:
                answer.append(f"[{label}] [{finding['severity'].upper()}] {finding['title']} · 판정 유형: {finding['confidence']} · 상태: {finding['status']}")
            answer.append(f"[증거 {index}] 이 작업의 저장된 관찰 기록을 인용했습니다." if evidence else
                          f"[{label}] 이 작업과 출처가 일치하는 관찰 증거를 확인할 수 없습니다.")
        if not findings:
            answer.append('이 작업에 연결된 발견 사항이 없습니다. 미실행·검증 실패·미지원 취약점은 별도로 확인해야 합니다.')
        elif findings_page['total'] > len(findings):
            answer.append(f"연결된 발견 사항 {findings_page['total']}개 중 우선순위가 높은 {len(findings)}개를 인용했습니다. 전체 목록도 확인하세요.")
        answer.append('이 답변은 저장된 작업·증거의 규칙 기반 요약입니다. 추가 요청이나 명령을 실행하지 않습니다.')
        return {'content':'\n\n'.join(answer), 'finding_ids':[f['id'] for f in findings],
                'provenance':{'version':1, 'mode':'recorded_rules', 'observed_at':observed_at,
                              'finding_total':findings_page['total'], 'citations':citations}}
