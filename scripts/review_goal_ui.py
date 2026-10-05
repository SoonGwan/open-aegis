"""Disposable built-app goal QA; synthetic local provider, no target execution."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aegis.app import create_app, TaskInput
from aegis.auth import new_user
from aegis.__main__ import AegisServer
from aegis.coverage import planned_slots
from aegis.store_util import now
from aegis.tool_contracts import contracts_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8812)
    parser.add_argument('--unconfigured', action='store_true', help='Exercise the real missing-provider configuration error')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be 1..65535')
    for key in list(os.environ):
        if key.startswith('AEGIS_'):
            del os.environ[key]
    release = threading.Event()
    calls = []
    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            prompt = json.loads(payload['messages'][1]['content'])
            calls.append(prompt['goal'])
            if '대기' in prompt['goal']:
                release.clear()
                print(json.dumps({'owned_provider_call': len(calls), 'held': True}), flush=True)
                if not release.wait(timeout=30):
                    self.send_error(503)
                    return
            plan = {'objectives': [{'id': 'g1', 'title': '합성 헤더 검토',
                    'rationale': '브라우저 상태 검수용 합성 계획입니다.',
                    'asset_ids': [prompt['assets'][0]['id']], 'checks': ['security_headers'],
                    'expected_evidence': '별도 승인 후 확인할 합성 기대 근거', 'missing_inputs': []}],
                    'worker_dependencies': {}}
            body = json.dumps({'choices': [{'message': {'content': json.dumps(plan)}}],
                               'usage': {'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20}}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass
        def log_message(self, *_):
            pass
    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    provider_thread = threading.Thread(target=provider.serve_forever, daemon=True)
    provider_thread.start()
    def commands():
        for line in sys.stdin:
            if line.strip() == 'release':
                release.set()
    threading.Thread(target=commands, daemon=True).start()
    os.environ['AEGIS_WEB_DIR'] = str(ROOT / 'web/dist')
    if not args.unconfigured:
        os.environ.update(AEGIS_LLM_MODEL='owned-goal-ui-model', AEGIS_LLM_API_KEY='owned-goal-ui-key',
                          AEGIS_LLM_BASE_URL='http://127.0.0.1:' + str(provider.server_port) + '/v1')
    with tempfile.TemporaryDirectory(prefix='aegis-goal-ui-') as workspace:
        app = create_app(workspace, allow_private=True)
        store = app.state.store
        store.add_user(new_user('admin', 'Owned goal reviewer', 'admin', 'owned-goal-password-only'))
        timestamp = now()
        asset = {'id': 'owned-goal-asset', 'name': '합성 목표 자산', 'url': 'https://owned-goal.invalid/',
                 'type': 'web', 'owner': '', 'tags': [], 'authorized': True, 'authorization_rules': [],
                 'revision': 1, 'created_at': timestamp, 'updated_at': timestamp, 'archived_at': None}
        task = {**TaskInput(name='합성 목표 키보드 검수', asset_ids=[asset['id']],
                           checks=['security_headers']).model_dump(), 'id': 'owned-goal-task',
                'status': 'pending', 'created_at': timestamp, 'approved_at': None,
                'done': 0, 'errors': 0, 'scope_snapshot': [asset], 'tool_contracts': contracts_for(['security_headers'])}
        store.put_many([('assets', asset), ('tasks', task),
                        *[('coverage', row) for row in planned_slots(task)]])
        print('Owned goal QA: admin / owned-goal-password-only', flush=True)
        print('Goal text containing 대기 holds the owned provider; type release to complete it.', flush=True)
        print(f'http://127.0.0.1:{args.port}/?page=tasks&detail=task&detail_id=owned-goal-task', flush=True)
        try:
            AegisServer(app, host='127.0.0.1', port=args.port, access_log=False,
                        timeout_graceful_shutdown=5).run()
        finally:
            release.set()
            provider.shutdown()
            provider.server_close()
            provider_thread.join(timeout=2)
            print(json.dumps({'owned_provider_calls': len(calls), 'target_traffic_records': store.count('traffic'),
                              'task_states': [{'id': row['id'], 'status': row['status'], 'approved_at': row.get('approved_at')}
                                             for row in store.page('tasks')['items']]}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)
