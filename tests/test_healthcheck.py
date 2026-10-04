import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from aegis import __version__
from aegis.healthcheck import healthy


@pytest.mark.parametrize('status,body,expected', [
    (200,json.dumps({'status':'ok','version':__version__}).encode(),True),
    (200,json.dumps({'status':'degraded','version':__version__}).encode(),False),
    (503,json.dumps({'status':'ok','version':__version__}).encode(),False),
    (200,json.dumps({'status':'ok','version':'other'}).encode(),False),
    (200,b'<html>Wrong server</html>',False),
    (200,b'[]',False),
    (200,b' '*4097,False),
    (302,b'',False),
])
def test_owned_loopback_probe_status_body_host_and_no_proxy(monkeypatch,status,body,expected):
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            requests.append((self.path,self.headers['Host']))
            self.send_response(status)
            self.send_header('Content-Length',str(len(body)))
            if status == 302:self.send_header('Location','https://must-not-fetch.invalid/')
            self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    monkeypatch.setenv('AEGIS_PORT',str(server.server_port))
    monkeypatch.setenv('AEGIS_HEALTH_HOST','service.example.invalid')
    monkeypatch.setenv('HTTP_PROXY','http://must-not-fetch.invalid:1234')
    monkeypatch.setenv('http_proxy','http://must-not-fetch.invalid:1234')
    try:
        assert healthy() is expected
        assert requests == [('/api/health','service.example.invalid')]
    finally:
        server.shutdown();server.server_close();thread.join(3)
    assert not thread.is_alive()


@pytest.mark.parametrize('port',['0','65536','invalid','-1'])
def test_invalid_port_fails_without_network(monkeypatch,port):
    monkeypatch.setenv('AEGIS_PORT',port)
    assert healthy() is False
