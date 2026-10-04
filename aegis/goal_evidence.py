"""Bounded objective findings linked by actual source proof, with validated retests."""
import json
from contextlib import nullcontext
from .goal_planner import require_task


def page(store, task_id, objective_id, *, limit=25, offset=0, snapshot=None, search='', finding_id=None, connection=None):
    with (nullcontext(connection) if connection is not None else store.read_transaction()) as db:
        task=store.get('tasks',task_id,connection=db)
        if not task:raise LookupError('작업이 없습니다.')
        require_task(task)
        objective=next((row for row in task.get('goal_plan',{}).get('decomposition',{}).get('objectives',[])
                        if row['id']==objective_id),None)
        if not objective:raise LookupError('목표 과제가 없습니다.')
        native=getattr(store,'backend',None)=='postgres'
        bind='%s' if native else '?'
        def field(alias,key):
            return f"{alias}.data::jsonb->>'{key}'" if native else f"json_extract({alias}.data,'$.{key}')"
        def members(alias,key):
            if native:
                return f"jsonb_array_elements_text(CASE WHEN jsonb_typeof({alias}.data::jsonb->'{key}')='array' THEN {alias}.data::jsonb->'{key}' ELSE '[]'::jsonb END)"
            return f"json_each(CASE WHEN json_type({alias}.data,'$.{key}')='array' THEN json_extract({alias}.data,'$.{key}') ELSE '[]' END)"
        def contains(alias,key,expression):
            return f"EXISTS (SELECT 1 FROM {members(alias,key)} member(value) WHERE member.value={expression})" if native else f"EXISTS (SELECT 1 FROM {members(alias,key)} member WHERE member.value={expression})"
        if snapshot is None:
            snapshot=db.execute("SELECT coalesce(max(rowid),0) AS watermark FROM records WHERE kind='findings'").fetchone()['watermark']
        proof=("FROM records e WHERE e.kind='evidence' AND "+field('e','task_id')+'='+bind+
               ' AND '+field('e','asset_id')+'='+field('f','asset_id')+' AND '+field('e','check')+'='+field('f','check')+
               ' AND '+field('e','fingerprint')+'='+field('f','fingerprint')+' AND '+contains('f','evidence_ids','e.id'))
        where="f.kind='findings' AND f.rowid<="+bind+' AND '+field('f','asset_id')+' IN ('+','.join(bind for _ in objective['asset_ids'])+') AND '+field('f','check')+' IN ('+','.join(bind for _ in objective['checks'])+') AND '+contains('f','task_ids',bind)+' AND EXISTS (SELECT 1 '+proof+')'
        args=[snapshot,*objective['asset_ids'],*objective['checks'],task_id,task_id]
        if finding_id is not None:
            where+=' AND f.id='+bind;args.append(finding_id)
        if search:
            expression=field('f','title')
            where+=' AND '+(f'position(lower({bind}) in lower({expression}))>0' if native else f'instr(lower({expression}),lower({bind}))>0')
            args.append(search)
        total=db.execute('SELECT count(*) AS total FROM records f WHERE '+where,args).fetchone()['total']
        # Retest conclusions only count when their task points back to this finding
        # and declares the same asset/check. A conclusion is not goal achievement.
        def length(alias,key):
            return f"jsonb_array_length(CASE WHEN jsonb_typeof({alias}.data::jsonb->'{key}')='array' THEN {alias}.data::jsonb->'{key}' ELSE '[]'::jsonb END)" if native else f"json_array_length({alias}.data,'$.{key}')"
        scope_member = ("jsonb_array_elements(CASE WHEN jsonb_typeof(rt.data::jsonb->'scope_snapshot')='array' THEN rt.data::jsonb->'scope_snapshot' ELSE '[]'::jsonb END) scope(value)" if native
                        else "json_each(CASE WHEN json_type(rt.data,'$.scope_snapshot')='array' THEN json_extract(rt.data,'$.scope_snapshot') ELSE '[]' END) scope")
        scope_id = "scope.value->>'id'" if native else "CASE WHEN scope.type='object' THEN json_extract(scope.value,'$.id') END"
        retests=("FROM records r JOIN records rt ON rt.kind='tasks' AND rt.id="+field('r','task_id')+
                 " WHERE r.kind='retests' AND "+field('r','finding_id')+'=f.id AND '+field('rt','retest_of')+'=f.id AND '+
                 field('rt','approved_at')+" IS NOT NULL AND "+field('r','conclusion')+" IN ('resolved','reproduced','inconclusive') AND "+
                 contains('rt','asset_ids',field('f','asset_id'))+' AND '+contains('rt','checks',field('f','check'))+
                 ' AND '+length('rt','asset_ids')+'=1 AND '+length('rt','checks')+'=1 AND '+length('rt','scope_snapshot')+'=1 AND EXISTS (SELECT 1 FROM '+scope_member+' WHERE '+scope_id+'='+field('f','asset_id')+')')
        fields=['f.id']+[field('f',key)+' AS "'+key+'"' for key in ('title','asset_id','asset_name','check','severity','status')]
        fields += ['(SELECT count(*) '+proof+') AS evidence_count',
                   '(SELECT count(*) '+retests+') AS retests_count',
                   '(SELECT r.data '+retests+' ORDER BY r.rowid DESC LIMIT 1) AS latest_retest']
        rows=db.execute('SELECT '+','.join(fields)+' FROM records f WHERE '+where+' ORDER BY f.rowid DESC LIMIT '+bind+' OFFSET '+bind,
                        [task_id,*args,limit,offset]).fetchall()
        items=[]
        for row in rows:
            item=dict(row);raw=item.pop('latest_retest')
            record=json.loads(raw) if raw else None
            item['latest_retest']={key:record.get(key) for key in ('id','task_id','conclusion','triage_effect','created_at')} if record else None
            items.append(item)
        return {'items':items,'total':total,'limit':limit,'offset':offset,'snapshot':snapshot,
                'has_more':offset+len(items)<total,'task_id':task_id,'objective_id':objective_id,'goal_verified':False,
                'basis':'source_task_proof_and_same_finding_retests'}
