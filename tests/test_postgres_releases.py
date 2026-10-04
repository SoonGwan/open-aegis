"""Signed native compatibility, stopped-workspace backup and failure cleanup."""
import json
import os
from pathlib import Path
import subprocess
import sys
from contextlib import contextmanager

import pytest
from aegis import postgres_transfer as transfer,postgres_backups as backups
from aegis.releases import create_release,verify_release,prepare_postgres_update,ReleaseError,digest
from aegis.maintenance import WorkspaceBusy
from aegis.postgres_store import PostgresStore
from tests.test_releases import release,resign
from tests.test_postgres_transfer import postgres,source,schema


@pytest.fixture
def native_release(release,tmp_path):
    bundle,key,public=release
    manifest=verify_release(bundle,public)
    lock=tmp_path/'postgres.lock';lock.write_text('psycopg[binary]==3.3.6\n')
    output=tmp_path/'native-bundle'
    create_release(bundle/manifest['wheel'],bundle/'web',bundle/'requirements.lock',output,key,'b'*40,postgres_lock=lock)
    return output,key,public


@pytest.fixture
def native(postgres,source):
    name=schema();transfer.sqlite_to_postgres(source.path,postgres['dsn'],name)
    return PostgresStore(postgres['dsn'],name)


def test_signed_native_bundle_and_legacy_bundle_remain_distinct(native_release,release):
    bundle,_,public=native_release;manifest=verify_release(bundle,public)
    assert manifest['format']==2 and manifest['postgres']=={'format':transfer.FORMAT,'read':[2,2],'write':2,'lock':'requirements-postgres.lock'}
    assert manifest['files']['requirements-postgres.lock']==digest(bundle/'requirements-postgres.lock')
    old,_,old_public=release;assert verify_release(old,old_public)['format']==1


@pytest.mark.parametrize('mutation',['type','range','write','lock','format','extra','missing_lock','tamper_lock'])
def test_native_manifest_and_dependency_payload_mutations_are_refused(native_release,mutation):
    bundle,key,public=native_release;manifest=json.loads((bundle/'release.json').read_text())
    if mutation=='type':manifest['postgres']['read']=[True,2]
    elif mutation=='range':manifest['postgres']['read']=[3,2]
    elif mutation=='write':manifest['postgres']['write']=True
    elif mutation=='lock':manifest['postgres']['lock']='../unreviewed.lock'
    elif mutation=='format':manifest['postgres']['format']='other-storage'
    elif mutation=='extra':manifest['postgres']['execute']='unreviewed command'
    elif mutation=='missing_lock':
        (bundle/'requirements-postgres.lock').unlink();manifest['files'].pop('requirements-postgres.lock')
    else:(bundle/'requirements-postgres.lock').write_text('tampered==1\n')
    resign(bundle,key,manifest)
    with pytest.raises(ReleaseError):verify_release(bundle,public)


def test_stopped_native_preflight_keeps_source_and_restores_exact_data(native_release,native,postgres,tmp_path):
    bundle,_,public=native_release;user=native.user(username='admin')
    native.session('preserve-source-cookie',9_999_999_999,user['id'])
    with native.read_transaction() as db:before=transfer.postgres_manifest(db)
    output=tmp_path/'preflight';receipt=prepare_postgres_update(bundle,public,postgres['dsn'],native.schema,output)
    assert receipt['installed'] is False and receipt['postgres_write']==2 and receipt['backend']=='postgres'
    assert (output/'before-update.zip').stat().st_mode&0o777==0o600 and (output/'preflight.json').stat().st_mode&0o777==0o600
    assert output.stat().st_mode&0o777==0o700 and json.loads((output/'preflight.json').read_text())==receipt
    assert receipt['backup']==digest(output/'before-update.zip') and 'output' not in receipt['backup_metadata']
    assert postgres['dsn'] not in json.dumps(receipt) and native.valid_session('preserve-source-cookie')
    with native.read_transaction() as db:assert transfer.postgres_manifest(db)==before
    native.put('notes',{'id':'later','title':'Simulate new runtime write'})
    restored=schema();backups.restore(output/'before-update.zip',postgres['dsn'],restored)
    copy=PostgresStore(postgres['dsn'],restored)
    with copy.read_transaction() as db:assert transfer.postgres_manifest(db)==before
    assert copy.get('notes','later') is None and not copy.valid_session('preserve-source-cookie')
    assert copy.user(username='admin')==user and native.valid_session('preserve-source-cookie')
    with pytest.raises(ReleaseError):prepare_postgres_update(bundle,public,postgres['dsn'],native.schema,output)
    assert not list(tmp_path.glob('.pg-preflight-*'))


@pytest.mark.parametrize('cause',['owner','unfinished','incompatible','downgrade','legacy','audit'])
def test_refused_preflight_never_publishes(native_release,release,native,postgres,tmp_path,cause):
    bundle,key,public=native_release;output=tmp_path/'refused';owner=None
    if cause=='owner':owner=native.acquire_runtime()
    elif cause=='unfinished':native.patch('tasks','owned-task',status='running')
    elif cause=='incompatible':
        manifest=json.loads((bundle/'release.json').read_text());manifest['postgres'].update(read=[3,3],write=3);resign(bundle,key,manifest)
    elif cause=='downgrade':
        manifest=json.loads((bundle/'release.json').read_text());manifest['postgres'].update(read=[1,2],write=1);resign(bundle,key,manifest)
    elif cause=='legacy':bundle,_,public=release
    else:
        with native.write_transaction() as db:db.execute("UPDATE events SET message='tampered'")
    try:
        with pytest.raises((ReleaseError,WorkspaceBusy,ValueError)):prepare_postgres_update(bundle,public,postgres['dsn'],native.schema,output)
    finally:
        if owner:owner.close()
    assert not output.exists() and not list(tmp_path.glob('.pg-preflight-*'))


