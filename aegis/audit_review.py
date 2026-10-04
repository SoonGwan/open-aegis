"""On-demand, bounded local audit verification. Never repairs or appends records."""
import sqlite3
import threading
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .audit import AuditIntegrityError, verify_chain


class AuditReadError(Exception):
    pass


class AuditDeadline:
    """Deadline contract used by the native read transaction cancellation guard."""
    def __init__(self, deadline):
        self.deadline=deadline

    def remaining(self):
        return max(0,self.deadline-time.monotonic())

    def interrupt_sql(self):
        return self.remaining()<=0

    def check(self):
        if self.interrupt_sql():raise TimeoutError()


class AuditCheckpoint(BaseModel):
    model_config = ConfigDict(extra='forbid')
    format: Literal['aegis-audit-v1']
    chain_id: str = Field(pattern=r'^[0-9a-f]{32}$')
    seq: int = Field(strict=True, ge=0, le=9_223_372_036_854_775_807)
    hash: str = Field(pattern=r'^[0-9a-f]{64}$')


class AuditReviewInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    checkpoint: AuditCheckpoint | None = None


class AuditReviewBusy(Exception):
    pass


class AuditReview:
    def __init__(self, path, timeout=10):
        self.source = path
        self.path = getattr(path,'path',path)
        self.timeout = timeout
        self.slot = threading.BoundedSemaphore(1)

    def run(self, checkpoint=None):
        if not self.slot.acquire(blocking=False):
            raise AuditReviewBusy()
        start = time.monotonic()
        deadline = start + self.timeout

        permit=AuditDeadline(deadline)
        check_cancelled=permit.check

        db = None
        try:
            check_cancelled()
            if getattr(self.source,'backend',None)=='postgres':
                from . import postgres_transfer as transfer
                from .maintenance import WorkspaceBusy
                postgres_error=transfer.driver()[0].Error
                try:
                    with self.source.transaction(permit=permit) as native:
                        result=transfer.postgres_audit(native,checkpoint,check_cancelled=check_cancelled)
                except (postgres_error,WorkspaceBusy,transfer.TransferError):
                    raise AuditReadError() from None
            else:
                # Read-only URI avoids schema migration, repair and accidental DB creation.
                db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True,
                                     timeout=min(.25, self.timeout))
                db.row_factory = sqlite3.Row
                db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 10000)
                db.execute('BEGIN')
                result = verify_chain(db, checkpoint, check_cancelled=check_cancelled)
            check_cancelled()
            return {**result, 'status': 'verified', 'checkpoint_compared': checkpoint is not None,
                    'checked_at': time.time(), 'duration_seconds': time.monotonic() - start}
        except AuditIntegrityError as exc:
            return {'status': 'mismatch', 'checkpoint_compared': checkpoint is not None,
                    'checked_at': time.time(), 'detail': str(exc)}
        except (TimeoutError, sqlite3.Error, AuditReadError):
            return {'status': 'inconclusive', 'checkpoint_compared': checkpoint is not None,
                    'checked_at': time.time(),
                    'detail': '시간 제한 또는 저장소 읽기 오류로 검증을 완료하지 못했습니다. CLI에서 확인하세요.'}
        finally:
            if db is not None:
                db.close()
            self.slot.release()
