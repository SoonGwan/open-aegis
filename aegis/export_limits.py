"""Per-process admission and monotonic deadlines for report downloads."""
import math
import os
import threading
import time
from dataclasses import asdict, dataclass


class ExportDeadline(RuntimeError):
    # TimeoutError inherits OSError, which ASGI 2.4 streaming translates into a
    # client disconnect. Keep SQL deadline failures distinct from send failures.
    pass


@dataclass(frozen=True)
class ExportPolicy:
    parallel: int = 2
    timeout: float = 120.0

    @classmethod
    def from_env(cls):
        defaults=cls();values={}
        for field,minimum,maximum in (('parallel',1,4),('timeout',1,600)):
            name='AEGIS_EXPORT_'+field.upper()
            try:
                value=type(getattr(defaults,field))(os.environ.get(name,getattr(defaults,field)))
                if not math.isfinite(value) or not minimum<=value<=maximum: raise ValueError()
            except (TypeError,ValueError):
                raise ValueError(f'{name} must be between {minimum} and {maximum}') from None
            values[field]=value
        return cls(**values)


class ExportPool:
    def __init__(self, policy):
        self.policy=policy
        self.lock=threading.Lock()
        self.active=0
        self.counters=dict.fromkeys(('started','completed','cancelled','timed_out','failed','rejected'),0)

    def acquire(self):
        with self.lock:
            if self.active>=self.policy.parallel:
                self.counters['rejected']+=1
                return None
            self.active+=1
            self.counters['started']+=1
            return ExportPermit(self,time.monotonic()+self.policy.timeout)

    def metrics(self):
        with self.lock:
            return {'policy':asdict(self.policy),'active':self.active,**self.counters}


class ExportPermit:
    def __init__(self, pool, deadline):
        self.pool,self.deadline=pool,deadline
        self.cancelled=threading.Event()
        self.finished=False

    def remaining(self):
        return max(0,self.deadline-time.monotonic())

    def interrupt_sql(self):
        return int(self.cancelled.is_set() or self.remaining()<=0)

    def check(self):
        if self.remaining()<=0: raise ExportDeadline('보고서 내보내기 시간 제한을 초과했습니다.')
        if self.cancelled.is_set(): raise InterruptedError('보고서 다운로드가 중단되었습니다.')

    def finish(self, outcome):
        self.cancelled.set()
        with self.pool.lock:
            if self.finished:return
            self.finished=True
            self.pool.active-=1
            self.pool.counters[outcome]+=1
