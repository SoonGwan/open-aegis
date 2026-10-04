"""Complete report records via server-side cursors in a native read snapshot."""
import json
from .postgres_store import array, text
from .reporting import Snapshot


class PostgresSnapshot(Snapshot):
    def __init__(self, db, task_id, permit=None):
        super().__init__(db,task_id)
        self.permit=permit

    def check(self):
        if self.permit:self.permit.check()

    def records(self, kind):
        self.check()
        where,args='r.kind=%s',[kind]
        if kind=='tasks' and self.task_id:
            where+=' AND r.id=%s';args.append(self.task_id)
        elif kind=='findings' and self.task_id:
            where+=' AND '+array('task_ids','r')+' ? %s';args.append(self.task_id)
        elif kind in ('evidence','traffic'):
            where+=" AND EXISTS (SELECT 1 FROM records t WHERE t.kind='tasks' AND t.id="+text('task_id','r')
            if self.task_id:where+=' AND t.id=%s';args.append(self.task_id)
            where+=')'
        elif kind=='finding_history':
            where+=" AND EXISTS (SELECT 1 FROM records f WHERE f.kind='findings' AND f.id="+text('finding_id','r')
            if self.task_id:
                where+=' AND '+array('task_ids','f')+' ? %s';args.append(self.task_id)
            where+=')'
        with self.db.cursor(name='aegis_report_'+kind) as cursor:
            cursor.itersize=32
            cursor.execute('SELECT r.data FROM records r WHERE '+where+' ORDER BY r.rowid DESC',args)
            for row in cursor:
                self.check()
                yield json.loads(row['data'])

    def get(self,kind,id):
        self.check()
        row=self.db.execute('SELECT data FROM records WHERE kind=%s AND id=%s',(kind,id)).fetchone()
        return json.loads(row['data']) if row else None
