"""Offline release signatures and update preflight; never installs or runs bundle code."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
from email.parser import BytesParser
from zipfile import ZipFile
from . import __version__
from .migrations import SCHEMA_VERSION
from .maintenance import WorkspaceLease
from .backups import backup_database, readonly, validate_backup
from contextlib import closing


class ReleaseError(ValueError):
    pass


def openssl(*args):
    try:
        result=subprocess.run(['openssl',*map(str,args)],stdin=subprocess.DEVNULL,
                              capture_output=True,timeout=15)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise ReleaseError('OpenSSL 서명 도구를 실행하지 못했습니다.') from exc
    if result.returncode:
        raise ReleaseError('서명 또는 키 검증을 통과하지 못했습니다.')
    return result.stdout


def key_identity(key, *, private=False):
    key=Path(key).resolve(strict=True)
    der=openssl('pkey',*([] if private else ['-pubin']),'-in',key,'-pubout','-outform','DER')
    # Ed25519 SubjectPublicKeyInfo: fixed algorithm OID and 32-byte public key.
    if len(der)!=44 or der[:12]!=bytes.fromhex('302a300506032b6570032100'):
        raise ReleaseError('Ed25519 키만 지원합니다.')
    return hashlib.sha256(der).hexdigest()


def digest(path):
    flags=os.O_RDONLY | getattr(os,'O_NOFOLLOW',0) | getattr(os,'O_NONBLOCK',0)
    with os.fdopen(os.open(path,flags),'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size>2*1024**3:
            raise ReleaseError('일반 파일과 2 GiB 이하 파일만 지원합니다.')
        checksum=hashlib.sha256(); size=0
        while chunk:=stream.read(1024*1024):
            size+=len(chunk)
            if size>2*1024**3: raise ReleaseError('파일 크기 제한을 초과했습니다.')
            checksum.update(chunk)
        return {'sha256':checksum.hexdigest(),'size':size}


def wheel_metadata(wheel):
    with ZipFile(wheel) as archive:
        entries=[info for info in archive.infolist() if info.filename.endswith('.dist-info/METADATA')]
        if len(entries)!=1 or entries[0].file_size>1024*1024:
            raise ReleaseError('wheel 메타데이터가 올바르지 않습니다.')
        metadata=BytesParser().parsebytes(archive.read(entries[0]))
    if metadata['Name']!='open-aegis' or metadata['Requires-Python']!='>=3.11':
        raise ReleaseError('지원하지 않는 패키지 또는 Python 계약입니다.')
    return metadata['Version']


def canonical(data):
    return (json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()


def create_release(wheel, web, lock, output, private_key, revision):
    wheel,web,lock=Path(wheel),Path(web),Path(lock)
    if not re.fullmatch(r'[a-f0-9]{40}',revision): raise ReleaseError('전체 Git revision이 필요합니다.')
    if wheel_metadata(wheel)!=__version__: raise ReleaseError('wheel 버전과 현재 코드 버전이 다릅니다.')
    if not (web/'index.html').is_file(): raise ReleaseError('빌드된 UI가 없습니다.')
    if not re.fullmatch(r'open_aegis-[A-Za-z0-9_.+-]+\.whl',wheel.name):
        raise ReleaseError('wheel 파일 이름이 올바르지 않습니다.')
    signer=key_identity(private_key,private=True)
    output=Path(output).absolute()
    if output.resolve().is_relative_to(web.resolve()):
        raise ReleaseError('릴리스 출력은 UI 입력 디렉터리 밖에 있어야 합니다.')
    if output.exists(): raise ReleaseError('릴리스 출력 경로가 이미 있습니다.')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.release-',dir=output.parent) as temporary:
        root=Path(temporary)
        (root/'runtime').mkdir()
        shutil.copyfile(wheel,root/'runtime'/wheel.name)
        shutil.copyfile(lock,root/'requirements.lock')
        (root/'web').mkdir()
        for source in web.rglob('*'):
            if source.is_symlink(): raise ReleaseError('UI 심볼릭 링크를 포함할 수 없습니다.')
            if source.is_file():
                target=root/'web'/source.relative_to(web)
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source,target)
        files={str(path.relative_to(root).as_posix()):digest(path)
               for path in sorted(root.rglob('*')) if path.is_file()}
        if len(files)>10000: raise ReleaseError('릴리스 파일 수 제한을 초과했습니다.')
        manifest={'format':1,'package':'open-aegis','version':__version__,'revision':revision,
                  'python_min':[3,11],'sqlite_read':[0,SCHEMA_VERSION],'sqlite_write':SCHEMA_VERSION,
                  'wheel':'runtime/'+wheel.name,'signer_sha256':signer,'files':files}
        encoded=canonical(manifest)
        if len(encoded)>262144: raise ReleaseError('manifest 크기 제한을 초과했습니다.')
        (root/'release.json').write_bytes(encoded)
        openssl('pkeyutl','-sign','-rawin','-inkey',Path(private_key).resolve(strict=True),
                '-in',root/'release.json','-out',root/'release.sig')
        # Output must be new; never replace an existing release directory.
        output.mkdir(mode=0o700)
        try:
            for path in root.iterdir(): shutil.move(str(path),str(output/path.name))
        except BaseException:
            shutil.rmtree(output)
            raise
    return manifest


def strict_object(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ReleaseError('중복 manifest 키입니다.')
        result[key]=value
    return result


def verify_release(bundle, public_key):
    root=Path(bundle)
    if root.is_symlink(): raise ReleaseError('릴리스 경로가 심볼릭 링크입니다.')
    root=root.resolve(strict=True)
    for path in root.rglob('*'):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ReleaseError('릴리스에 특수 파일 또는 심볼릭 링크가 있습니다.')
    manifest_path=root/'release.json'; signature=root/'release.sig'
    if not manifest_path.is_file() or manifest_path.stat().st_size>262144:
        raise ReleaseError('manifest가 없거나 크기 제한을 초과했습니다.')
    if not signature.is_file() or signature.stat().st_size!=64:
        raise ReleaseError('Ed25519 서명이 없거나 형식이 다릅니다.')
    signer=key_identity(public_key)
    openssl('pkeyutl','-verify','-rawin','-pubin','-inkey',Path(public_key).resolve(strict=True),
            '-in',manifest_path,'-sigfile',signature)
    raw=manifest_path.read_bytes()
    manifest=json.loads(raw,object_pairs_hook=strict_object,
                        parse_constant=lambda _: (_ for _ in ()).throw(ReleaseError('비정상 숫자입니다.')))
    fields={'format','package','version','revision','python_min','sqlite_read','sqlite_write',
            'wheel','signer_sha256','files'}
    if (type(manifest) is not dict or set(manifest)!=fields or type(manifest['format']) is not int or manifest['format']!=1 or
            manifest['package']!='open-aegis' or manifest['signer_sha256']!=signer or
            raw!=canonical(manifest) or type(manifest['revision']) is not str or
            not re.fullmatch(r'[a-f0-9]{40}',manifest['revision']) or
            type(manifest['version']) is not str or type(manifest['wheel']) is not str or
            manifest['python_min']!=[3,11] or type(manifest['sqlite_read']) is not list or
            len(manifest['sqlite_read'])!=2 or
            any(type(n) is not int or n<0 for n in [*manifest['sqlite_read'],manifest['sqlite_write']]) or
            not manifest['sqlite_read'][0]<=manifest['sqlite_write']<=manifest['sqlite_read'][1]):
        raise ReleaseError('릴리스 manifest 계약이 올바르지 않습니다.')
    files=manifest['files']
    if type(files) is not dict or not 1<=len(files)<=10000:
        raise ReleaseError('릴리스 파일 목록이 올바르지 않습니다.')
    for name,expected in files.items():
        parts=PurePosixPath(name)
        if (parts.is_absolute() or '..' in parts.parts or str(parts)!=name or '\\' in name or
                name in ('release.json','release.sig') or
                type(expected) is not dict or set(expected)!={'sha256','size'} or
                type(expected['size']) is not int or not 0<=expected['size']<=2*1024**3 or
                type(expected['sha256']) is not str or not re.fullmatch(r'[a-f0-9]{64}',expected['sha256'])):
            raise ReleaseError('릴리스 파일 경로 또는 해시 계약이 다릅니다.')
        path=root/name
        if not path.is_file() or digest(path)!=expected:
            raise ReleaseError('릴리스 파일이 없거나 변경되었습니다: '+name)
    actual={str(p.relative_to(root).as_posix()) for p in root.rglob('*') if p.is_file()}
    if actual!=set(files)|{'release.json','release.sig'}:
        raise ReleaseError('서명에 포함되지 않은 추가 파일이 있습니다.')
    if ('web/index.html' not in files or 'requirements.lock' not in files or
            manifest['wheel'] not in files or not manifest['wheel'].startswith('runtime/') or
            wheel_metadata(root/manifest['wheel'])!=manifest['version']):
        raise ReleaseError('릴리스의 runtime/UI 계약이 다릅니다.')
    return manifest


def prepare_update(bundle, public_key, database, output):
    manifest=verify_release(bundle,public_key)
    database=Path(database).resolve(strict=True)
    output=Path(output).absolute()
    if output.exists(): raise ReleaseError('사전 점검 출력 경로가 이미 있습니다.')
    with WorkspaceLease(database.parent):
        metadata=validate_backup(database)
        if not manifest['sqlite_read'][0]<=metadata['schema_version']<=manifest['sqlite_read'][1]:
            raise ReleaseError('현재 DB 스키마를 이 릴리스가 읽을 수 없습니다.')
        with closing(readonly(database)) as db:
            unfinished=db.execute("SELECT count(*) FROM records WHERE kind='tasks' AND "
                                  "json_extract(data,'$.status') IN ('queued','running','stopping')").fetchone()[0]
        if unfinished: raise ReleaseError('미완료 실행 작업이 있습니다. 먼저 중지·복구 상태를 확인하세요.')
        output.mkdir(parents=True,mode=0o700)
        try:
            backup=output/'before-update.db'
            backup_metadata=backup_database(database,backup)
            receipt={'format':1,'release':manifest['version'],'revision':manifest['revision'],
                     'signer_sha256':manifest['signer_sha256'],
                     'manifest':digest(Path(bundle)/'release.json'),'database':str(database),
                     'backup':digest(backup),'backup_metadata':backup_metadata,
                     'sqlite_write':manifest['sqlite_write'],'installed':False}
            target=output/'preflight.json'
            target.write_bytes(canonical(receipt));target.chmod(0o600)
        except BaseException:
            shutil.rmtree(output)
            raise
    return receipt
