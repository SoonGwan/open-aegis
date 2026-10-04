"""Append-only checkpoint capture for an operator-provided independent directory."""
import fcntl
import json
import os
import re
import secrets
import stat
from pathlib import Path

from .audit import AuditIntegrityError, FORMAT

_NAME = re.compile(r'checkpoint-([0-9a-f]{32})-([0-9]{20})-([0-9a-f]{64})\.json\Z')
MAX_CHECKPOINTS = 10000


class CheckpointArchiveError(ValueError):
    pass


def filename(checkpoint):
    return f"checkpoint-{checkpoint['chain_id']}-{checkpoint['seq']:020d}-{checkpoint['hash']}.json"


def _previous(directory):
    latest = None
    chain = None
    sequences = set()
    with os.scandir(directory) as entries:
        for entry in entries:
            if not entry.name.startswith('checkpoint-'):
                continue
            match = _NAME.fullmatch(entry.name)
            if not match or not entry.is_file(follow_symlinks=False):
                raise CheckpointArchiveError('보관된 체크포인트 파일 형식이 올바르지 않습니다.')
            if len(sequences) >= MAX_CHECKPOINTS:
                raise CheckpointArchiveError('체크포인트 보관 한도에 도달했습니다. 독립 보존 정책을 확인하세요.')
            fd = os.open(entry.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            with os.fdopen(fd, 'rb') as source:
                if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                    raise CheckpointArchiveError('체크포인트는 일반 파일이어야 합니다.')
                raw = source.read(4097)
            if len(raw) > 4096:
                raise CheckpointArchiveError('보관된 체크포인트 파일이 너무 큽니다.')
            try:
                checkpoint = json.loads(raw)
                valid = (type(checkpoint) is dict and set(checkpoint) == {'format','chain_id','seq','hash'}
                         and checkpoint['format'] == FORMAT and type(checkpoint['seq']) is int
                         and 0 <= checkpoint['seq'] <= 2**63-1
                         and checkpoint['chain_id'] == match[1] and checkpoint['hash'] == match[3]
                         and filename(checkpoint) == entry.name)
            except (ValueError, TypeError, KeyError):
                valid = False
            if not valid:
                raise CheckpointArchiveError('보관된 체크포인트 내용과 파일명이 일치하지 않습니다.')
            if (chain is not None and chain != checkpoint['chain_id']) or checkpoint['seq'] in sequences:
                raise CheckpointArchiveError('서로 다른 로그 또는 같은 순번의 체크포인트가 있습니다.')
            chain = checkpoint['chain_id']
            sequences.add(checkpoint['seq'])
            if latest is None or checkpoint['seq'] > latest['seq']:
                latest = checkpoint
    return latest, len(sequences)


def capture_checkpoint(verify, destination):
    """verify(previous) must verify a single read snapshot and return an audit result.

    Holds an archive lock through verification/publication; never prunes or modifies
    checkpoints. The destination's independent trust is the operator's responsibility.
    """
    path = Path(destination)
    path.mkdir(mode=0o700, parents=False, exist_ok=True)
    directory = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    lock = None
    staged = None
    try:
        lock = os.open('.checkpoint.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        if not stat.S_ISREG(os.fstat(lock).st_mode):
            raise CheckpointArchiveError('보관 잠금은 일반 파일이어야 합니다.')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise CheckpointArchiveError('다른 체크포인트 보관 작업이 실행 중입니다.') from exc
        previous, count = _previous(directory)
        result = verify(previous)
        checkpoint = result['checkpoint']
        if result.get('valid') is not True:
            raise AuditIntegrityError('검증되지 않은 감사 체크포인트는 보관하지 않습니다.')
        name = filename(checkpoint)
        created = previous != checkpoint
        if created:
            if count >= MAX_CHECKPOINTS:
                raise CheckpointArchiveError('체크포인트 보관 한도에 도달했습니다. 독립 보존 정책을 확인하세요.')
            payload = (json.dumps(checkpoint, ensure_ascii=False, separators=(',', ':'))+'\n').encode()
            candidate = '.checkpoint-stage-'+secrets.token_hex(16)
            fd = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            staged = candidate
            with os.fdopen(fd, 'wb') as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            os.link(staged, name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
            os.fsync(directory)
        return {**result, 'created': created, 'archive_file': str(path/name)}
    finally:
        try:
            if staged is not None:
                os.unlink(staged, dir_fd=directory)
        finally:
            if lock is not None:
                os.close(lock)
            os.close(directory)
