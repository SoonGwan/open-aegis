"""Deliberately weak loopback-only fixture. Never deploy it publicly."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class LabHandler(BaseHTTPRequestHandler):
    hardened = os.environ.get('AEGIS_LAB_HARDENED') == '1'
    fault = False
    requests = []

    def do_GET(self):
        type(self).requests.append(self.path)
        if self.path == '/redirect-outside':
            self.send_response(302)
            self.send_header('Location', 'http://169.254.169.254/latest/meta-data/')
            self.end_headers()
            return
        if self.fault:
            self.send_response(503)
            self.end_headers()
            return
        if self.path == '/api/account' and self.hardened and self.headers.get('Authorization') != 'Bearer lab-test-token':
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(200)
        is_api = self.path.startswith('/api/')
        self.send_header('Content-Type', 'application/json' if is_api else 'text/html; charset=utf-8')
        if self.hardened:
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; frame-ancestors 'none'")
            self.send_header('Set-Cookie', 'lab_session=fixture-only; Secure; HttpOnly; SameSite=Lax')
        else:
            self.send_header('Set-Cookie', 'lab_session=fixture-only')
            self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        body = json.dumps({'account': 'synthetic-fixture', 'secret': 'NOT-REAL-CUSTOMER-DATA'}).encode() if is_api else b'<html><title>Aegis lab</title><a href="/api/account">Fixture account</a><a href="https://outside.invalid/">Outside</a></html>'
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    port = int(os.environ.get('AEGIS_LAB_PORT', '9090'))
    print(f'Local synthetic fixture: http://127.0.0.1:{port} (hardened={LabHandler.hardened})', flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), LabHandler).serve_forever()
