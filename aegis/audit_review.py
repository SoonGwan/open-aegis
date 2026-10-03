"""On-demand, bounded local audit verification. Never repairs or appends records."""
import sqlite3
import threading
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .audit import AuditIntegrityError, verify_chain


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
        self.path = path
        self.timeout = timeout
        self.slot = threading.BoundedSemaphore(1)

    def run(self, checkpoint=None):
        if not self.slot.acquire(blocking=False):
            raise AuditReviewBusy()
        start = time.monotonic()
        deadline = start + self.timeout

        def check_cancelled():
            if time.monotonic() >= deadline:
                raise TimeoutError()

        db = None
        try:
            # Read-only URI avoids schema migration, repair and accidental DB creation.
            db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True,
                                 timeout=min(.25, self.timeout))
            db.row_factory = sqlite3.Row
            db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 10000)
            db.execute('BEGIN')
            result = verify_chain(db, checkpoint, check_cancelled=check_cancelled)
            return {**result, 'status': 'verified', 'checkpoint_compared': checkpoint is not None,
                    'checked_at': time.time(), 'duration_seconds': time.monotonic() - start}
        except AuditIntegrityError as exc:
            return {'status': 'mismatch', 'checkpoint_compared': checkpoint is not None,
                    'checked_at': time.time(), 'detail': str(exc)}
        except (TimeoutError, sqlite3.Error):
            return {'status': 'inconclusive', 'checkpoint_compared': checkpoint is not None,
                    'checked_at': time.time(),
                    'detail': '시간 제한 또는 저장소 읽기 오류로 검증을 완료하지 못했습니다. CLI에서 확인하세요.'}
        finally:
            if db is not None:
                db.close()
            self.slot.release()
