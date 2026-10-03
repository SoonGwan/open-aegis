"""Bounded daemon DNS workers: a stalled system resolver cannot grow threads or block shutdown."""
import queue
import socket
import threading
import time
from .runtime import RequestDeadline


class Resolver:
    def __init__(self, workers=4, queued=4):
        self.jobs=queue.Queue(maxsize=queued);self.workers=workers;self.queue_limit=queued
        self.lock=threading.Lock();self.active=0
        for index in range(workers):
            threading.Thread(target=self.run,daemon=True,name=f'aegis-dns-{index}').start()

    def run(self):
        while True:
            host,port,result,event,abandoned=self.jobs.get()
            try:
                if abandoned.is_set():continue
                with self.lock:self.active+=1
                try:result['value']=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
                except Exception as exc:result['error']=exc
                finally:
                    with self.lock:self.active-=1
            finally:event.set();self.jobs.task_done()

    def resolve(self,host,port,control,seconds):
        end=time.monotonic()+control.timeout(seconds)
        result={};event=threading.Event();abandoned=threading.Event()
        try:
            while True:
                control.check()
                if time.monotonic()>=end:raise RequestDeadline('DNS 확인 시간 제한을 초과했습니다.')
                try:self.jobs.put_nowait((host,port,result,event,abandoned));break
                except queue.Full:control.wait(.02)
            while not event.wait(.02):
                control.check()
                if time.monotonic()>=end:raise RequestDeadline('DNS 확인 시간 제한을 초과했습니다.')
            control.check()
            if time.monotonic()>=end:raise RequestDeadline('DNS 확인 시간 제한을 초과했습니다.')
            if 'error' in result:raise result['error']
            return result['value']
        finally:abandoned.set()

    def snapshot(self):
        with self.lock:return {'active':self.active,'queued':self.jobs.qsize(),'workers':self.workers,'queue_limit':self.queue_limit}


_lock=threading.Lock()
_resolver=None

def resolver():
    global _resolver
    with _lock:
        if _resolver is None:_resolver=Resolver()
        return _resolver
