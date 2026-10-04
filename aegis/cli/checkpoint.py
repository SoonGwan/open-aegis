"""Verify the audit chain against its latest archived checkpoint and append a new one."""
import argparse
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from ..audit import verify_chain, AuditIntegrityError
from ..backups import readonly
from ..checkpoint_archive import capture_checkpoint, CheckpointArchiveError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=['sqlite', 'postgres'], default=os.environ.get('AEGIS_STORAGE_BACKEND','sqlite'))
    parser.add_argument('--source', help='SQLite source file; unavailable with PostgreSQL backend')
    parser.add_argument('--schema', default=os.environ.get('AEGIS_POSTGRES_SCHEMA',''))
    parser.add_argument('--destination', required=True, help='Independent checkpoint directory; append-only, one chain per directory')
    args = parser.parse_args()
    native_errors = ()
    try:
        if args.backend not in ('sqlite', 'postgres'):
            raise ValueError('Unknown storage backend')
        if args.backend == 'postgres':
            if args.source:
                raise ValueError('SQLite source is incompatible with PostgreSQL backend')
            from ..postgres_store import PostgresStore
            from ..postgres_transfer import driver
            native_errors = (driver()[0].Error,)
            store = PostgresStore(os.environ.get('AEGIS_POSTGRES_DSN',''), args.schema)
            verify = store.audit_integrity
        else:
            source = args.source or str(Path(os.environ.get('AEGIS_DATA_DIR','data'))/'aegis.db')
            def verify(previous):
                with closing(readonly(source)) as db:
                    db.row_factory = sqlite3.Row
                    db.execute('BEGIN')
                    return verify_chain(db, previous)
        print(json.dumps(capture_checkpoint(verify, args.destination), ensure_ascii=False))
    except (ValueError, OSError, sqlite3.Error) + native_errors as exc:
        detail = str(exc) if isinstance(exc, (AuditIntegrityError, CheckpointArchiveError)) else '파일, 보관 경로 또는 스키마를 확인하세요.'
        parser.error('감사 체크포인트 보관 실패: '+detail)


if __name__ == '__main__':
    main()
