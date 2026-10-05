"""Atomic, task-bound admission of reviewed remote GET results.

Internal integration primitive; neither arbitrary RPC input nor an execution API.
"""
import hashlib
import hmac

from .coverage import slot
from .findings import record_observation
from .goal_planner import execution_checks
from .mcp_execution_result import validate_execution_response
from .mcp_scope import issue_grant, verify_claim
from .remote_mcp import _decode, _encode
from .store_util import identifier, now
from .tool_contracts import require_contracts
from .worker_observations import record_link


class AdmissionError(ValueError):
    pass


AUTHORITY_FIELDS = ('id', 'approved_at', 'plan', 'asset_ids', 'scope_snapshot', 'checks', 'tool_contracts',
                    'execution_policy', 'worker_dependencies', 'worker_dependency_contract',
                    'goal_plan', 'goal_selection', 'goal_selection_contract',
                    'observation_execution', 'observation_execution_contract', 'worker_observation_context',
                    'observation_cells', 'goal_observation', 'observation_selection',
                    'remote_execution', 'remote_connection_id')


def admit(store, task, asset_id, check_id, token, key, server_id, response, *,
          ceiling=None, allow_private=False, protected_values=(), attempt_id=None, control=None):
    """Validate completely, then commit receipt/evidence/coverage/audit together.

Replaying an identical still-valid response returns its original receipt. A
receipt is proof of local admission, not remote runtime or target attestation.
    """
    try:
        task = _decode(_encode(task))
        output = validate_execution_response(token, key, server_id, response,
                                             ceiling=ceiling, allow_private=allow_private)
        claim = verify_claim(token, key, server_id)
        if task.get('remote_execution') and not attempt_id:
            raise ValueError()
        if (claim.task_id != task['id'] or claim.asset.id != asset_id or claim.check_id != check_id
                or bool(claim.observation) != bool(task.get('observation_execution'))):
            raise ValueError()
        expected = issue_grant(task, asset_id, check_id, server_id, key,
                               ttl=claim.expires_at - claim.issued_at, timestamp=claim.issued_at,
                               allow_private=claim.allow_private, request_budget=claim.limits.request_budget)
        if not hmac.compare_digest(token, expected):
            raise ValueError()
        secrets = (key.decode('utf-8', errors='ignore'), token, *protected_values)
        if any(not isinstance(value, str) for value in secrets):
            raise ValueError()
        pending = [output]
        while pending:
            value = pending.pop()
            if isinstance(value, str) and any(secret and secret in value for secret in secrets):
                raise ValueError()
            if isinstance(value, dict):
                pending.extend(value.keys()); pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
        result_sha = hashlib.sha256(_encode(output)).hexdigest()
        authority = {name: task.get(name) for name in AUTHORITY_FIELDS}
        authority_sha = hashlib.sha256(_encode(authority)).hexdigest()
        receipt_id = hashlib.sha256(_encode([task['id'], asset_id, check_id, server_id])).hexdigest()
    except (ValueError, TypeError, KeyError, AttributeError):
        raise AdmissionError('remote_result_not_admitted') from None

    # The shared write connection is passed through every evidence helper. No
    # helper commits a nested transaction or leaves an orphan on audit failure.
    with store.lock, store.write_transaction() as db:
        if control:
            control.check()
        existing = store.get('mcp_execution_receipts', receipt_id, connection=db)
        if existing is not None:
            identity = {'id': receipt_id, 'format': 'aegis-mcp-admission-v1', 'task_id': task['id'],
                        'asset_id': asset_id, 'asset_revision': claim.asset.revision,
                        'check': check_id, 'server_id': server_id}
            if (not isinstance(existing, dict)
                    or _encode({name: existing.get(name) for name in identity}) != _encode(identity)
                    or existing.get('grant_sha256') != output['grant_sha256']
                    or existing.get('result_sha256') != result_sha
                    or existing.get('authority_sha256') != authority_sha):
                raise AdmissionError('remote_result_conflict')
            return existing
        current = store.get('tasks', task['id'], connection=db)
        if (not current or current.get('status') != 'running'
                or _encode({name: current.get(name) for name in AUTHORITY_FIELDS}) != _encode(authority)
                or (not claim.observation and check_id not in execution_checks(current, asset_id))):
            raise AdmissionError('task_authority_changed')
        require_contracts(current)
        if claim.observation:
            from .observation_execution import require
            require(current, approved=True)
        attempt = store.get('mcp_execution_attempts', attempt_id, connection=db) if attempt_id else None
        if attempt_id and (not attempt or attempt.get('state') != 'dispatching'
                or attempt.get('grant_sha256') != output['grant_sha256']
                or attempt.get('task_id') != task['id'] or attempt.get('asset_id') != asset_id
                or attempt.get('check') != check_id or attempt.get('server_id') != server_id
                or attempt.get('contract_sha256') != hashlib.sha256(_encode(current.get('remote_execution'))).hexdigest()):
            raise AdmissionError('remote_attempt_changed')
        scopes = [asset for asset in current['scope_snapshot'] if asset['id'] == asset_id]
        if len(scopes) != 1:
            raise AdmissionError('task_authority_changed')
        asset = scopes[0]
        live_asset = store.get('assets', asset_id, connection=db)
        if (not live_asset or live_asset.get('archived_at')
                or live_asset.get('id') != asset_id
                or live_asset.get('authorized') is not True or live_asset.get('url') != asset.get('url')
                or type(live_asset.get('revision', 1)) is not int
                or live_asset.get('revision', 1) != asset.get('revision', 1)
                or asset.get('revision', 1) != claim.asset.revision or asset.get('url') != claim.asset.url):
            raise AdmissionError('asset_authority_changed')
        selected_checks = list(dict.fromkeys(cell.check for cell in claim.observation.cells)) if claim.observation else [check_id]
        priors = {}
        for selected_check in selected_checks:
            coverage_id = f"{task['id']}:{asset_id}:{selected_check}"
            prior = store.get('coverage', coverage_id, connection=db)
            identity = {'id': coverage_id, 'task_id': task['id'], 'asset_id': asset_id,
                        'check': selected_check, 'asset_revision': claim.asset.revision}
            if prior is not None and (prior.get('status') not in ('not_started', 'running')
                    or _encode({name: prior.get(name) for name in identity}) != _encode(identity)):
                raise AdmissionError('coverage_already_recorded')
            priors[selected_check] = prior
        if claim.observation:
            from .mcp_observation import finding as observed_finding
            rows = output['result']
            try:
                findings = [observed_finding(item, row, claim.observation.source_task_id)
                            for row in rows if row['status'] == 'completed' for item in row['findings']]
            except ValueError:
                raise AdmissionError('observation_finding_contract') from None
            observed, skipped = [], None
        else:
            findings, observed, skipped = output['result']
        timestamp = now()
        if timestamp >= claim.expires_at:
            raise AdmissionError('remote_authority_expired')
        receipt = {'id': receipt_id, 'format': 'aegis-mcp-admission-v1', 'task_id': task['id'],
                   'asset_id': asset_id, 'asset_revision': claim.asset.revision, 'check': check_id,
                   'server_id': server_id, 'scope_url': claim.asset.url,
                   'package_sha256': claim.package_sha256, 'grant_sha256': output['grant_sha256'],
                   'result_sha256': result_sha, 'authority_sha256': authority_sha,
                   'created_at': timestamp, 'finding_ids': [], 'evidence_ids': [],
                   'observation_ids': [], 'traffic_ids': [], 'coverage_id': coverage_id,
                   'fingerprints': [], 'coverage_status': 'skipped' if skipped else 'completed',
                   'provenance_basis': 'validated_remote_result_and_local_approval_metadata'}
        if claim.observation:
            receipt['coverage_id'] = None
            receipt['coverage_ids'] = [f"{task['id']}:{asset_id}:{check}" for check in selected_checks]
            receipt['coverage_statuses'] = {check: 'completed' if all(row['status'] == 'completed'
                for row in rows if row['check'] == check) else 'failed' for check in selected_checks}
            receipt['coverage_status'] = 'completed' if all(status == 'completed'
                for status in receipt['coverage_statuses'].values()) else 'failed'
            receipt['observation_source_task_id'] = claim.observation.source_task_id
            receipt['observation_execution_fingerprint'] = claim.observation.execution_fingerprint
        for item in findings:
            finding, evidence, _ = record_observation(store, current, asset, item, connection=db)
            receipt['finding_ids'].append(finding['id'])
            receipt['evidence_ids'].append(evidence['id'])
            receipt['fingerprints'].append(finding['fingerprint'])
        for url in observed:
            record = record_link(store, current, asset, check_id, url, connection=db)
            receipt['observation_ids'].append(record['id'])
        records = []
        for row in output['traffic']:
            record = {**row, 'id': identifier(), 'task_id': task['id'], 'asset_id': asset_id,
                      'created_at': timestamp, 'remote_admission_id': receipt_id, 'server_id': server_id}
            receipt['traffic_ids'].append(record['id'])
            records.append(('traffic', record))
        for selected_check in selected_checks:
            coverage = {**(priors[selected_check] or slot(current, asset, selected_check)),
                        'status': 'skipped' if skipped else 'completed',
                        'reason': skipped or '승인된 원격 GET 검증 결과를 확인했습니다.',
                        'updated_at': timestamp, 'finished_at': timestamp, 'remote_admission_id': receipt_id}
            if claim.observation:
                coverage['targets'] = [{name: row[name] for name in ('observation_id', 'url', 'status', 'error_type') if name in row}
                                       for row in rows if row['check'] == selected_check]
                coverage['status'] = receipt['coverage_statuses'][selected_check]
                coverage['reason'] = '선택한 모든 관찰 응답의 검증을 완료했습니다.' if coverage['status'] == 'completed' else '일부 관찰 응답의 검증을 완료하지 못했습니다.'
            records.append(('coverage', coverage))
        records.append(('mcp_execution_receipts', receipt))
        if attempt:
            receipt['attempt_id'] = attempt_id
            records.append(('mcp_execution_attempts', {**attempt, 'state': 'admitted',
                'receipt_id': receipt_id, 'finished_at': timestamp}))
        store.put_many(records, connection=db)
        store.event(task['id'], '승인된 원격 검증 결과를 원자적으로 기록했습니다.', detail={
            'asset_id': asset_id, 'worker_id': task['id'] + ':' + asset_id, 'check': check_id,
            'server_id': server_id, 'remote_admission_id': receipt_id,
            'grant_sha256': output['grant_sha256'], 'result_sha256': result_sha,
            'findings': len(findings), 'observations': len(observed), 'requests': len(output['traffic'])}, connection=db)
        if control:
            control.check()
        return receipt
