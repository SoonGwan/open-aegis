"""Coverage describes executed checks, never a claim that an asset is secure."""
import sqlite3
from .checks import CATALOG
from .store_util import now

STATUSES = ('not_started', 'running', 'completed', 'skipped', 'failed', 'cancelled', 'interrupted', 'not_recorded', 'stale')
TERMINAL = {'completed', 'skipped', 'failed', 'cancelled', 'interrupted', 'not_recorded'}


def slot(task, asset, check, status='not_started', **details):
    return {'id': f"{task['id']}:{asset['id']}:{check}", 'task_id': task['id'],
            'asset_id': asset['id'], 'asset_revision': asset.get('revision', 1), 'check': check,
            'status': status, 'created_at': task['created_at'], 'updated_at': now(), **details}


def planned_slots(task):
    from .goal_planner import execution_checks
    return [slot(task, asset, check, reason='승인 후 실행합니다.')
            for asset in task['scope_snapshot'] for check in execution_checks(task, asset['id'])]


def task_rows(store, task, *, get_record=None):
    return list(iter_task_rows(store, task, get_record=get_record))


def iter_task_rows(store, task, *, get_record=None):
    """Yield expected cells without materializing a whole task's coverage matrix."""
    from .goal_planner import execution_checks
    get_record = get_record or store.get
    for asset in task.get('scope_snapshot', []):
        for check in execution_checks(task, asset['id']):
            template = slot(task, asset, check)
            row = get_record('coverage', template['id'])
            if row is not None and any(row.get(key) != template[key] for key in ('id', 'task_id', 'asset_id', 'check')):
                row = {**template, 'status': 'not_recorded', 'reason': '실행 범위와 일치하지 않는 결과 기록입니다.'}
            if row is None:
                status = 'not_started' if task['status'] in ('pending', 'queued', 'running', 'stopping') else 'not_recorded'
                row = {**template, 'status': status, 'reason': '이전 기록에 도구별 결과가 없습니다.' if status == 'not_recorded' else '아직 실행 결과가 없습니다.'}
            if row.get('status') not in STATUSES:
                row = {**row, 'status': 'not_recorded', 'reason': '도구별 실행 결과의 상태를 확인할 수 없습니다.'}
            yield row


def finish_remaining(store, task, status, reason):
    for row in iter_task_rows(store, task):
        if row['status'] not in TERMINAL:
            store.put('coverage', {**row, 'status': status, 'reason': reason, 'updated_at': now()})


