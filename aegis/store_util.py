import time
import uuid


def now():
    return time.time()


def identifier():
    return uuid.uuid4().hex[:16]
