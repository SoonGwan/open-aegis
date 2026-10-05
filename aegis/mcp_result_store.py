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


AUTHORITY_FIELDS = ('id', 'approved_at', 'asset_ids', 'scope_snapshot', 'checks', 'tool_contracts',
                    'execution_policy', 'worker_dependencies', 'worker_dependency_contract',
                    'goal_plan', 'goal_selection', 'goal_selection_contract',
                    'observation_execution', 'observation_execution_contract')


def admit(store, task, asset_id, check_id, token, key, server_id, response, *,
          ceiling=None, allow_private=False, protected_values=()):
    """Validate completely, then commit receipt/evidence/coverage/audit together.

Replaying an identical still-valid response returns its original receipt. A
receipt is proof of local admission, not remote runtime or target attestation.
    """
    try:
        task = _decode(_encode(task))
        output = validate_execution_response(token, key, server_id, response,
                                             ceiling=ceiling, allow_private=allow_private)
        claim = verify_claim(token, key, server_id)
        if (claim.task_id != task['id'] or claim.asset.id != asset_id or claim.check_id != check_id
                or task.get('observation_execution') or task.get('observation_cells')):
            raise ValueError()
        expected = issue_grant(task, asset_id, check_id, server_id, key,
                               ttl=claim.expires_at - claim.issued_at, timestamp=claim.issued_at,
                               allow_private=claim.allow_private)
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
                or check_id not in execution_checks(current, asset_id)):
            raise AdmissionError('task_authority_changed')
        require_contracts(current)
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
        coverage_id = f"{task['id']}:{asset_id}:{check_id}"
        prior = store.get('coverage', coverage_id, connection=db)
        coverage_identity = {'id': coverage_id, 'task_id': task['id'], 'asset_id': asset_id,
                             'check': check_id, 'asset_revision': claim.asset.revision}
        if prior is not None and (prior.get('status') not in ('not_started', 'running')
                                 or _encode({name: prior.get(name) for name in coverage_identity})
                                 != _encode(coverage_identity)):
            raise AdmissionError('coverage_already_recorded')
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
                   'provenance_basis': 'validated_remote_result_and_local_approval_metadata'}
        for item in findings:
            finding, evidence, _ = record_observation(store, current, asset, item, connection=db)
            receipt['finding_ids'].append(finding['id'])
            receipt['evidence_ids'].append(evidence['id'])
        for url in observed:
            record = record_link(store, current, asset, check_id, url, connection=db)
            receipt['observation_ids'].append(record['id'])
        records = []
        for row in output['traffic']:
            record = {**row, 'id': identifier(), 'task_id': task['id'], 'asset_id': asset_id,
                      'created_at': timestamp, 'remote_admission_id': receipt_id, 'server_id': server_id}
            receipt['traffic_ids'].append(record['id'])
            records.append(('traffic', record))
        coverage = {**(prior or slot(current, asset, check_id)),
                    'status': 'skipped' if skipped else 'completed',
                    'reason': skipped or '승인된 원격 GET 검증 결과를 확인했습니다.',
                    'updated_at': timestamp, 'finished_at': timestamp, 'remote_admission_id': receipt_id}
        records.extend([('coverage', coverage), ('mcp_execution_receipts', receipt)])
        store.put_many(records, connection=db)
        store.event(task['id'], '승인된 원격 검증 결과를 원자적으로 기록했습니다.', detail={
            'asset_id': asset_id, 'worker_id': task['id'] + ':' + asset_id, 'check': check_id,
            'server_id': server_id, 'remote_admission_id': receipt_id,
            'grant_sha256': output['grant_sha256'], 'result_sha256': result_sha,
            'findings': len(findings), 'observations': len(observed), 'requests': len(output['traffic'])}, connection=db)
        return receipt
