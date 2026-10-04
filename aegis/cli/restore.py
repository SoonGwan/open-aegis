"""Verify and restore data; PostgreSQL requires a new schema, SQLite keeps rollback."""
import argparse
import json
import os
from pathlib import Path
from ..backups import restore_database, validate_backup
from ..maintenance import WorkspaceBusy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=['sqlite','postgres'],default=os.environ.get('AEGIS_STORAGE_BACKEND','sqlite'))
    parser.add_argument('--source', required=True)
    parser.add_argument('--destination',help='SQLite destination file; unavailable with PostgreSQL backend')
    parser.add_argument('--schema',default=os.environ.get('AEGIS_POSTGRES_SCHEMA',''),help='New PostgreSQL schema; existing schemas are never replaced')
    parser.add_argument('--checkpoint',help='PostgreSQL archive: independently trusted audit checkpoint file')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    native_errors=()
    try:
        if args.backend not in ('sqlite','postgres'):raise ValueError('Unknown storage backend')
        if args.backend=='postgres':
            if args.destination:raise ValueError('SQLite destination is incompatible with PostgreSQL backend')
            from ..postgres_backups import restore,validate,unique,invalid
            checkpoint=None
            if args.checkpoint:
                with Path(args.checkpoint).open('rb') as file:raw=file.read(4097)
                if len(raw)>4096:raise ValueError('Checkpoint is too large')
                checkpoint=json.loads(raw,object_pairs_hook=unique,parse_constant=invalid)
                if not isinstance(checkpoint,dict):raise ValueError('Invalid checkpoint')
            if args.check_only:result=validate(args.source,checkpoint)
            else:
                from ..postgres_transfer import driver
                native_errors=(driver()[0].Error,)
                result=restore(args.source,os.environ.get('AEGIS_POSTGRES_DSN',''),args.schema,checkpoint)
        else:
            if args.checkpoint:raise ValueError('Use aegis-verify-audit for a SQLite checkpoint')
            destination=args.destination or str(Path(os.environ.get('AEGIS_DATA_DIR','data'))/'aegis.db')
            result=validate_backup(args.source) if args.check_only else restore_database(args.source,destination)
    except (ValueError, OSError, WorkspaceBusy, KeyError, TypeError, UnicodeError, RecursionError) + native_errors as exc:
        parser.error('PostgreSQL 복구 실패: 백업·체크포인트, 연결 설정 또는 새 스키마를 확인하세요.' if args.backend=='postgres' else str(exc))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
