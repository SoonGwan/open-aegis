"""Bounded provider POST. Credentials never follow redirects or enter traffic records."""
import json
from urllib.error import HTTPError
from urllib.parse import urlsplit
from .network import PinnedHTTP, PinnedHTTPS, resolve
from .runtime import TaskControl, RequestGuard


def completion(base, key, payload, allow_local=False, *, control=None, timeout=8):
    parsed=urlsplit(base)
    local=allow_local and parsed.hostname in ('localhost','127.0.0.1','::1')
    if (parsed.scheme != 'https' and not (local and parsed.scheme == 'http')) or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Provider URL must use HTTPS; local lab providers are the only HTTP exception')
    if not parsed.hostname:raise ValueError('Provider hostname is required')
    control=control or TaskControl()
    port=parsed.port or (443 if parsed.scheme=='https' else 80)
    address=resolve(parsed.hostname,port,allow_private=local,control=control,timeout=min(4,timeout))[0]
    cls=PinnedHTTPS if parsed.scheme=='https' else PinnedHTTP
    connection=cls(parsed.hostname,port,address,timeout=control.timeout(timeout))
    try:
        with RequestGuard(connection,control,timeout) as guard:
            connection.request('POST',parsed.path.rstrip('/')+'/chat/completions',body=json.dumps(payload).encode(),
                               headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
            guard.sock=connection.sock
            response=connection.getresponse()
            if not 200<=response.status<300:
                raise HTTPError(base,response.status,'Provider request failed',{},None)
            body=response.read(1024*1024+1)
            if len(body)>1024*1024:
                raise ValueError('Provider response exceeds size budget')
        return json.loads(body)
    finally:connection.close()
