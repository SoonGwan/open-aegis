"""Bounded HTTP GET transport, with DNS pinning and scope checks per redirect."""
import hashlib
import http.client
import ipaddress
import socket
import ssl
import time
from contextlib import nullcontext
from email.utils import parsedate_to_datetime
from .runtime import ExecutionPolicy, TaskControl, RequestGuard, TaskDeadline
from .dns import resolver
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


def resolve(host, port, allow_private=False, *, control=None, timeout=4):
    try:
        addresses = list(dict.fromkeys(info[4][0] for info in resolver().resolve(host, port, control or TaskControl(), timeout)))
    except (InterruptedError, TimeoutError):
        raise
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
        started = time.monotonic()
        raw = socket.create_connection((self.address, self.port), self.timeout)
        try:
            raw.settimeout(max(.001, self.timeout-(time.monotonic()-started)))
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host, do_handshake_on_connect=False)
            self.sock.do_handshake()
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
    def __init__(self, base, allow_private=False, record=None, cancelled=None, delay=0.25,
                 *, policy=None, limiter=None, control=None, execution_permit=None):
        self.base = normalize_url(base)
        self.allow_private = allow_private
        self.record = record or (lambda entry: None)
        self.cancelled = cancelled or (lambda: False)
        self.delay = delay
        self.policy = policy or ExecutionPolicy()
        self.limiter = limiter
        self.control = control or TaskControl()
        self.count = 0
        self.max_requests = self.policy.request_budget
        self.execution_permit=execution_permit or nullcontext

    def check(self):
        self.control.check()
        if self.cancelled():
            raise InterruptedError('작업이 중지되었습니다.')

    def retry_delay(self, header, attempt):
        if header:
            try:
                seconds = float(header) if header.strip().isdigit() else parsedate_to_datetime(header).timestamp() - time.time()
                if seconds > 60:return None  # Do not retry earlier than a long Retry-After.
                return max(0, seconds)
            except (TypeError,ValueError,OverflowError):pass
        return self.policy.retry_delay * 2**attempt

    def get(self, url=None, headers=None):
        url = normalize_url(url or self.base)
        for _ in range(4):
            self.check()
            if not in_scope(url, self.base):
                raise ScopeError('승인된 origin 또는 경로 범위를 벗어났습니다.')
            result = None
            for attempt in range(self.policy.request_retries+1):
                self.check()
                if self.count >= self.max_requests:
                    raise ScopeError('자산별 HTTP 요청 예산을 초과했습니다.')
                retry_wait = self.policy.retry_delay * 2**attempt
                try:
                    result = self.request(url, headers or {}, attempt)
                    if result['status'] not in (429,502,503,504):break
                    retry_wait = self.retry_delay(result.pop('retry_after',None),attempt)
                    if retry_wait is None:break
                except (TaskDeadline,InterruptedError,ScopeError,ssl.SSLCertVerificationError):raise
                except (OSError,http.client.HTTPException):
                    if attempt >= self.policy.request_retries or self.count >= self.max_requests:raise
                if attempt >= self.policy.request_retries or self.count >= self.max_requests:break
                self.control.wait(retry_wait)
                self.check()
                if self.limiter:self.limiter.retry()
            if result is None:raise ConnectionError('응답을 확인하지 못했습니다.')
            if result['status'] in (301,302,303,307,308) and result.get('location'):
                url = normalize_url(urljoin(url,result['location']))
                continue
            return result
        raise ScopeError('리다이렉트 횟수 제한을 초과했습니다.')

    def request(self, url, headers, attempt):
        with self.execution_permit():
            return self._request(url,headers,attempt)

    def _request(self, url, headers, attempt):
        p = urlsplit(url)
        port = p.port or (443 if p.scheme == 'https' else 80)
        address = resolve(p.hostname,port,self.allow_private,control=self.control,timeout=self.policy.dns_timeout)[0]
        self.check()
        permit = self.limiter.acquire(origin(url),self.control) if self.limiter else nullcontext()
        with permit:
            self.check()
            cls = PinnedHTTPS if p.scheme == 'https' else PinnedHTTP
            connection = cls(p.hostname,port,address,timeout=self.control.timeout(self.policy.request_timeout))
            self.count += 1
            start = time.monotonic()
            recorded = False
            redacted = urlunsplit((p.scheme,p.netloc,p.path,'',''))
            try:
                with RequestGuard(connection,self.control,self.policy.request_timeout) as guard:
                    connection.request('GET',p.path+('?' + p.query if p.query else ''),
                                       headers={'User-Agent':'OpenAegis/0.1 security-validation', **headers})
                    guard.sock = connection.sock
                    certificate = connection.sock.getpeercert() if p.scheme == 'https' and connection.sock else None
                    response = connection.getresponse()
                    raw_headers = response.getheaders()
                    body = response.read(131073)
                    result = {'url':url,'status':response.status,'headers':public_headers(raw_headers),
                              'cookies':[v for k,v in raw_headers if k.lower()=='set-cookie'],
                              'body':body[:131072],'truncated':len(body)>131072,'certificate':certificate,
                              'elapsed_ms':round((time.monotonic()-start)*1000),'address':address,
                              'location':response.getheader('Location'),'retry_after':response.getheader('Retry-After')}
                self.check()
                self.record({'url':redacted,'method':'GET','status':result['status'],'headers':result['headers'],
                             'elapsed_ms':result['elapsed_ms'],'bytes':len(result['body']),
                             'body_sha256':hashlib.sha256(result['body']).hexdigest(),
                             'truncated':result['truncated'],'address':address,'attempt':attempt+1})
                recorded = True
                if not self.limiter:self.control.wait(self.delay)
                return result
            except Exception as exc:
                if not recorded:
                    self.record({'url':redacted,'method':'GET','status':0,'headers':{},
                                 'elapsed_ms':round((time.monotonic()-start)*1000),'bytes':0,
                                 'address':address,'attempt':attempt+1,'error_type':type(exc).__name__})
                raise
            finally:connection.close()
