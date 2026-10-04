"""Explicit persistence operations for one atomic reviewed asset import."""
import json
from .audit import append_event as sqlite_event
from .postgres_store import text,append_event as postgres_event


def encoded(record):
    return json.dumps(record,ensure_ascii=False)


class SQLiteImports:
    def __init__(self,db):self.db=db

    def read(self,kind,id):
        row=self.db.execute('SELECT data FROM records WHERE kind=? AND id=?',(kind,id)).fetchone()
        return json.loads(row['data']) if row else None

    def assets(self,url):
        return [json.loads(row['data']) for row in self.db.execute("SELECT data FROM records WHERE kind='assets' AND json_extract(data,'$.url')=? LIMIT 2",(url,)).fetchall()]

    def expire(self,timestamp):
        self.db.execute("DELETE FROM records WHERE kind='import_previews' AND json_extract(data,'$.expires_at')<=?",(timestamp,))

    def count(self):
        return self.db.execute("SELECT count(*) AS count FROM records WHERE kind='import_previews'").fetchone()['count']

    def insert(self,kind,record):
        self.db.execute('INSERT INTO records(kind,id,data) VALUES (?,?,?)',(kind,record['id'],encoded(record)))

    def update(self,kind,record):
        self.db.execute('UPDATE records SET data=? WHERE kind=? AND id=?',(encoded(record),kind,record['id']))

    def source(self,record):
        self.db.execute("INSERT INTO records(kind,id,data) VALUES ('asset_sources',?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",(record['id'],encoded(record)))

    def event(self,values):
        return sqlite_event(self.db,values)


class PostgresImports:
    def __init__(self,db):self.db=db

    def read(self,kind,id):
        row=self.db.execute('SELECT data FROM records WHERE kind=%s AND id=%s',(kind,id)).fetchone()
        return json.loads(row['data']) if row else None

    def assets(self,url):
        return [json.loads(row['data']) for row in self.db.execute("SELECT data FROM records WHERE kind='assets' AND "+text('url')+'=%s LIMIT 2',(url,)).fetchall()]

    def expire(self,timestamp):
        self.db.execute("DELETE FROM records WHERE kind='import_previews' AND CASE WHEN jsonb_typeof(data::jsonb->'expires_at')='number' THEN (data::jsonb->>'expires_at')::numeric ELSE NULL END<=%s",(timestamp,))

    def count(self):
        return self.db.execute("SELECT count(*) AS count FROM records WHERE kind='import_previews'").fetchone()['count']

    def insert(self,kind,record):
        self.db.execute('INSERT INTO records(kind,id,data) VALUES (%s,%s,%s)',(kind,record['id'],encoded(record)))

    def update(self,kind,record):
        self.db.execute('UPDATE records SET data=%s WHERE kind=%s AND id=%s',(encoded(record),kind,record['id']))

    def source(self,record):
        self.db.execute("INSERT INTO records(kind,id,data) VALUES ('asset_sources',%s,%s) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",(record['id'],encoded(record)))

    def event(self,values):
        return postgres_event(self.db,values)