def test_backup_failure_and_transaction_exit_failure_remove_unpublished_receipt(native_release,native,postgres,tmp_path,monkeypatch):
    bundle,_,public=native_release;original=transfer.connect
    class ExitFailure:
        def __init__(self,db):self.db=db
        def __getattr__(self,key):return getattr(self.db,key)
        def __enter__(self):self.db.__enter__();return self
        def __exit__(self,*args):return self.db.__exit__(*args)
        @contextmanager
        def transaction(self):
            with self.db.transaction():yield
            raise RuntimeError('Owned preflight read exit failure')
    calls=0
    def first_only(dsn):
        nonlocal calls
        calls+=1;db=original(dsn);return ExitFailure(db) if calls==1 else db
    with monkeypatch.context() as patch:
        patch.setattr(transfer,'connect',first_only)
        with pytest.raises(RuntimeError):prepare_postgres_update(bundle,public,postgres['dsn'],native.schema,tmp_path/'exit-refused')
    def fail(*args,**kwargs):raise RuntimeError('Owned backup verification failure')
    with monkeypatch.context() as patch:
        patch.setattr(backups,'backup',fail)
        with pytest.raises(RuntimeError):prepare_postgres_update(bundle,public,postgres['dsn'],native.schema,tmp_path/'backup-refused')
    assert not (tmp_path/'exit-refused').exists() and not (tmp_path/'backup-refused').exists() and not list(tmp_path.glob('.pg-preflight-*'))


def test_gate_blocks_new_owner_until_backup_finishes(native_release,native,postgres,tmp_path,monkeypatch):
    bundle,_,public=native_release;original=backups.backup
    def guarded(*args,**kwargs):
        fresh=PostgresStore(postgres['dsn'],native.schema)
        with pytest.raises(WorkspaceBusy):fresh.acquire_runtime()
        return original(*args,**kwargs)
    monkeypatch.setattr(backups,'backup',guarded)
    assert prepare_postgres_update(bundle,public,postgres['dsn'],native.schema,tmp_path/'guarded')['installed'] is False
    with PostgresStore(postgres['dsn'],native.schema).acquire_runtime():pass


def test_real_prepare_cli_selects_native_and_sanitizes_connection_errors(native_release,native,postgres,tmp_path):
    bundle,_,public=native_release
    env={**os.environ,'AEGIS_STORAGE_BACKEND':'postgres','AEGIS_POSTGRES_DSN':postgres['dsn'],'AEGIS_POSTGRES_SCHEMA':native.schema,'AEGIS_DATA_DIR':str(tmp_path/'unused')}
    def run(output,*args,environment=env):return subprocess.run([sys.executable,'-m','aegis.cli.release','prepare','--bundle',str(bundle),'--public-key',str(public),'--output',str(output),*args],env=environment,capture_output=True,text=True,timeout=30)
    result=run(tmp_path/'cli');assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['backend']=='postgres'
    bad={**env,'AEGIS_POSTGRES_DSN':'postgresql://preflight-user:preflight-secret@127.0.0.1:1/db'}
    for args,environment in [((),bad),(('--database','not-a-SQLite-file'),env)]:
        result=run(tmp_path/'failed',*args,environment=environment)
        assert result.returncode==2 and 'Traceback' not in result.stderr
        assert 'preflight-user' not in result.stderr+result.stdout and 'preflight-secret' not in result.stderr+result.stdout
    assert not (tmp_path/'failed').exists() and not (tmp_path/'unused').exists()


def test_publication_failure_removes_only_its_created_output_and_concurrent_output_is_preserved(native_release,native,postgres,tmp_path,monkeypatch):
    from aegis import releases
    bundle,_,public=native_release;original=releases.os.link;output=tmp_path/'partial'
    def fail_receipt(source,destination):
        if Path(destination).name=='preflight.json':raise OSError('Owned receipt publication failure')
        return original(source,destination)
    with monkeypatch.context() as patch:
        patch.setattr(releases.os,'link',fail_receipt)
        with pytest.raises(OSError):prepare_postgres_update(bundle,public,postgres['dsn'],native.schema,output)
    assert not output.exists() and not list(tmp_path.glob('.pg-preflight-*'))
    original_backup=backups.backup;concurrent=tmp_path/'concurrent'
    def competing(*args,**kwargs):
        result=original_backup(*args,**kwargs)
        concurrent.mkdir();(concurrent/'keep.txt').write_text('Concurrent creator must survive')
        return result
    with monkeypatch.context() as patch:
        patch.setattr(backups,'backup',competing)
        with pytest.raises(FileExistsError):prepare_postgres_update(bundle,public,postgres['dsn'],native.schema,concurrent)
    assert (concurrent/'keep.txt').read_text()=='Concurrent creator must survive' and len(list(concurrent.iterdir()))==1
    assert not list(tmp_path.glob('.pg-preflight-*'))
