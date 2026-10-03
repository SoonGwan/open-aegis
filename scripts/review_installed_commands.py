"""Rehearse maintenance commands from a wheel in an isolated, disposable installation."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import venv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', required=True, type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    environment = {key: value for key, value in os.environ.items()
                   if key not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV')}
    with tempfile.TemporaryDirectory(prefix='aegis-package-review-') as temporary:
        root = Path(temporary)
        installation = root / 'installation'
        venv.EnvBuilder(with_pip=True).create(installation)
        binaries = installation / 'bin'
        python = binaries / 'python'

        def run(command, expected=0):
            result = subprocess.run([str(item) for item in command], cwd=root,
                                    env=environment, capture_output=True, text=True, timeout=60)
            if result.returncode != expected:
                raise RuntimeError(f'Unexpected exit {result.returncode}: {result.stderr}')
            return result.stdout

        run([python, '-m', 'pip', 'install', '--no-index', '--no-deps', wheel])
        origin = json.loads(run([python, '-I', '-c',
            'import aegis,json; from pathlib import Path; import sys; '
            'assert Path(aegis.__file__).is_relative_to(Path(sys.prefix)); '
            'print(json.dumps({"module":aegis.__file__}))']))
        source = root / 'live' / 'aegis.db'
        run([python, '-I', '-c',
            'from aegis.store import Store; import sys; '
            's=Store(sys.argv[1]); s.put("notes", {"id":"fixture","title":"설치 검증"}); '
            's.event(None,"installed fixture"); '
            'db=s.connect(); '
            'db.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)", '
            '("fixture","fixture","fixture","admin","unused","unused",0,0,0)); '
            'db.execute("INSERT INTO sessions VALUES (?,?,?)",("fixture",9999999999,"fixture")); '
            'db.commit(); db.close()', source])

        def command(name, *arguments, expected=0):
            output = run([binaries / ('aegis-' + name), *arguments], expected)
            return json.loads(output) if expected == 0 else None

        backup = root / 'backup 한글 ?' / 'snapshot.db'
        metadata = command('backup', '--source', source, '--output', backup)
        assert metadata['records']['notes'] == 1
        assert backup.stat().st_mode & 0o777 == 0o600
        before = backup.read_bytes()
        command('backup', '--source', source, '--output', backup, expected=2)
        assert backup.read_bytes() == before
        command('restore', '--source', backup, '--check-only')
        checkpoint = root / 'checkpoint.json'
        audit = command('verify-audit', '--source', source, '--output', checkpoint)
        assert audit['events'] == 1
        restored = root / 'restored' / 'aegis.db'
        assert command('restore', '--source', backup, '--destination', restored)['sessions_revoked']
        assert command('verify-audit', '--source', restored, '--checkpoint', checkpoint)['events'] == 1
        with sqlite3.connect(restored) as db:
            assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 0
            assert json.loads(db.execute("SELECT data FROM records WHERE kind='notes'").fetchone()[0])['title'] == '설치 검증'
        run([python, '-I', '-c',
             'from aegis.store import Store; import sys; '
             'Store(sys.argv[1]).put("notes", {"id":"later","title":"rollback fixture"})', restored])
        with (restored.parent / '.server.lock').open('a+') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            command('restore', '--source', backup, '--destination', restored, expected=2)
            with sqlite3.connect(restored) as db:
                assert db.execute('SELECT COUNT(*) FROM records').fetchone()[0] == 2
        rollback = command('restore', '--source', backup, '--destination', restored)['rollback']
        assert command('restore', '--source', rollback, '--check-only')['records']['notes'] == 2
        assert command('restore', '--source', restored, '--check-only')['records']['notes'] == 1
        with sqlite3.connect(backup) as db:
            db.execute("UPDATE events SET message='tampered'")
        rejected = root / 'rejected' / 'aegis.db'
        command('restore', '--source', backup, '--destination', rejected, expected=2)
        assert not rejected.exists()
        command('verify-audit', '--source', backup, expected=2)
        print(json.dumps({'valid': True, 'wheel': wheel.name,
                          'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
                          'installed_origin': origin['module'], 'schema': metadata['schema_version'],
                          'checks': ['installed commands outside checkout', 'backup 0600',
                                     'overwrite rejected', 'backup check-only', 'audit checkpoint',
                                     'restore data and revoke sessions', 'restored checkpoint matches',
                                     'busy workspace refused', 'previous data preserved for rollback',
                                     'tampered backup refused before replacement']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
