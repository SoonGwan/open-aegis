"""Native PostgreSQL query for the same revision-aware coverage contract."""
from .checks import CATALOG
from .coverage import STATUSES
from .postgres_store import array, text


def latest_summary(db, asset_ids=None):
    checks=[item['id'] for item in CATALOG]
    counts=dict.fromkeys(STATUSES,0);assets={}
    if asset_ids is not None and not asset_ids:
        return {'expected':0,'completed':0,'percent':0,'counts':counts,'assets':{},'covered_assets':0,'fully_covered_assets':0}
    args=list(checks)
    asset_clause=''
    if asset_ids is not None:asset_clause=' AND id=ANY(%s)';args.append(list(asset_ids))
    query="""
      WITH catalog(check_id) AS (VALUES %s),
      assets AS (SELECT id,coalesce((%s)::numeric,1) AS revision FROM records
        WHERE kind='assets' AND coalesce((%s)::numeric,0)=0 %s),
      attempts AS (
        SELECT a.id AS asset_id, checks.value AS check_id,
          coalesce((scope.value->>'revision')::numeric,1) AS revision,
          coalesce(%s,CASE WHEN %s IN ('queued','running','stopping') THEN 'not_started' ELSE 'not_recorded' END) AS status,
          ROW_NUMBER() OVER (PARTITION BY a.id,checks.value
            ORDER BY coalesce((%s)::numeric,(%s)::numeric) DESC NULLS LAST,t.rowid DESC) AS rank
        FROM records t CROSS JOIN LATERAL jsonb_array_elements(%s) scope(value)
        CROSS JOIN LATERAL jsonb_array_elements_text(%s) checks(value)
        JOIN assets a ON a.id=scope.value->>'id'
        LEFT JOIN records c ON c.kind='coverage' AND c.id=t.id||':'||a.id||':'||checks.value
          AND %s=t.id AND %s=a.id AND %s=checks.value
        WHERE t.kind='tasks' AND t.data::jsonb->>'observation_execution' IS NULL
          AND (%s IS NOT NULL OR %s IN ('queued','running','stopping','completed','failed','stopped','interrupted'))
      ), cells AS (
        SELECT a.id AS asset_id,CASE WHEN attempts.asset_id IS NULL THEN 'not_started'
          WHEN attempts.revision!=a.revision THEN 'stale' ELSE attempts.status END AS status
        FROM assets a CROSS JOIN catalog LEFT JOIN attempts ON attempts.asset_id=a.id
          AND attempts.check_id=catalog.check_id AND attempts.rank=1
      ) SELECT asset_id,status,count(*) AS count FROM cells GROUP BY asset_id,status ORDER BY asset_id COLLATE "C"
    """ % (','.join('(%s)' for _ in checks),text('revision'),text('archived_at'),asset_clause,
           text('status','c'),text('status','t'),text('approved_at','t'),text('created_at','t'),
           array('scope_snapshot','t'),array('checks','t'),text('task_id','c'),text('asset_id','c'),
           text('check','c'),text('approved_at','t'),text('status','t'))
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
