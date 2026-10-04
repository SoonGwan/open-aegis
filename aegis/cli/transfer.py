"""Offline SQLite/PostgreSQL transfer. Never prints connection credentials/errors."""
import argparse
import json
import os
from .. import postgres_transfer


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    forward=commands.add_parser('sqlite-to-postgres')
    forward.add_argument('--source',required=True);forward.add_argument('--schema',required=True)
    reverse=commands.add_parser('postgres-to-sqlite')
    reverse.add_argument('--output',required=True);reverse.add_argument('--schema',required=True)
    args=parser.parse_args()
    dsn=os.environ.get('AEGIS_POSTGRES_DSN','')
    try:
        if args.command=='sqlite-to-postgres':
            result=postgres_transfer.sqlite_to_postgres(args.source,dsn,args.schema)
        else:
            result=postgres_transfer.postgres_to_sqlite(dsn,args.schema,args.output)
        print(json.dumps(result,ensure_ascii=False))
    except Exception:
        parser.exit(1,'저장소 전송에 실패했습니다. 연결·권한·서버 중지·스키마·감사 검증을 확인하세요. 기존 대상은 덮어쓰지 않습니다.\n')


if __name__=='__main__':main()
