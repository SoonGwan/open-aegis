"""Process-wide execution limits. Monotonic deadlines never depend on wall-clock edits."""
import os
import math
import socket
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass


class TaskDeadline(TimeoutError):
    pass


class RequestDeadline(TimeoutError):
    pass


@dataclass(frozen=True)
class ExecutionPolicy:
    target_rps: float = 2.0
    target_parallel: int = 1
    request_timeout: float = 8.0
    dns_timeout: float = 4.0
    task_timeout: float = 300.0
    queue_timeout: float = 600.0
    request_budget: int = 24
    request_retries: int = 1
    retry_delay: float = 0.5
    concurrent_tasks: int = 2
    pending_limit: int = 30

    @classmethod
    def from_env(cls):
        bounds = {'target_rps':(.1,20), 'target_parallel':(1,4),
                  'request_timeout':(.1,30), 'dns_timeout':(.1,30),
                  'task_timeout':(.2,3600), 'queue_timeout':(1,3600),
                  'request_budget':(1,240), 'request_retries':(0,2),
                  'retry_delay':(.05,10), 'concurrent_tasks':(1,4), 'pending_limit':(1,100)}
        defaults=cls(); values={}
        for key,(minimum,maximum) in bounds.items():
            name='AEGIS_'+key.upper(); raw=os.environ.get(name)
            try:
                value=type(getattr(defaults,key))(raw) if raw is not None else getattr(defaults,key)
                if not math.isfinite(value) or not minimum<=value<=maximum:
                    raise ValueError()
            except (TypeError,ValueError):
                raise ValueError(f'{name} must be between {minimum} and {maximum}') from None
            values[key]=value
        return cls(**values)

    def public(self):
        return asdict(self)


class TaskControl:
    def __init__(self, stop=None, deadline=None):
        self.stop=stop or threading.Event()
        self.deadline=deadline

    def check(self):
        if self.stop.is_set():
            raise InterruptedError('작업이 중지되었습니다.')
        if self.expired():
            raise TaskDeadline('작업 실행 시간 제한을 초과했습니다.')

    def expired(self):
        return self.deadline is not None and time.monotonic()>=self.deadline

    def wait(self, seconds):
        end=time.monotonic()+max(0,seconds)
        while True:
            self.check(); remaining=end-time.monotonic()
            if remaining<=0:return
            self.stop.wait(min(.05,remaining))

    def timeout(self, seconds):
        self.check()
        return min(seconds,max(.001,self.deadline-time.monotonic())) if self.deadline is not None else seconds


class RequestGuard:
    """Interrupt response headers/body, including slow-drip peers, by shutting down the socket."""
    def __init__(self, connection, control, seconds):
        self.connection=connection;self.control=control
        self.deadline=time.monotonic()+control.timeout(seconds)
        self.done=threading.Event();self.error=None;self.sock=None
        self.thread=threading.Thread(target=self.watch,daemon=True,name='aegis-request-deadline')

    def watch(self):
        while not self.done.wait(.02):
            try:
                self.control.check()
                if time.monotonic()>=self.deadline:
                    raise RequestDeadline('HTTP 요청 시간 제한을 초과했습니다.')
            except (InterruptedError,TimeoutError) as exc:
                self.error=exc
                sock=self.sock or self.connection.sock
                if sock is not None:
                    try:sock.shutdown(socket.SHUT_RDWR)
                    except OSError:pass
                return

    def __enter__(self):
        self.thread.start();return self

    def __exit__(self, *args):
        self.done.set();self.thread.join()
        if self.error:raise self.error
        self.control.check()
        if time.monotonic()>=self.deadline:
            raise RequestDeadline('HTTP 요청 시간 제한을 초과했습니다.')


class OriginLimiter:
    """All assets and tasks share an origin's start interval and concurrent request slots."""
    def __init__(self, policy):
        self.policy=policy;self.lock=threading.Lock();self.origins={}
        self.counters={'requests':0,'throttled_requests':0,'throttle_seconds':0.0,'retries':0}

    @contextmanager
    def acquire(self, origin, control):
        started=time.monotonic(); waited=False
        while True:
            control.check()
            with self.lock:
                current=time.monotonic()
                # Only retain active origins and ones whose next start is still rate-limited.
                self.origins={key:row for key,row in self.origins.items() if row['active'] or row['next']>current}
                row=self.origins.setdefault(origin,{'active':0,'next':0})
                delay=max(0,row['next']-current)
                if row['active']<self.policy.target_parallel and delay<=0:
                    row['active']+=1;row['next']=current+1/self.policy.target_rps
                    self.counters['requests']+=1
                    if waited:
                        self.counters['throttled_requests']+=1
                        self.counters['throttle_seconds']+=current-started
                    break
            waited=True;control.wait(min(.05,delay) if delay>0 else .05)
        try:yield
        finally:
            with self.lock:row['active']-=1

    def retry(self):
        with self.lock:self.counters['retries']+=1

    def snapshot(self):
        with self.lock:
            return {**self.counters,'active_requests':sum(row['active'] for row in self.origins.values())}
