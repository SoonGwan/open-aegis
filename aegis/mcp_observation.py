"""Fixed observed-response batch: approved URLs, reused responses, explicit cells."""
from .checks import run_check
from .observation_execution import digest
from .tool_contracts import validate_result


def execute(claim, transport, control):
    """Fetch each selected URL once; do not fetch the base or discover more URLs."""
    responses = {}
    for target in claim.observation.targets:
        control.check()
        try:
            response = transport.get(target.url)
            if not 200 <= response['status'] < 300:
                raise ValueError('target_unconfirmed')
            responses[target.id] = response
        except Exception:
            control.check()  # Cancellation/deadline is not a confirmed partial batch.
            responses[target.id] = None
    targets = {target.id: target for target in claim.observation.targets}
    rows = []
    for cell in claim.observation.cells:
        control.check()
        row = {'observation_id': cell.observation_id, 'url': targets[cell.observation_id].url,
               'check': cell.check}
        response = responses[cell.observation_id]
        try:
            if response is None:
                raise ValueError('target_unconfirmed')
            findings, observed, skipped = validate_result(cell.check, claim.asset.model_dump(),
                run_check(cell.check, claim.asset.model_dump(), transport, response))
            if observed or skipped:
                raise ValueError('observation_result_contract')
            row.update(status='completed', findings=findings)
        except Exception:
            control.check()
            row.update(status='failed', error_type='TargetUnconfirmed')
        rows.append(row)
    return rows


def validate(claim, rows):
    if not isinstance(rows, list) or len(rows) != len(claim.observation.cells):
        raise ValueError('observation_result_matrix')
    targets = {target.id: target for target in claim.observation.targets}
    for cell, row in zip(claim.observation.cells, rows):
        identity = {'observation_id': cell.observation_id, 'url': targets[cell.observation_id].url,
                    'check': cell.check}
        if not isinstance(row, dict) or any(row.get(key) != value for key, value in identity.items()):
            raise ValueError('observation_result_identity')
        if row.get('status') == 'completed':
            if set(row) != set(identity) | {'status', 'findings'}:
                raise ValueError('observation_result_shape')
            validate_result(cell.check, claim.asset.model_dump(), (row['findings'], [], None))
        elif row.get('status') == 'failed':
            if set(row) != set(identity) | {'status', 'error_type'} or row['error_type'] != 'TargetUnconfirmed':
                raise ValueError('observation_result_shape')
        else:
            raise ValueError('observation_result_status')
    return rows


def finding(item, row, source_task_id):
    """Use the same URL-specific finding identity as local observed-response jobs."""
    value = {**item, 'code': 'observed-' + digest(row['url'])[:24] + '-' + item['code'],
             'evidence': {**item['evidence'], 'observation_id': row['observation_id'], 'requested_url': row['url']}}
    validate_result(row['check'], {'url': row['url']}, ([value], [], None))
    return {**value, 'observation_id': row['observation_id'], 'observation_source_task_id': source_task_id}
