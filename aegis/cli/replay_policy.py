"""Validate an API policy artifact; send scoped GET requests only with --run."""
import argparse
import json
from pathlib import Path
from pydantic import ValidationError
from ..reproduction import MAX_MANIFEST_BYTES, PolicyManifest, replay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--run', action='store_true', help='Confirm current permission and execute the exported scope')
    parser.add_argument('--lab', action='store_true', help='Allow private/loopback addresses for an owned isolated fixture')
    args = parser.parse_args()
    if args.lab and not args.run:
        parser.error('--lab은 --run과 함께 사용하세요.')
    try:
        with Path(args.source).open('rb') as file:
            payload = file.read(MAX_MANIFEST_BYTES + 1)
        if len(payload) > MAX_MANIFEST_BYTES:
            raise ValueError()
        def pairs(entries):
            result = {}
            for key, value in entries:
                if key in result:
                    raise ValueError()
                result[key] = value
            return result

        manifest = PolicyManifest.model_validate(json.loads(payload.decode('utf-8-sig'), object_pairs_hook=pairs))
        if not args.run:
            print(json.dumps({'valid': True, 'executed': False, 'task_id': manifest.task_id,
                              'assets': len(manifest.assets), 'rules': sum(len(a.authorization_rules) for a in manifest.assets)}))
            return
        result = replay(manifest, lab=args.lab)
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(0 if result['passed'] else 1)
    except (ValueError, OSError, ValidationError, RecursionError):
        parser.error('정책 파일의 형식·범위·실행 제한을 확인하세요. 입력 내용은 출력하지 않습니다.')
    except KeyboardInterrupt:
        parser.exit(130, '검증을 중지했습니다.\n')


if __name__ == '__main__':
    main()
