"""Bounded graph persistence queries, with explicit native dialects."""
import json
from .postgres_store import array,text

FIELDS=('title','check','severity','status','confidence')


class SQLiteGraph:
    def __init__(self,db):self.db=db

    def latest_task(self,asset):
        row=self.db.execute("SELECT data FROM records WHERE kind='tasks' AND EXISTS (SELECT 1 FROM json_each(records.data,'$.asset_ids') WHERE value=?) ORDER BY rowid DESC LIMIT 1",(asset,)).fetchone()
        return json.loads(row['data']) if row else None

    def watermark(self):
        return self.db.execute("SELECT coalesce(max(rowid),0) FROM records WHERE kind='findings'").fetchone()[0]

    def findings(self,asset,task,checks,snapshot,severity,status,limit,offset):
        clauses=["kind='findings'",'rowid<=?',"json_extract(data,'$.asset_id')=?",
                 "EXISTS (SELECT 1 FROM json_each(records.data,'$.task_ids') WHERE value=?)",
                 "json_extract(data,'$.check') IN ("+','.join('?' for _ in checks)+')']
        args=[snapshot,asset,task,*checks]
        for key,value in (('severity',severity),('status',status)):
            if value:clauses.append(f"json_extract(data,'$.{key}')=?");args.append(value)
        where=' AND '.join(clauses)
        total=self.db.execute('SELECT count(*) FROM records WHERE '+where,args).fetchone()[0]
        projection=','.join(f"json_extract(data,'$.{key}') AS \"{key}\"" for key in FIELDS)
        rows=[dict(row) for row in self.db.execute('SELECT id,'+projection+' FROM records WHERE '+where+' ORDER BY rowid DESC LIMIT ? OFFSET ?',(*args,limit,offset))]
        return total,rows

    def proofs(self,finding,asset,task,check):
        matches="""FROM records f CROSS JOIN json_each(f.data,'$.evidence_ids') ref
          JOIN records e ON e.kind='evidence' AND e.id=ref.value
          WHERE f.kind='findings' AND f.id=? AND json_extract(e.data,'$.asset_id')=?
            AND json_extract(e.data,'$.task_id')=? AND json_extract(e.data,'$.check')=?
            AND json_extract(e.data,'$.fingerprint')=json_extract(f.data,'$.fingerprint')"""
        args=(finding,asset,task,check)
        count=self.db.execute('SELECT count(DISTINCT e.id) '+matches,args).fetchone()[0]
        rows=self.db.execute('SELECT e.id,e.data '+matches+' GROUP BY e.id ORDER BY e.rowid DESC LIMIT 2',args).fetchall()
        references=self.db.execute("SELECT count(DISTINCT value) FROM records f,json_each(f.data,'$.evidence_ids') WHERE f.kind='findings' AND f.id=?",(finding,)).fetchone()[0]
        invalid=self.db.execute("SELECT count(DISTINCT ref.value) FROM records f CROSS JOIN json_each(f.data,'$.evidence_ids') ref LEFT JOIN records e ON e.kind='evidence' AND e.id=ref.value WHERE f.kind='findings' AND f.id=? AND (e.id IS NULL OR json_extract(e.data,'$.asset_id') IS NOT ? OR json_extract(e.data,'$.check') IS NOT ? OR json_extract(e.data,'$.task_id') IS NULL OR json_extract(e.data,'$.fingerprint') IS NULL OR json_extract(f.data,'$.fingerprint') IS NULL OR json_extract(e.data,'$.fingerprint') IS NOT json_extract(f.data,'$.fingerprint'))",(finding,asset,check)).fetchone()[0]
        return count,rows,references,invalid

    def endpoints(self,asset,task):
        where="kind='observations' AND json_extract(data,'$.asset_id')=? AND json_extract(data,'$.task_id')=?"
        args=(asset,task)
        count=self.db.execute('SELECT count(*) FROM records WHERE '+where,args).fetchone()[0]
        rows=self.db.execute("SELECT id,json_extract(data,'$.url') AS url,json_extract(data,'$.created_at') AS created_at FROM records WHERE "+where+' ORDER BY rowid DESC LIMIT 10',args).fetchall()
        return count,rows


