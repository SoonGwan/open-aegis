import os
import uvicorn
from .app import create_app
from .maintenance import WorkspaceBusy


class AegisServer(uvicorn.Server):
    """Drain live event streams before Uvicorn waits for active connections."""
    def __init__(self, app, **options):
        self.aegis_app = app
        super().__init__(uvicorn.Config(app, **options))

    def handle_exit(self, sig, frame):
        self.aegis_app.state.shutdown_requested.set()
        super().handle_exit(sig, frame)


if __name__ == '__main__':
    try:
        AegisServer(create_app(), host=os.environ.get('AEGIS_HOST', '127.0.0.1'),
                    port=int(os.environ.get('AEGIS_PORT', '8787')), log_level='info',
                    access_log=False, timeout_graceful_shutdown=5).run()
    except WorkspaceBusy as exc:
        raise SystemExit(str(exc))
    except KeyboardInterrupt:
        raise SystemExit(130)
