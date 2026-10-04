"""Read-only audit verification with an optional independently trusted checkpoint."""
import argparse
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from ..audit import verify_chain, AuditIntegrityError
from ..backups import readonly


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=['sqlite','postgres'],default=os.environ.get('AEGIS_STORAGE_BACKEND','sqlite'))
    parser.add_argument('--schema',default=os.environ.get('AEGIS_POSTGRES_SCHEMA',''))
    parser.add_argument('--source',help='SQLite source file; unavailable with PostgreSQL backend')
    parser.add_argument('--checkpoint', help='Previously exported checkpoint from trusted independent storage')
    parser.add_argument('--output', help='Create a new checkpoint file; never overwrite an existing file')
    args = parser.parse_args()
    native_errors=()
    try:
        if args.backend not in ('sqlite','postgres'):raise ValueError('Unknown storage backend')
        if args.backend=='postgres' and args.source:raise ValueError('SQLite source is incompatible with PostgreSQL backend')
        checkpoint = None
        if args.checkpoint:
            with Path(args.checkpoint).open('rb') as file:
                raw = file.read(4097)
            if len(raw) > 4096:
                raise AuditIntegrityError('체크포인트 파일이 너무 큽니다.')
            checkpoint = json.loads(raw)
        if args.backend=='postgres':
            from ..postgres_store import PostgresStore
            from ..postgres_transfer import driver
            native_errors=(driver()[0].Error,)
            store=PostgresStore(os.environ.get('AEGIS_POSTGRES_DSN',''),args.schema)
            result=store.audit_integrity(checkpoint)
        else:
            source=args.source or str(Path(os.environ.get('AEGIS_DATA_DIR','data'))/'aegis.db')
            with closing(readonly(source)) as db:
                db.row_factory = sqlite3.Row
                db.execute('BEGIN')
                result = verify_chain(db, checkpoint)
        if args.output:
            payload = (json.dumps(result['checkpoint'], ensure_ascii=False) + '\n').encode()
            fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, 'wb') as file:
                file.write(payload)
                file.flush()
                os.fsync(file.fileno())
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, sqlite3.Error) + native_errors as exc:
        parser.error('감사 로그 검증 실패: ' + (str(exc) if isinstance(exc, AuditIntegrityError) else '파일 또는 스키마를 확인하세요.'))


if __name__ == '__main__':
    main()
