"""Initialize a new native PostgreSQL schema; never replace an existing workspace."""
import argparse
import json
import os
from ..postgres_bootstrap import initialize
from ..postgres_transfer import driver
from ..maintenance import WorkspaceBusy


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schema',default=os.environ.get('AEGIS_POSTGRES_SCHEMA',''))
    args=parser.parse_args();native_errors=()
    try:
        native_errors=(driver()[0].Error,)
        result=initialize(os.environ.get('AEGIS_POSTGRES_DSN',''),args.schema)
    except (ValueError,OSError,WorkspaceBusy)+native_errors:
        parser.error('PostgreSQL 초기화 실패: 연결·CREATE 권한·새 스키마 또는 실행 소유권을 확인하세요.')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
