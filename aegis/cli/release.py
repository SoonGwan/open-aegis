"""Offline signed bundle creation/verification and pre-update backup."""
import argparse
import json
import os
from pathlib import Path
from ..releases import create_release,verify_release,prepare_update,prepare_postgres_update
from ..maintenance import WorkspaceBusy
from zipfile import BadZipFile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    create=commands.add_parser('create')
    for name in ('wheel','web','lock','output','private-key','revision'):
        create.add_argument('--'+name,required=True)
    create.add_argument('--postgres-lock',help='Include signed PostgreSQL dependency lock and native compatibility declaration')
    verify=commands.add_parser('verify')
    prepare=commands.add_parser('prepare')
    for command in (verify,prepare):
        command.add_argument('--bundle',required=True)
        command.add_argument('--public-key',required=True)
    prepare.add_argument('--backend',choices=['sqlite','postgres'],default=os.environ.get('AEGIS_STORAGE_BACKEND','sqlite'))
    prepare.add_argument('--schema',default=os.environ.get('AEGIS_POSTGRES_SCHEMA',''))
    prepare.add_argument('--database',help='SQLite file only; unavailable with PostgreSQL backend')
    prepare.add_argument('--output',required=True)
    args=vars(parser.parse_args());command=args.pop('command')
    native_errors=();backend=args.get('backend')
    try:
        if command=='prepare':
            backend=args.pop('backend');schema=args.pop('schema');database=args.pop('database')
            if backend not in ('sqlite','postgres'):raise ValueError('Unknown backend')
            if backend=='postgres':
                if database:raise ValueError('SQLite file is incompatible with PostgreSQL backend')
                from ..postgres_transfer import driver
                native_errors=(driver()[0].Error,)
                result=prepare_postgres_update(dsn=os.environ.get('AEGIS_POSTGRES_DSN',''),schema=schema,**args)
            else:
                database=database or str(Path(os.environ.get('AEGIS_DATA_DIR','data'))/'aegis.db')
                result=prepare_update(database=database,**args)
        else:result={'create':create_release,'verify':verify_release}[command](**args)
    except (ValueError,OSError,WorkspaceBusy,BadZipFile,TypeError,KeyError,RecursionError)+native_errors as exc:
        parser.error('PostgreSQL 업데이트 사전 점검 실패: 서명·호환성·연결·서버 중지·백업 경로를 확인하세요.' if backend=='postgres' else str(exc))
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