def latest_summary(db, asset_ids=None):
    """Rank attempts by approval time; proof from an old revision is stale.

    Build the expected matrix from the catalog and active assets, including cells
    missing from older databases. Pending/rejected plans do not replace evidence.
    """
    checks = [item['id'] for item in CATALOG]
    args = list(checks)
    asset_clause = ''
    if asset_ids is not None:
        if not asset_ids:
            return {'expected': 0, 'completed': 0, 'percent': 0, 'counts': dict.fromkeys(STATUSES, 0), 'assets': {}, 'covered_assets': 0, 'fully_covered_assets': 0}
        asset_clause = ' AND id IN (' + ','.join('?' for _ in asset_ids) + ')'
        args.extend(asset_ids)
    # CROSS JOIN fixes SQLite's loop order: enumerate task scope first, then
    # look up assets by (kind,id), rather than scan every task for each asset.
    # Project the needed task fields once before expanding its scope/checks.
    # The temporary relation omits full task payloads; result rows are looked
    # up only after the latest attempt is ranked. Older SQLite keeps the same
    # query semantics without the materialization hint.
    # Keep iterated fields encoded as JSON, including scalar strings; otherwise
    # extracting a string before json_each changes its original path semantics.
    query = """
      WITH catalog(check_id) AS (VALUES %s),
      task_fields AS %s(
        SELECT id,rowid,json_quote(json_extract(data,'$.scope_snapshot')) AS scope_snapshot,
          json_quote(json_extract(data,'$.checks')) AS checks,json_extract(data,'$.status') AS task_status,
          coalesce(json_extract(data,'$.approved_at'),json_extract(data,'$.created_at')) AS attempt_time,
          json_extract(data,'$.goal_selection') AS goal_selection,
          json_quote(json_extract(data,'$.goal_selection.cells')) AS selected_cells,
          json_extract(data,'$.goal_plan.execution') AS goal_execution,
          json_quote(json_extract(data,'$.goal_plan.decomposition.objectives')) AS objectives
        FROM records WHERE kind='tasks' AND json_extract(data,'$.observation_execution') IS NULL
          AND (json_extract(data,'$.approved_at') IS NOT NULL OR
            json_extract(data,'$.status') IN ('queued','running','stopping','completed','failed','stopped','interrupted'))
      ),
      assets AS (SELECT id,json_extract(data,'$.revision') AS revision FROM records
                 WHERE kind='assets' AND coalesce(json_extract(data,'$.archived_at'),0)=0 %s),
      attempts AS (
        SELECT a.id AS asset_id, checks.value AS check_id,t.id AS task_id,
               coalesce(json_extract(scope.value,'$.revision'),1) AS revision,
               t.task_status,
               ROW_NUMBER() OVER (PARTITION BY a.id,checks.value
                 ORDER BY t.attempt_time DESC,t.rowid DESC) AS rank
        FROM task_fields t CROSS JOIN json_each(t.scope_snapshot) scope
        CROSS JOIN json_each(t.checks) checks CROSS JOIN assets a
        WHERE a.id=json_extract(scope.value,'$.id')
          AND (t.goal_selection IS NULL OR EXISTS (
            SELECT 1 FROM json_each(t.selected_cells) selected
              WHERE json_extract(selected.value,'$.asset_id')=a.id
                AND json_extract(selected.value,'$.check')=checks.value))
          AND (t.goal_execution IS NULL OR
            EXISTS (SELECT 1 FROM json_each(t.objectives) objective
              CROSS JOIN json_each(objective.value,'$.asset_ids') goal_asset
              CROSS JOIN json_each(objective.value,'$.checks') goal_check
              WHERE goal_asset.value=a.id AND goal_check.value=checks.value))
      ), cells AS (
        SELECT a.id AS asset_id, CASE
          WHEN attempts.asset_id IS NULL THEN 'not_started'
          WHEN attempts.revision!=coalesce(a.revision,1) THEN 'stale'
          ELSE coalesce(json_extract(c.data,'$.status'),
            CASE WHEN attempts.task_status IN ('queued','running','stopping')
              THEN 'not_started' ELSE 'not_recorded' END) END AS status
        FROM assets a CROSS JOIN catalog
        LEFT JOIN attempts ON attempts.asset_id=a.id AND attempts.check_id=catalog.check_id AND attempts.rank=1
        LEFT JOIN records c ON c.kind='coverage' AND c.id=attempts.task_id||':'||a.id||':'||catalog.check_id
          AND json_extract(c.data,'$.task_id')=attempts.task_id AND json_extract(c.data,'$.asset_id')=a.id
          AND json_extract(c.data,'$.check')=catalog.check_id
      ) SELECT asset_id,status,count(*) AS count FROM cells GROUP BY asset_id,status ORDER BY asset_id
    """ % (','.join('(?)' for _ in checks),
           'MATERIALIZED ' if sqlite3.sqlite_version_info >= (3,35,0) else '',asset_clause)
    counts = dict.fromkeys(STATUSES, 0)
    assets = {}
    previous_asset, asset_completed = None, 0
    covered_assets, fully_covered_assets = 0, 0
    for row in db.execute(query, args):
        status = row['status'] if row['status'] in counts else 'not_recorded'
        counts[status] += row['count']
        if row['asset_id'] != previous_asset:
            covered_assets += int(asset_completed > 0)
            fully_covered_assets += int(asset_completed == len(checks))
            previous_asset, asset_completed = row['asset_id'], 0
        if status == 'completed':
            asset_completed += row['count']
        if asset_ids is not None:
            item = assets.setdefault(row['asset_id'], {'expected': len(checks), 'completed': 0, 'counts': dict.fromkeys(STATUSES, 0)})
            item['counts'][status] += row['count']
            if status == 'completed':
                item['completed'] += row['count']
    covered_assets += int(asset_completed > 0)
    fully_covered_assets += int(asset_completed == len(checks))
    expected = sum(counts.values())
    return {'expected': expected, 'completed': counts['completed'],
            'percent': round(counts['completed'] * 100 / expected) if expected else 0,
            'counts': counts, 'assets': assets, 'covered_assets': covered_assets, 'fully_covered_assets': fully_covered_assets}
