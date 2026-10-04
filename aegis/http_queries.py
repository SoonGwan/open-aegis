"""Named HTTP persistence operations with explicit native SQL."""
import json
from .postgres_store import text


def related_field(field):
    if field not in ('retry_of','retest_of'):raise ValueError('Unknown task relation')
    return field


class SQLiteHTTP:
    def __init__(self,store):self.store=store

    def active_related_task(self,field,id,exclude=''):
        field=related_field(field)
        with self.store.read_transaction() as db:
            row=db.execute("SELECT data FROM records WHERE kind='tasks' AND json_extract(data,'$."+field+"')=? AND id!=? AND json_extract(data,'$.status') IN ('pending','queued','running','stopping') LIMIT 1",(id,exclude)).fetchone()
            return json.loads(row['data']) if row else None

    def overview_summary(self):
        from .coverage import latest_summary
        with self.store.read_transaction() as db:
            summary=latest_summary(db)
            counts={f"findings_{row['severity']}":row['count'] for row in db.execute("SELECT json_extract(data,'$.severity') AS severity,count(*) AS count FROM records WHERE kind='findings' AND json_extract(data,'$.status')='open' GROUP BY json_extract(data,'$.severity')")}
            return summary,counts

    def assignees(self,search,limit,offset):
        with self.store.read_transaction() as db:
            where="disabled=0 AND role IN ('admin','operator') AND instr(lower(name||' '||username),lower(?))>0"
            total=db.execute('SELECT count(*) AS count FROM users WHERE '+where,(search,)).fetchone()['count']
            items=[dict(row) for row in db.execute('SELECT id,name,username,role FROM users WHERE '+where+' ORDER BY name,id LIMIT ? OFFSET ?',(search,limit,offset))]
        return dict(items=items,total=total,limit=limit,offset=offset,has_more=offset+len(items)<total)

    def delete_note(self,id):
        with self.store.write_transaction() as db:db.execute("DELETE FROM records WHERE kind='notes' AND id=?",(id,))


class PostgresHTTP:
    def __init__(self,store):self.store=store

    def active_related_task(self,field,id,exclude=''):
        field=related_field(field)
        with self.store.transaction() as db:
            row=db.execute("SELECT data FROM records WHERE kind='tasks' AND "+text(field)+'=%s AND id!=%s AND '+text('status')+" IN ('pending','queued','running','stopping') LIMIT 1",(id,exclude)).fetchone()
            return json.loads(row['data']) if row else None

    def overview_summary(self):
        from .postgres_coverage import latest_summary
        with self.store.transaction() as db:
            summary=latest_summary(db)
            counts={f"findings_{row['severity']}":row['count'] for row in db.execute('SELECT '+text('severity')+" AS severity,count(*) AS count FROM records WHERE kind='findings' AND "+text('status')+"='open' GROUP BY "+text('severity'))}
            return summary,counts

    def assignees(self,search,limit,offset):
        with self.store.transaction() as db:
            where="disabled=0 AND role IN ('admin','operator') AND strpos(lower((name||' '||username) COLLATE \"C\"),lower(%s COLLATE \"C\"))>0"
            total=db.execute('SELECT count(*) AS count FROM users WHERE '+where,(search,)).fetchone()['count']
            items=db.execute('SELECT id,name,username,role FROM users WHERE '+where+' ORDER BY name COLLATE "C",id COLLATE "C" LIMIT %s OFFSET %s',(search,limit,offset)).fetchall()
        return dict(items=items,total=total,limit=limit,offset=offset,has_more=offset+len(items)<total)

    def delete_note(self,id):
        with self.store.transaction(write=True) as db:db.execute("DELETE FROM records WHERE kind='notes' AND id=%s",(id,))
