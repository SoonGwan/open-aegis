"""The documented launcher must drain active SSE connections on SIGTERM."""
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def test_documented_launcher_shuts_down_with_open_event_stream(tmp_path):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    env={**os.environ,'AEGIS_HOST':'127.0.0.1','AEGIS_PORT':str(port),'AEGIS_DATA_DIR':str(tmp_path/'live'),
         'AEGIS_ALLOWED_HOSTS':'localhost,127.0.0.1','AEGIS_SETUP_TOKEN':'','AEGIS_SECURE_COOKIE':'0',
         'AEGIS_LLM_API_KEY':'','AEGIS_LLM_MODEL':'','AEGIS_LLM_BASE_URL':'https://api.openai.com/v1'}
    root=Path(__file__).resolve().parents[1]
    process=subprocess.Popen([sys.executable,str(root/'scripts/run.py')],cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stream=None
    try:
        base=f'http://127.0.0.1:{port}'
        for _ in range(100):
            try:
                with urllib.request.urlopen(base+'/api/health',timeout=.3) as response:
                    assert json.load(response)['status']=='ok'
                break
            except OSError:time.sleep(.05)
        else:raise AssertionError('Launcher did not become healthy')
        request=urllib.request.Request(base+'/api/auth/setup',data=json.dumps({'password':'launcher-fixture-password'}).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=2) as response:
            cookie=response.headers['Set-Cookie'].split(';',1)[0]
        stream=urllib.request.urlopen(urllib.request.Request(base+'/api/events/stream',headers={'Cookie':cookie}),timeout=2)
        assert stream.readline()
        started=time.monotonic();process.send_signal(signal.SIGTERM)
        process.communicate(timeout=3)
        assert time.monotonic()-started<3 and process.returncode in (0,-signal.SIGTERM)
        stream.read()  # Consume already-buffered events, then observe a closed response.
        assert stream.read()==b''
    finally:
        if stream:stream.close()
        if process.poll() is None:process.kill();process.communicate(timeout=2)
