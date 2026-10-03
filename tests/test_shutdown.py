"""Exercise actual server shutdown while a live SSE connection is open."""
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path


def test_server_drains_live_stream_on_sigterm(tmp_path):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = {**os.environ, 'AEGIS_PORT': str(port), 'AEGIS_DATA_DIR': str(tmp_path)}
    root = Path(__file__).resolve().parents[1]
    process = subprocess.Popen([sys.executable, '-m', 'aegis'], cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    stream = None
    try:
        base = f'http://127.0.0.1:{port}'
        for _ in range(100):
            try:
                with urllib.request.urlopen(base + '/api/health', timeout=1) as response:
                    assert response.status == 200
                break
            except OSError:
                assert process.poll() is None
                time.sleep(.05)
        else:
            raise AssertionError('Server did not start')
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
        request = urllib.request.Request(base + '/api/auth/setup', json.dumps({'password': 'shutdown-fixture-password'}).encode(), headers={'Content-Type': 'application/json'})
        with opener.open(request, timeout=3) as response:
            assert response.status == 200
        stream = opener.open(base + '/api/events/stream', timeout=3)
        assert stream.readline().startswith((b': heartbeat', b'id: '))
        process.send_signal(signal.SIGTERM)
        output, _ = process.communicate(timeout=8)
        # Uvicorn re-raises the captured signal after graceful cleanup on Unix.
        assert process.returncode in (0, -signal.SIGTERM), output
        assert 'Application shutdown complete' in output
        assert 'Cancel ' not in output
        assert 'Exception in ASGI application' not in output
    finally:
        if stream:
            stream.close()
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=3)
