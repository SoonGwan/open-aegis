"""Manual responsive QA server. Loopback only; intentionally permits fixture embedding."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aegis.app import create_app
from fastapi.responses import FileResponse, Response
import uvicorn


def review_app(data_dir, *, lab=False, finding_id=None, task_id=None):
    app = create_app(data_dir, allow_private=lab)
    fixtures = ROOT / 'web/tests/browser'
    config = json.dumps({'finding': finding_id, 'task': task_id}).replace('<', '\\u003c')

    @app.get('/responsive-review')
    def review():
        body = (fixtures / 'responsive-review.html').read_text().replace('{{REVIEW_CONFIG}}', config)
        return Response(body, media_type='text/html')

    @app.get('/responsive-review.js')
    def review_js():
        return FileResponse(fixtures / 'responsive-review.js', media_type='application/javascript')

    @app.get('/responsive-metrics.js')
    def metrics_js():
        return FileResponse(fixtures / 'responsive-metrics.js', media_type='application/javascript')

    @app.middleware('http')
    async def frame_headers(request, call_next):
        response = await call_next(request)
        if request.url.path == '/' and request.method == 'GET':
            body = b''.join([part async for part in response.body_iterator])
            headers = dict(response.headers)
            headers.pop('content-length', None)
            response = Response(body.replace(b'</body>', b'<script src="/responsive-metrics.js"></script></body>'),
                                media_type='text/html', headers=headers)
        # Applies exclusively to this manually launched loopback QA instance.
        response.headers['Content-Security-Policy'] = response.headers.get('Content-Security-Policy', '').replace(
            "frame-ancestors 'none'", "frame-ancestors 'self'")
        if 'X-Frame-Options' in response.headers:
            del response.headers['X-Frame-Options']
        return response

    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True, help='Use an isolated QA workspace, not production data.')
    parser.add_argument('--port', type=int, default=8811)
    parser.add_argument('--lab', action='store_true', help='Allow owned loopback lab assets in this QA instance.')
    parser.add_argument('--finding-id')
    parser.add_argument('--task-id')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be between 1 and 65535')
    for value in (args.finding_id, args.task_id):
        if value is not None and not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value):
            parser.error('detail IDs must contain 1–80 ASCII letters, digits, underscores or hyphens')
    uvicorn.run(review_app(args.data_dir, lab=args.lab, finding_id=args.finding_id, task_id=args.task_id),
                host='127.0.0.1', port=args.port, access_log=False)
