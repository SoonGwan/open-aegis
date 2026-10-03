"""Transactional schema migrations. Older schemas receive a consistent preflight backup."""
import json
import os
import sqlite3
from pathlib import Path
from contextlib import closing
from .store_util import now, identifier

SCHEMA_VERSION = 2


def migrate(path):
    path = Path(path)
    existed = path.is_file() and path.stat().st_size > 0
    with closing(sqlite3.connect(path)) as db:
        version = db.execute('PRAGMA user_version').fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError('데이터 스키마가 이 서버보다 최신입니다. 이전 서버로 열 수 없습니다.')
        if version == SCHEMA_VERSION:
            return
        legacy = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='records'").fetchone()
        if existed and legacy:
            backup = path.with_name(path.name + f'.pre-schema{SCHEMA_VERSION}-' + identifier() + '.db')
            fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            with closing(sqlite3.connect(backup)) as target:
                db.backup(target)
        try:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('PRAGMA user_version').fetchone()[0] == SCHEMA_VERSION:
                db.rollback()
                return
            statements = [
                'CREATE TABLE IF NOT EXISTS records (kind TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(kind,id))',
                'CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, task_id TEXT, level TEXT, message TEXT, detail TEXT)',
                "CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','operator','viewer')), salt TEXT NOT NULL, password_hash TEXT NOT NULL, disabled INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL, updated_at REAL NOT NULL)",
                'CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY, expires REAL NOT NULL, user_id TEXT NOT NULL REFERENCES users(id))',
                'CREATE INDEX IF NOT EXISTS events_task_seq ON events(task_id,seq)',
            ]
            for statement in statements:
                db.execute(statement)
            columns = {row[1] for row in db.execute('PRAGMA table_info(sessions)')}
            if 'user_id' not in columns:
                # Legacy sessions must never acquire admin privileges implicitly.
                db.execute('DROP TABLE sessions')
                db.execute('CREATE TABLE sessions (digest TEXT PRIMARY KEY, expires REAL NOT NULL, user_id TEXT NOT NULL REFERENCES users(id))')
            row = db.execute("SELECT data FROM records WHERE kind='settings' AND id='auth'").fetchone()
            if row:
                auth = json.loads(row[0])
                db.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)',
                           ('legacy-admin', 'admin', '관리자', 'admin', auth['salt'], auth['password_hash'], 0, now(), now()))
                db.execute("DELETE FROM records WHERE kind='settings' AND id='auth'")
                db.execute('DELETE FROM sessions')
            db.execute('CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id)')
            from .audit import initialize_chain
            initialize_chain(db)
            db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
            db.commit()
        except BaseException:
            db.rollback()
            raise
    path.chmod(0o600)
