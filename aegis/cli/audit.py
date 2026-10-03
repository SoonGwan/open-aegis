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
    parser.add_argument('--source', default='data/aegis.db')
    parser.add_argument('--checkpoint', help='Previously exported checkpoint from trusted independent storage')
    parser.add_argument('--output', help='Create a new checkpoint file; never overwrite an existing file')
    args = parser.parse_args()
    try:
        checkpoint = None
        if args.checkpoint:
            with Path(args.checkpoint).open('rb') as file:
                raw = file.read(4097)
            if len(raw) > 4096:
                raise AuditIntegrityError('체크포인트 파일이 너무 큽니다.')
            checkpoint = json.loads(raw)
        with closing(readonly(args.source)) as db:
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
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.error('감사 로그 검증 실패: ' + (str(exc) if isinstance(exc, AuditIntegrityError) else '파일 또는 스키마를 확인하세요.'))


if __name__ == '__main__':
    main()
