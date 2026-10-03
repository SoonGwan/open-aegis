"""Bounded in-process login admission; no addresses or credentials in metrics."""
from collections import OrderedDict, deque
from contextlib import contextmanager
from dataclasses import dataclass
import math
import threading
import time


class LoginLimited(Exception):
    def __init__(self, reason, retry_after):
        self.reason = reason
        self.retry_after = max(1, math.ceil(retry_after))


@dataclass
class LoginAttempt:
    gate: 'LoginGate'
    address: str
    serial: int

    def succeeded(self):
        # A slow successful request must not erase attempts admitted after it.
        with self.gate.lock:
            rows = self.gate.addresses.get(self.address)
            if rows is not None:
                while rows and rows[0][1] <= self.serial:
                    rows.popleft()
                if not rows:
                    self.gate.addresses.pop(self.address, None)


class LoginGate:
    def __init__(self, *, window=300, attempts=10, addresses=4096, parallel=4,
                 clock=time.monotonic):
        if window <= 0 or min(attempts, addresses, parallel) < 1:
            raise ValueError('Login limits must be positive')
        self.window, self.attempt_limit = window, attempts
        self.address_limit, self.parallel = addresses, parallel
        self.clock = clock
        self.addresses = OrderedDict()
        self.active = self.serial = 0
        self.denied = {'rate': 0, 'capacity': 0, 'busy': 0}
        self.lock = threading.Lock()

    def expire(self, timestamp):
        # Buckets are ordered by their most recent admitted attempt. Remove only
        # expired buckets; never evict a live bucket to admit a new address.
        while self.addresses:
            rows = next(iter(self.addresses.values()))
            if rows[-1][0] > timestamp - self.window:
                break
            self.addresses.popitem(last=False)

    def reject(self, reason, seconds):
        self.denied[reason] += 1
        raise LoginLimited(reason, seconds)

    @contextmanager
    def attempt(self, address):
        with self.lock:
            timestamp = self.clock()
            self.expire(timestamp)
            rows = self.addresses.get(address)
            if rows is not None:
                while rows and rows[0][0] <= timestamp - self.window:
                    rows.popleft()
                if len(rows) >= self.attempt_limit:
                    self.reject('rate', rows[0][0] + self.window - timestamp)
            elif len(self.addresses) >= self.address_limit:
                oldest = next(iter(self.addresses.values()))
                self.reject('capacity', oldest[-1][0] + self.window - timestamp)
            if self.active >= self.parallel:
                self.reject('busy', 1)
            if rows is None:
                rows = deque()
                self.addresses[address] = rows
            self.serial += 1
            rows.append((timestamp, self.serial))
            self.addresses.move_to_end(address)
            self.active += 1
            permit = LoginAttempt(self, address, self.serial)
        try:
            yield permit
        finally:
            with self.lock:
                self.active -= 1

    def metrics(self):
        with self.lock:
            self.expire(self.clock())
            return {'active': self.active, 'parallel': self.parallel,
                    'tracked_addresses': len(self.addresses), 'address_limit': self.address_limit,
                    'window_seconds': self.window, 'attempt_limit': self.attempt_limit,
                    'denied': dict(self.denied)}
