import json
import shutil
from zipfile import ZipFile
import pytest
from aegis.releases import (create_release,verify_release,prepare_update,ReleaseError,
                            openssl,canonical)
from aegis.maintenance import WorkspaceLease,WorkspaceBusy
from aegis.store import Store
from aegis.backups import restore_database


@pytest.fixture
def release(tmp_path):
    if not shutil.which('openssl'):pytest.skip('OpenSSL is required for release signatures')
    key=tmp_path/'signing.pem';public=tmp_path/'trusted.pem'
    openssl('genpkey','-algorithm','ED25519','-out',key);key.chmod(0o600)
    openssl('pkey','-in',key,'-pubout','-out',public)
    wheel=tmp_path/'open_aegis-0.1.0-py3-none-any.whl'
    # Metadata-only fixture, not an installable runtime wheel.
    with ZipFile(wheel,'w') as z:
        z.writestr('open_aegis-0.1.0.dist-info/METADATA',
                   'Name: open-aegis\nVersion: 0.1.0\nRequires-Python: >=3.11\n')
    web=tmp_path/'web';web.mkdir();(web/'index.html').write_text('<h1>owned fixture</h1>')
    lock=tmp_path/'requirements.lock';lock.write_text('owned==1\n')
    bundle=tmp_path/'bundle'
    create_release(wheel,web,lock,bundle,key,'a'*40)
    return bundle,key,public


def resign(bundle,key,manifest):
    (bundle/'release.json').write_bytes(canonical(manifest))
    openssl('pkeyutl','-sign','-rawin','-inkey',key,'-in',bundle/'release.json',
            '-out',bundle/'release.sig')


def test_signed_bundle_and_wrong_key(release,tmp_path):
    bundle,_,public=release
    manifest=verify_release(bundle,public)
    assert manifest['version']=='0.1.0' and len(manifest['files'])==3
    assert 'private' not in json.dumps(manifest)
    wrong=tmp_path/'wrong.pem';wrong_public=tmp_path/'wrong-public.pem'
    openssl('genpkey','-algorithm','ED25519','-out',wrong)
    openssl('pkey','-in',wrong,'-pubout','-out',wrong_public)
    with pytest.raises(ReleaseError):verify_release(bundle,wrong_public)


@pytest.mark.parametrize('mutation',['payload','manifest','signature','extra','missing','symlink'])
def test_unsigned_changes_are_refused(release,mutation,tmp_path):
    bundle,_,public=release
    if mutation=='payload':(bundle/'web/index.html').write_text('modified')
    elif mutation=='manifest':(bundle/'release.json').write_text('{}')
    elif mutation=='signature':(bundle/'release.sig').write_bytes(b'x'*64)
    elif mutation=='extra':(bundle/'unexpected.txt').write_text('extra')
    elif mutation=='missing':(bundle/'requirements.lock').unlink()
    else:
        (bundle/'web/index.html').unlink()
        (bundle/'web/index.html').symlink_to(tmp_path/'outside')
    with pytest.raises(ReleaseError):verify_release(bundle,public)


@pytest.mark.parametrize('mutation',['path','format','schema','revision','size','wheel'])
def test_signed_but_malformed_contract_is_refused(release,mutation):
    bundle,key,public=release
    manifest=json.loads((bundle/'release.json').read_bytes())
    if mutation=='path':manifest['files']['../outside']={'sha256':'a'*64,'size':1}
    elif mutation=='format':manifest['format']=True
    elif mutation=='schema':manifest['sqlite_read']=[3,1]
    elif mutation=='revision':manifest['revision']=3
    elif mutation=='size':manifest['files']['requirements.lock']['size']=True
    else:manifest['wheel']=[]
    resign(bundle,key,manifest)
    with pytest.raises(ReleaseError):verify_release(bundle,public)


def test_preflight_stopped_workspace_backup_and_data_rollback(release,tmp_path):
    bundle,_,public=release
    store=Store(tmp_path/'workspace/aegis.db')
    store.put('notes',{'id':'before','title':'preserved'})
    output=tmp_path/'preflight'
    with WorkspaceLease(store.path.parent):
        with pytest.raises(WorkspaceBusy):prepare_update(bundle,public,store.path,output)
    assert not output.exists()
    receipt=prepare_update(bundle,public,store.path,output)
    assert receipt['installed'] is False and receipt['backup_metadata']['records']['notes']==1
    assert (output/'before-update.db').stat().st_mode&0o777==0o600
    assert (output/'preflight.json').stat().st_mode&0o777==0o600
    store.put('notes',{'id':'after','title':'simulate failed upgrade'})
    restored=restore_database(output/'before-update.db',store.path)
    assert restored['sessions_revoked']
    assert Store(store.path).get('notes','before')['title']=='preserved'
    assert Store(store.path).get('notes','after') is None
    with pytest.raises(ReleaseError):prepare_update(bundle,public,store.path,output)


def test_preflight_incompatible_or_running_tasks_do_not_create_backup(release,tmp_path):
    bundle,key,public=release
    store=Store(tmp_path/'workspace/aegis.db')
    manifest=json.loads((bundle/'release.json').read_bytes())
    manifest.update(sqlite_read=[0,1],sqlite_write=1);resign(bundle,key,manifest)
    with pytest.raises(ReleaseError,match='스키마'):
        prepare_update(bundle,public,store.path,tmp_path/'out')
    assert not (tmp_path/'out').exists()
    manifest.update(sqlite_read=[0,2],sqlite_write=2);resign(bundle,key,manifest)
    store.put('tasks',{'id':'running','status':'running'})
    with pytest.raises(ReleaseError,match='미완료'):
        prepare_update(bundle,public,store.path,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_signed_read_compatible_but_lower_write_schema_is_refused(release,tmp_path):
    bundle,key,public=release;store=Store(tmp_path/'workspace/aegis.db')
    manifest=json.loads((bundle/'release.json').read_text())
    manifest.update(sqlite_read=[0,2],sqlite_write=1);resign(bundle,key,manifest)
    with pytest.raises(ReleaseError,match='스키마'):
        prepare_update(bundle,public,store.path,tmp_path/'downgrade')
    assert not (tmp_path/'downgrade').exists()
