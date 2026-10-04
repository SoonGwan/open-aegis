"""Manual built-app session QA with disposable users and held note acknowledgments.

Loopback only. Never opens an existing workspace or launches target checks.
"""
import argparse
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.responses import FileResponse, Response
from aegis.app import create_app
from aegis.auth import new_user
from aegis.__main__ import AegisServer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8811)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be 1..65535')
    for key in list(os.environ):
        if key.startswith('AEGIS_'):
            del os.environ[key]
    os.environ['AEGIS_WEB_DIR'] = str(ROOT/'web/dist')
    with tempfile.TemporaryDirectory(prefix='aegis-session-ui-') as workspace:
        app = create_app(workspace, allow_private=False)
        for username, role in [('admin', 'admin'), ('operator', 'operator')]:
            app.state.store.add_user(new_user(username, 'Owned '+username, role,
                                              'owned-session-ui-password-only'))

        @app.get('/session-review.js')
        def script():
            return FileResponse(ROOT/'web/tests/browser/session-review.js',
                                media_type='application/javascript')

        @app.middleware('http')
        async def fixture(request, call_next):
            response = await call_next(request)
            if request.method == 'GET' and request.url.path == '/':
                body = b''.join([part async for part in response.body_iterator])
                headers = dict(response.headers)
                headers.pop('content-length', None)
                response = Response(body.replace(b'</body>',
                    b'<script src="/session-review.js"></script></body>'),
                    headers=headers, media_type='text/html')
            return response

        print('Owned QA users: admin / operator; password: owned-session-ui-password-only', flush=True)
        AegisServer(app, host='127.0.0.1', port=args.port, access_log=False,
                    timeout_graceful_shutdown=5).run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)