class PostgresGraph:
    def __init__(self,db):self.db=db

    def latest_task(self,asset):
        row=self.db.execute("SELECT data FROM records WHERE kind='tasks' AND "+array('asset_ids')+' ? %s ORDER BY rowid DESC LIMIT 1',(asset,)).fetchone()
        return json.loads(row['data']) if row else None

    def watermark(self):
        return self.db.execute("SELECT coalesce(max(rowid),0) AS upper FROM records WHERE kind='findings'").fetchone()['upper']

    def findings(self,asset,task,checks,snapshot,severity,status,limit,offset):
        clauses=["kind='findings'",'rowid<=%s',text('asset_id')+'=%s',array('task_ids')+' ? %s',text('check')+'=ANY(%s)']
        args=[snapshot,asset,task,list(checks)]
        for key,value in (('severity',severity),('status',status)):
            if value:clauses.append(text(key)+'=%s');args.append(value)
        where=' AND '.join(clauses)
        total=self.db.execute('SELECT count(*) AS count FROM records WHERE '+where,args).fetchone()['count']
        # jsonb scalar projections decode into the same Python scalar types.
        projection=','.join(f"data::jsonb->'{key}' AS \"{key}\"" for key in FIELDS)
        rows=self.db.execute('SELECT id,'+projection+' FROM records WHERE '+where+' ORDER BY rowid DESC LIMIT %s OFFSET %s',(*args,limit,offset)).fetchall()
        return total,rows

    def proofs(self,finding,asset,task,check):
        refs='FROM records f CROSS JOIN LATERAL jsonb_array_elements_text('+array('evidence_ids','f')+') ref(value) '
        matches=refs+"JOIN records e ON e.kind='evidence' AND e.id=ref.value WHERE f.kind='findings' AND f.id=%s AND "+text('asset_id','e')+'=%s AND '+text('task_id','e')+'=%s AND '+text('check','e')+'=%s AND '+text('fingerprint','e')+'='+text('fingerprint','f')
        args=(finding,asset,task,check)
        count=self.db.execute('SELECT count(DISTINCT e.id) AS count '+matches,args).fetchone()['count']
        rows=self.db.execute('SELECT e.id,e.data '+matches+' GROUP BY e.id,e.data,e.rowid ORDER BY e.rowid DESC LIMIT 2',args).fetchall()
        references=self.db.execute("SELECT count(DISTINCT ref.value) AS count "+refs+"WHERE f.kind='findings' AND f.id=%s",(finding,)).fetchone()['count']
        invalid=self.db.execute('SELECT count(DISTINCT ref.value) AS count '+refs+"LEFT JOIN records e ON e.kind='evidence' AND e.id=ref.value WHERE f.kind='findings' AND f.id=%s AND (e.id IS NULL OR "+text('asset_id','e')+' IS DISTINCT FROM %s OR '+text('check','e')+' IS DISTINCT FROM %s OR '+text('task_id','e')+' IS NULL OR '+text('fingerprint','e')+' IS NULL OR '+text('fingerprint','f')+' IS NULL OR '+text('fingerprint','e')+' IS DISTINCT FROM '+text('fingerprint','f')+')',(finding,asset,check)).fetchone()['count']
        return count,rows,references,invalid

    def endpoints(self,asset,task):
        where="kind='observations' AND "+text('asset_id')+'=%s AND '+text('task_id')+'=%s'
        args=(asset,task)
        count=self.db.execute('SELECT count(*) AS count FROM records WHERE '+where,args).fetchone()['count']
        rows=self.db.execute("SELECT id,data::jsonb->'url' AS url,data::jsonb->'created_at' AS created_at FROM records WHERE "+where+' ORDER BY rowid DESC LIMIT 10',args).fetchall()
        return count,rows
