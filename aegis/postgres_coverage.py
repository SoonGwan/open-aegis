"""Native PostgreSQL query for the same revision-aware coverage contract."""
from .checks import CATALOG
from .coverage import STATUSES
from .postgres_store import text


def latest_summary(db, asset_ids=None):
    checks=[item['id'] for item in CATALOG]
    counts=dict.fromkeys(STATUSES,0);assets={}
    if asset_ids is not None and not asset_ids:
        return {'expected':0,'completed':0,'percent':0,'counts':counts,'assets':{},'covered_assets':0,'fully_covered_assets':0}
    args=list(checks)
    asset_clause=''
    if asset_ids is not None:asset_clause=' AND id=ANY(%s)';args.append(list(asset_ids))
    # Decode each task document once into the fields used by coverage, rather
    # than casting its whole payload repeatedly for each asset/check attempt.
    # Delay timestamp casts and coverage lookup until eligible cells are known.
    query="""
      WITH catalog(check_id) AS (VALUES %s),
      task_fields AS MATERIALIZED (
        SELECT t.id,t.rowid,f.scope_snapshot,f.checks,f.status AS task_status,
          f.approved_at,f.created_at,
          f.goal_selection,f.goal_plan->>'execution' AS goal_execution,
          f.goal_plan->'decomposition'->'objectives' AS objectives
        FROM records t CROSS JOIN LATERAL jsonb_to_record(t.data::jsonb) AS f(
          scope_snapshot jsonb,checks jsonb,status text,approved_at text,created_at text,
          goal_selection jsonb,goal_plan jsonb,observation_execution jsonb)
        WHERE t.kind='tasks' AND f.observation_execution IS NULL
          AND (f.approved_at IS NOT NULL OR f.status IN
            ('queued','running','stopping','completed','failed','stopped','interrupted'))
      ),
      assets AS (SELECT id,coalesce((%s)::numeric,1) AS revision FROM records
        WHERE kind='assets' AND coalesce((%s)::numeric,0)=0 %s),
      attempts AS (
        SELECT a.id AS asset_id, checks.value AS check_id,t.id AS task_id,
          coalesce((scope.value->>'revision')::numeric,1) AS revision,
          t.task_status,
          ROW_NUMBER() OVER (PARTITION BY a.id,checks.value
            ORDER BY coalesce(t.approved_at::numeric,t.created_at::numeric) DESC NULLS LAST,t.rowid DESC) AS rank
        FROM task_fields t CROSS JOIN LATERAL jsonb_array_elements(
          CASE WHEN jsonb_typeof(t.scope_snapshot)='array' THEN t.scope_snapshot ELSE '[]'::jsonb END) scope(value)
        CROSS JOIN LATERAL jsonb_array_elements_text(
          CASE WHEN jsonb_typeof(t.checks)='array' THEN t.checks ELSE '[]'::jsonb END) checks(value)
        JOIN assets a ON a.id=scope.value->>'id'
        WHERE (t.goal_selection IS NULL OR EXISTS (
            SELECT 1 FROM jsonb_array_elements(t.goal_selection->'cells') selected
              WHERE selected->>'asset_id'=a.id AND selected->>'check'=checks.value))
          AND (t.goal_execution IS NULL OR EXISTS (
            SELECT 1 FROM jsonb_array_elements(t.objectives) objective
              CROSS JOIN jsonb_array_elements_text(objective->'asset_ids') goal_asset
              CROSS JOIN jsonb_array_elements_text(objective->'checks') goal_check
              WHERE goal_asset=a.id AND goal_check=checks.value))
      ), cells AS (
        SELECT a.id AS asset_id,CASE WHEN attempts.asset_id IS NULL THEN 'not_started'
          WHEN attempts.revision!=a.revision THEN 'stale' ELSE coalesce(%s,
            CASE WHEN attempts.task_status IN ('queued','running','stopping')
              THEN 'not_started' ELSE 'not_recorded' END) END AS status
        FROM assets a CROSS JOIN catalog LEFT JOIN attempts ON attempts.asset_id=a.id
          AND attempts.check_id=catalog.check_id AND attempts.rank=1
        LEFT JOIN records c ON c.kind='coverage' AND c.id=attempts.task_id||':'||a.id||':'||catalog.check_id
          AND %s=attempts.task_id AND %s=a.id AND %s=catalog.check_id
      ) SELECT asset_id,status,count(*) AS count FROM cells GROUP BY asset_id,status ORDER BY asset_id COLLATE "C"
    """ % (','.join('(%s)' for _ in checks),text('revision'),text('archived_at'),asset_clause,
           text('status','c'),text('task_id','c'),text('asset_id','c'),text('check','c'))
    previous=None;completed=0;covered=0;fully=0
    for row in db.execute(query,args):
        status=row['status'] if row['status'] in counts else 'not_recorded'
        counts[status]+=row['count']
        if row['asset_id']!=previous:
            covered+=int(completed>0);fully+=int(completed==len(checks));previous=row['asset_id'];completed=0
        if status=='completed':completed+=row['count']
        if asset_ids is not None:
            item=assets.setdefault(row['asset_id'],{'expected':len(checks),'completed':0,'counts':dict.fromkeys(STATUSES,0)})
            item['counts'][status]+=row['count']
            if status=='completed':item['completed']+=row['count']
    covered+=int(completed>0);fully+=int(completed==len(checks));expected=sum(counts.values())
    return {'expected':expected,'completed':counts['completed'],'percent':round(counts['completed']*100/expected) if expected else 0,
            'counts':counts,'assets':assets,'covered_assets':covered,'fully_covered_assets':fully}
