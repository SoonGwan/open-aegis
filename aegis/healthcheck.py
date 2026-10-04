"""Container probe: bounded direct loopback request; no proxy or redirects."""
import http.client
import json
import os

from . import __version__


def healthy():
    connection = None
    try:
        port = int(os.environ.get('AEGIS_PORT', '8787'))
        if not 1 <= port <= 65535:
            return False
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
        connection.request('GET', '/api/health', headers={
            'Host': os.environ.get('AEGIS_HEALTH_HOST', 'localhost'),
            'Connection': 'close',
        })
        response = connection.getresponse()
        if response.status != 200:
            return False
        raw = response.read(4097)
        if len(raw) > 4096:
            return False
        payload = json.loads(raw)
        return (type(payload) is dict and payload.get('status') == 'ok'
                and payload.get('version') == __version__)
    except (ValueError, OSError, http.client.HTTPException):
        return False
    finally:
        if connection is not None:
            connection.close()


if __name__ == '__main__':
    raise SystemExit(0 if healthy() else 1)
