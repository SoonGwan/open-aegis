"""Bounded HTTP GET transport, with DNS pinning and scope checks per redirect."""
import hashlib
import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit


class ScopeError(ValueError):
    pass


def normalize_url(value):
    value = value.strip()
    p = urlsplit(value)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ScopeError('HTTP/HTTPS 주소만 허용합니다. 주소에 인증정보를 넣을 수 없습니다.')
    if p.fragment or any(c in value for c in ('\\', '\r', '\n', '\t')):
        raise ScopeError('주소에 제어 문자, 역슬래시 또는 fragment를 넣을 수 없습니다.')
    try:
        port = p.port
    except ValueError as exc:
        raise ScopeError('포트가 올바르지 않습니다.') from exc
    host = p.hostname.encode('idna').decode('ascii').lower()
    if ':' in host:
        host = '[' + host + ']'
    netloc = host + (f':{port}' if port else '')
    path = p.path or '/'
    decoded = path
    for _ in range(4):
        decoded = unquote(decoded)
    if any(part in ('.', '..') for part in decoded.split('/')) or '\\' in decoded:
        raise ScopeError('경로 이동 문자는 허용하지 않습니다.')
    return urlunsplit((p.scheme, netloc, path, p.query, ''))


def origin(url):
    p = urlsplit(url)
    return p.scheme, p.hostname, p.port or (443 if p.scheme == 'https' else 80)


def in_scope(url, base):
    url, base = normalize_url(url), normalize_url(base)
    if origin(url) != origin(base):
        return False
    root = urlsplit(base).path.rstrip('/')
    path = urlsplit(url).path
    return not root or path == root or path.startswith(root + '/')


def resolve(host, port, allow_private=False):
    try:
        addresses = list(dict.fromkeys(info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)))
    except OSError as exc:
        raise ScopeError('대상 DNS를 확인할 수 없습니다.') from exc
    if not addresses:
        raise ScopeError('DNS 응답이 없습니다.')
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if ip.is_unspecified or ip.is_multicast or ip.is_link_local or str(ip) == '100.100.100.200' or (not allow_private and not ip.is_global):
            raise ScopeError('사설·예약·메타데이터 주소는 차단됩니다. 로컬 실습은 별도 lab 설정을 사용하세요.')
    return addresses


class PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host, port, address, timeout=8):
        super().__init__(host, port, timeout=timeout)
        self.address = address

    def connect(self):
        self.sock = socket.create_connection((self.address, self.port), self.timeout)


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, port, address, timeout=8):
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def public_headers(headers):
    allowed = {'content-type', 'content-length', 'server', 'strict-transport-security',
               'content-security-policy', 'x-content-type-options', 'x-frame-options',
               'referrer-policy', 'permissions-policy', 'access-control-allow-origin',
               'access-control-allow-credentials', 'cache-control'}
    return {k.lower(): v[:2000] for k, v in headers if k.lower() in allowed}


class Transport:
    def __init__(self, base, allow_private=False, record=None, cancelled=None, delay=0.25):
        self.base = normalize_url(base)
        self.allow_private = allow_private
        self.record = record or (lambda entry: None)
        self.cancelled = cancelled or (lambda: False)
        self.delay = delay
        self.count = 0
        self.max_requests = 24

    def get(self, url=None, headers=None):
        url = normalize_url(url or self.base)
        for _ in range(4):
            if self.cancelled():
                raise InterruptedError('작업이 중지되었습니다.')
            if not in_scope(url, self.base):
                raise ScopeError('승인된 origin 또는 경로 범위를 벗어났습니다.')
            if self.count >= self.max_requests:
                raise ScopeError('작업별 HTTP 요청 예산을 초과했습니다.')
            p = urlsplit(url)
            port = p.port or (443 if p.scheme == 'https' else 80)
            address = resolve(p.hostname, port, self.allow_private)[0]
            cls = PinnedHTTPS if p.scheme == 'https' else PinnedHTTP
            connection = cls(p.hostname, port, address)
            self.count += 1
            start = time.monotonic()
            try:
                connection.request('GET', p.path + ('?' + p.query if p.query else ''),
                                   headers={'User-Agent': 'OpenAegis/0.1 security-validation', **(headers or {})})
                certificate = connection.sock.getpeercert() if p.scheme == 'https' and connection.sock else None
                response = connection.getresponse()
                raw_headers = response.getheaders()
                body = response.read(131073)
                result = {'url': url, 'status': response.status, 'headers': public_headers(raw_headers),
                          'cookies': [v for k, v in raw_headers if k.lower() == 'set-cookie'],
                          'body': body[:131072], 'truncated': len(body) > 131072, 'certificate': certificate,
                          'elapsed_ms': round((time.monotonic() - start) * 1000), 'address': address}
                # Query values and response bodies are deliberately excluded from persisted evidence.
                self.record({'url': urlunsplit((p.scheme, p.netloc, p.path, '', '')),
                             'method': 'GET', 'status': response.status, 'headers': result['headers'],
                             'elapsed_ms': result['elapsed_ms'], 'bytes': len(result['body']),
                             'body_sha256': hashlib.sha256(result['body']).hexdigest(),
                             'truncated': result['truncated'], 'address': address})
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader('Location')
                    if not location:
                        return result
                    url = normalize_url(urljoin(url, location))
                    time.sleep(self.delay)
                    continue
                time.sleep(self.delay)
                return result
            finally:
                connection.close()
        raise ScopeError('리다이렉트 횟수 제한을 초과했습니다.')
