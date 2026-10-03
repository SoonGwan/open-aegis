"""Offline restore: verifies backup, preserves previous DB, revokes restored sessions."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aegis.backups import restore_database, validate_backup
from aegis.maintenance import WorkspaceBusy


def main():
    parser = argparse.ArgumentParser(description='Validate or restore an Open Aegis backup')
    parser.add_argument('--source', required=True)
    parser.add_argument('--destination', default='data/aegis.db')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    try:
        result = validate_backup(args.source) if args.check_only else restore_database(args.source, args.destination)
    except (ValueError, OSError, WorkspaceBusy) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
