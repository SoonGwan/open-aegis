"""Consistent online SQLite backup. Includes credential hashes: protect the file."""
import argparse
import json
from ..backups import backup_database


def main():
    parser = argparse.ArgumentParser(description='Back up Open Aegis SQLite data')
    parser.add_argument('--source', default='data/aegis.db')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        metadata = backup_database(args.source, args.output)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({'output': args.output, **metadata}, ensure_ascii=False))


if __name__ == '__main__':
    main()
