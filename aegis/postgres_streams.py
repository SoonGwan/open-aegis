"""Interrupt owned PostgreSQL reads when an export permit expires or cancels."""
import threading
from contextlib import contextmanager


@contextmanager
def query_permit(db, permit):
    if permit is None:
        yield
        return
    permit.check()
    stopped = threading.Event()

    def interrupt():
        while not stopped.wait(.025):
            if permit.interrupt_sql():
                try:
                    db.cancel_safe(timeout=1)
                except Exception:
                    # The query's own statement timeout remains the fallback.
                    # Connection/SQL exceptions are handled by the consuming thread.
                    return

    worker = threading.Thread(target=interrupt, name='aegis-report-cancel', daemon=True)
    worker.start()
    try:
        db.execute("SELECT set_config('statement_timeout',%s,true)",
                   (str(max(1, int(permit.remaining()*1000))),))
        permit.check()
        yield
    except Exception:
        permit.check()
        raise
    finally:
        stopped.set()
        worker.join()
