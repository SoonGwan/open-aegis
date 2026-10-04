"""Consistent online data backup. Includes credential hashes: protect the file."""
import argparse
import json
import os
from pathlib import Path
from ..backups import backup_database


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=['sqlite','postgres'],default=os.environ.get('AEGIS_STORAGE_BACKEND','sqlite'))
    parser.add_argument('--source',help='SQLite source file; unavailable with PostgreSQL backend')
    parser.add_argument('--schema',default=os.environ.get('AEGIS_POSTGRES_SCHEMA',''))
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    native_errors=()
    try:
        if args.backend not in ('sqlite','postgres'):raise ValueError('Unknown storage backend')
        if args.backend=='postgres':
            if args.source:raise ValueError('SQLite source is incompatible with PostgreSQL backend')
            from ..postgres_backups import backup
            from ..postgres_transfer import driver
            native_errors=(driver()[0].Error,)
            metadata=backup(os.environ.get('AEGIS_POSTGRES_DSN',''),args.schema,args.output)
        else:
            source=args.source or str(Path(os.environ.get('AEGIS_DATA_DIR','data'))/'aegis.db')
            metadata=backup_database(source,args.output)
    except (ValueError, OSError) + native_errors as exc:
        parser.error('PostgreSQL 백업 실패: 연결 설정, 스키마 또는 출력 경로를 확인하세요.' if args.backend=='postgres' else str(exc))
    print(json.dumps({'output': args.output, **metadata}, ensure_ascii=False))


if __name__ == '__main__':
    main()
