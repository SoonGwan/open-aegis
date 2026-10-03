import pytest
from aegis.llm import completion


def test_provider_credentials_never_follow_redirect():
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.error import HTTPError
    calls=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            calls.append(self.path)
            self.send_response(302)
            self.send_header('Location','/capture')
            self.end_headers()
        def do_GET(self):
            calls.append(self.path)
            self.send_response(200)
            self.end_headers()
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        with pytest.raises(HTTPError):
            completion(f'http://127.0.0.1:{server.server_port}/v1','fixture-key',{},allow_local=True)
        assert calls == ['/v1/chat/completions']
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_provider_plaintext_rejected_before_network():
    with pytest.raises(ValueError,match='HTTPS'):
        completion('http://provider.invalid/v1','fixture-key',{})


def test_provider_response_size_is_bounded():
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(200)
            self.send_header('Content-Length',str(1024*1024+1))
            self.end_headers()
            self.wfile.write(b'x'*(1024*1024+1))
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with pytest.raises(ValueError,match='size budget'):
            completion(f'http://127.0.0.1:{server.server_port}/v1','fixture-key',{},allow_local=True)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
