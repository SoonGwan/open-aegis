"""Actual native read-only snapshot checkpoint capture and CLI."""
import json
import os
import subprocess
import sys
import pytest
from aegis.audit import AuditIntegrityError
from aegis.checkpoint_archive import capture_checkpoint
from tests.test_postgres_transfer import postgres, schema
from tests.test_postgres_store import stores


def test_native_capture_no_writes_prefix_and_truncation(stores, tmp_path):
    _, pg = stores
    pg.event(None, 'SECRET-ORIGINAL')
    destination = tmp_path/'independent'
    before = pg.audit_integrity()
    first = capture_checkpoint(pg.audit_integrity, destination)
    assert first['checkpoint'] == before['checkpoint']
    assert pg.audit_integrity() == before
    pg.event(None, 'second')
    second = capture_checkpoint(pg.audit_integrity, destination)
    assert second['events'] == 2 and second['created']
    assert capture_checkpoint(pg.audit_integrity, destination)['created'] is False
    with pg.transaction(write=True) as db:
        db.execute('DELETE FROM event_hashes WHERE seq>%s', (first['checkpoint']['seq'],))
        db.execute('DELETE FROM events WHERE seq>%s', (first['checkpoint']['seq'],))
        db.execute('UPDATE audit_state SET last_seq=%s,head_hash=%s', (first['checkpoint']['seq'], first['checkpoint']['hash']))
    assert pg.audit_integrity()['valid']
    with pytest.raises(AuditIntegrityError): capture_checkpoint(pg.audit_integrity, destination)
    assert len(list(destination.glob('checkpoint-*.json'))) == 2


def test_native_cli_capture_and_source_incompatibility(stores, tmp_path):
    _, pg = stores
    pg.event(None, 'DO-NOT-EXPOSE')
    before = pg.audit_integrity()
    environment = {**os.environ, 'AEGIS_STORAGE_BACKEND':'postgres', 'AEGIS_POSTGRES_DSN':pg._dsn, 'AEGIS_POSTGRES_SCHEMA':pg.schema}
    command = [sys.executable, '-m', 'aegis.cli.checkpoint', '--destination', str(tmp_path/'archive')]
    first = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
    assert first.returncode == 0 and json.loads(first.stdout)['created']
    second = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
    assert second.returncode == 0 and not json.loads(second.stdout)['created']
    refused = subprocess.run([*command, '--source', str(tmp_path/'forbidden.db')], env=environment, capture_output=True, text=True, timeout=10)
    assert refused.returncode == 2 and not (tmp_path/'forbidden.db').exists()
    assert 'DO-NOT-EXPOSE' not in first.stdout+first.stderr+refused.stdout+refused.stderr
    assert pg.audit_integrity() == before
