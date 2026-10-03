"""Consistent backup and offline restore with validation, rollback copy and session revocation."""
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from .maintenance import WorkspaceLease
from .migrations import SCHEMA_VERSION
from .store_util import identifier


class InvalidBackup(ValueError):
    pass


def readonly(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=15)


def validate_backup(path):
    path = Path(path)
    if not path.is_file():
        raise InvalidBackup('백업 파일이 없습니다.')
    try:
        with closing(readonly(path)) as db:
            if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise InvalidBackup('SQLite 무결성 검증을 통과하지 못했습니다.')
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, SCHEMA_VERSION):
                raise InvalidBackup('이 서버에서 지원하지 않는 백업 스키마입니다.')
            required = {'records': {'kind', 'id', 'data'},
                        'events': {'seq', 'ts', 'task_id', 'level', 'message', 'detail'},
                        'sessions': {'digest', 'expires'}}
            if version == SCHEMA_VERSION:
                required['users'] = {'id', 'username', 'name', 'role', 'salt', 'password_hash', 'disabled', 'created_at', 'updated_at'}
                required['sessions'].add('user_id')
            for table, columns in required.items():
                if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                    raise InvalidBackup('필수 데이터 테이블이 없습니다: ' + table)
                if not columns <= {r[1] for r in db.execute(f'PRAGMA table_info({table})')}:
                    raise InvalidBackup('데이터 테이블 형식이 올바르지 않습니다: ' + table)
            invalid = db.execute('SELECT COUNT(*) FROM records WHERE NOT json_valid(data)').fetchone()[0]
            if invalid:
                raise InvalidBackup('손상된 JSON 기록이 있습니다.')
            if db.execute('PRAGMA foreign_key_check').fetchone():
                raise InvalidBackup('참조 무결성을 통과하지 못했습니다.')
            counts = dict(db.execute('SELECT kind,COUNT(*) FROM records GROUP BY kind'))
            return {'schema_version': version, 'records': counts}
    except sqlite3.Error as exc:
        raise InvalidBackup('SQLite 백업을 읽을 수 없습니다.') from exc


def backup_database(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.is_file():
        raise InvalidBackup('원본 DB가 없습니다.')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with closing(readonly(source)) as src, closing(sqlite3.connect(output)) as dst:
            src.backup(dst)
            dst.execute("PRAGMA journal_mode=DELETE")
        result = validate_backup(output)
        with output.open("rb") as file:
            os.fsync(file.fileno())
        return result
    except BaseException:
        output.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm"):
            Path(str(output) + suffix).unlink(missing_ok=True)
        raise


def restore_database(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise InvalidBackup('원본 백업과 복구 대상은 다른 경로여야 합니다.')
    metadata = validate_backup(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rollback = None
    with WorkspaceLease(destination.parent):
        fd, temporary = tempfile.mkstemp(prefix='.restore-', suffix='.db', dir=destination.parent)
        os.close(fd)
        stage = Path(temporary)
        try:
            with closing(readonly(source)) as src, closing(sqlite3.connect(stage)) as target:
                src.backup(target)
                target.execute('PRAGMA journal_mode=DELETE')
                target.execute('DELETE FROM sessions')
                target.commit()
            validate_backup(stage)
            if destination.exists():
                with closing(sqlite3.connect(destination, timeout=15)) as existing:
                    busy, _, _ = existing.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
                    if busy:
                        raise InvalidBackup('기존 DB가 사용 중입니다. 모든 프로세스를 종료하세요.')
                rollback = destination.with_name(destination.name + '.pre-restore-' + identifier() + '.db')
                backup_database(destination, rollback)
            # The workspace lease protects cooperating server/restore processes.
            # Preserve old state in rollback before removing obsolete WAL sidecars.
            for suffix in ('-wal', '-shm'):
                Path(str(destination) + suffix).unlink(missing_ok=True)
            with stage.open('rb') as file:
                os.fsync(file.fileno())
            os.replace(stage, destination)
            destination.chmod(0o600)
            dir_fd = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        finally:
            stage.unlink(missing_ok=True)
            for suffix in ('-wal', '-shm'):
                Path(str(stage) + suffix).unlink(missing_ok=True)
    return {**metadata, 'sessions_revoked': True, 'rollback': str(rollback) if rollback else None}
