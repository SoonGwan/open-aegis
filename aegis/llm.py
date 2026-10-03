"""Bounded provider request; credential-bearing requests never follow redirects."""
import json
import urllib.request
from urllib.parse import urlsplit


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def completion(base, key, payload, allow_local=False):
    parsed=urlsplit(base)
    local=allow_local and parsed.hostname in ('localhost','127.0.0.1','::1')
    if (parsed.scheme != 'https' and not (local and parsed.scheme == 'http')) or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Provider URL must use HTTPS; local lab providers are the only HTTP exception')
    request=urllib.request.Request(base.rstrip('/')+'/chat/completions',data=json.dumps(payload).encode(),
                                   headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    opener=urllib.request.build_opener(NoRedirect())
    with opener.open(request,timeout=20) as response:
        body=response.read(1024*1024+1)
        if len(body)>1024*1024:
            raise ValueError('Provider response exceeds size budget')
        return json.loads(body)
