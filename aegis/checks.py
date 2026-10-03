"""Reviewed, read-only checks. Each finding distinguishes evidence from inference."""
import os
import hashlib
import ssl
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

from .network import in_scope, normalize_url

CATALOG = [
    {'id': 'security_headers', 'name': 'HTTP 보안 헤더', 'description': 'CSP, MIME sniffing, 클릭재킹 방어 설정을 확인합니다.', 'category': 'Web', 'risk': 'read-only'},
    {'id': 'transport_security', 'name': '전송 보안', 'description': 'HTTPS 사용과 HSTS 설정, 인증서 만료를 확인합니다.', 'category': 'TLS', 'risk': 'read-only'},
    {'id': 'cookie_policy', 'name': '쿠키 설정', 'description': '쿠키의 Secure·HttpOnly·SameSite 설정을 검토합니다.', 'category': 'Session', 'risk': 'read-only'},
    {'id': 'cors_policy', 'name': 'CORS 정책', 'description': '응답에 선언된 교차 출처 허용 정책을 검토합니다.', 'category': 'API', 'risk': 'read-only'},
    {'id': 'endpoint_inventory', 'name': '엔드포인트 관찰', 'description': '현재 페이지에 링크된 범위 내 주소를 수집합니다. 추가 요청은 보내지 않습니다.', 'category': 'Discovery', 'risk': 'read-only'},
    {'id': 'api_authorization', 'name': 'API 권한 검증', 'description': '운영자가 정의한 GET 접근 규칙과 환경변수 기반 테스트 계정을 비교합니다.', 'category': 'Authorization', 'risk': 'read-only'},
]
CHECK_IDS = {c['id'] for c in CATALOG}


def issue(check, code, title, severity, evidence, remediation, confidence='configuration'):
    return dict(check=check, code=code, title=title, severity=severity, evidence=evidence,
                remediation=remediation, confidence=confidence)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in ('a', 'script', 'link'):
            for name, value in attrs:
                if name in ('href', 'src') and value and len(self.links) < 100:
                    self.links.append(value)


def run_check(check, asset, transport, response):
    headers = response['headers']
    findings, observed = [], []
    if check == 'security_headers':
        if 'content-security-policy' not in headers and 'html' in headers.get('content-type', ''):
            findings.append(issue(check, 'missing-csp', 'Content-Security-Policy 미설정', 'low',
                                  {'header': 'Content-Security-Policy', 'present': False},
                                  '애플리케이션 리소스를 조사한 후 CSP를 Report-Only로 검증하고 적용하세요. 이 결과만으로 XSS 존재를 의미하지 않습니다.'))
        if headers.get('x-content-type-options', '').lower() != 'nosniff':
            findings.append(issue(check, 'missing-nosniff', 'MIME sniffing 방어 헤더 미설정', 'low',
                                  {'header': 'X-Content-Type-Options', 'value': headers.get('x-content-type-options')},
                                  '응답에 X-Content-Type-Options: nosniff를 적용하세요.'))
        if 'html' in headers.get('content-type', '') and 'x-frame-options' not in headers and 'frame-ancestors' not in headers.get('content-security-policy', '').lower():
            findings.append(issue(check, 'missing-framing', '프레임 삽입 제한 미설정', 'low',
                                  {'x_frame_options': False, 'csp_frame_ancestors': False},
                                  '업무에 필요한 출처를 기준으로 CSP frame-ancestors를 설정하세요.'))
    elif check == 'transport_security':
        if urlsplit(response['url']).scheme != 'https':
            findings.append(issue(check, 'plain-http', '암호화되지 않은 HTTP 연결', 'medium',
                                  {'scheme': 'http', 'status': response['status']},
                                  'HTTPS를 제공하고 HTTP에서 HTTPS로 전환하세요. HTTPS로의 전환은 별도 승인 범위가 필요합니다.'))
        elif 'strict-transport-security' not in headers:
            findings.append(issue(check, 'missing-hsts', 'HSTS 헤더 미설정', 'low',
                                  {'header': 'Strict-Transport-Security', 'present': False},
                                  'HTTPS가 모든 관련 호스트에서 동작하는지 확인한 후 HSTS를 단계적으로 적용하세요.'))
        cert = response.get('certificate')
        if cert and cert.get('notAfter'):
            import time
            days = int((ssl.cert_time_to_seconds(cert['notAfter']) - time.time()) / 86400)
            if days < 30:
                findings.append(issue(check, 'certificate-expiry', 'TLS 인증서 만료 임박', 'medium',
                                      {'days_remaining': days, 'not_after': cert['notAfter']}, '인증서 자동 갱신과 실패 알림을 설정하세요.'))
    elif check == 'cookie_policy':
        for index, cookie in enumerate(response['cookies']):
            flags = [part.strip().split('=', 1)[0].lower() for part in cookie.split(';')[1:]]
            missing = [flag for flag in ('secure', 'httponly', 'samesite') if flag not in flags]
            if missing:
                cookie_id = hashlib.sha256(cookie.split('=', 1)[0].encode()).hexdigest()[:12]
                findings.append(issue(check, f'cookie-flags-{cookie_id}', '쿠키 보안 속성 검토 필요', 'low',
                                      {'cookie_index': index, 'missing_attributes': missing},
                                      '인증 쿠키인지 확인하고 필요한 Secure·HttpOnly·SameSite 속성을 적용하세요. JS 접근이 필요한 쿠키는 별도로 판단하세요.', 'review'))
    elif check == 'cors_policy':
        if headers.get('access-control-allow-origin') == '*':
            findings.append(issue(check, 'cors-wildcard', '모든 출처를 허용하는 CORS 정책', 'info',
                                  {'allow_origin': '*', 'allow_credentials': headers.get('access-control-allow-credentials')},
                                  '공개 API라면 의도된 정책일 수 있습니다. 민감한 데이터 응답은 허용 출처와 인증 정책을 검토하세요. 와일드카드만으로 유출이 확인되지는 않습니다.', 'review'))
    elif check == 'endpoint_inventory':
        if 'html' in headers.get('content-type', ''):
            parser = Links()
            parser.feed(response['body'].decode('utf-8', errors='replace'))
            for link in parser.links:
                try:
                    url = normalize_url(urljoin(response['url'], link))
                    if in_scope(url, asset['url']):
                        p = urlsplit(url)
                        url = urlunsplit((p.scheme, p.netloc, p.path, '', ''))
                        if url not in observed:
                            observed.append(url)
                except ValueError:
                    continue
    elif check == 'api_authorization':
        rules = asset.get('authorization_rules', [])
        if not rules:
            return [], [], '권한 규칙이 없어 검증하지 않았습니다.'
        for index, rule in enumerate(rules):
            request_headers = {}
            if rule.get('credential_env'):
                credential = os.environ.get(rule['credential_env'])
                if not credential:
                    raise ValueError('테스트 계정 환경변수가 설정되지 않았습니다. 값을 로그에 기록하지 않습니다.')
                request_headers['Authorization'] = credential
            result = transport.get(urljoin(asset['url'], rule['path']), request_headers)
            if result['status'] >= 500 or result['status'] == 429:
                raise ValueError('서버 오류 또는 요청 제한으로 권한 결과를 판정할 수 없습니다.')
            allowed = 200 <= result['status'] < 300
            denied = result['status'] in (401, 403)
            if not allowed and not denied:
                raise ValueError('2xx 또는 401/403 응답이 아니어서 권한 결과를 판정할 수 없습니다.')
            if allowed != rule['expected_allowed']:
                findings.append(issue(check, f'auth-rule-{index}', '정의된 API 접근 권한과 응답이 불일치',
                                      'high' if not rule['expected_allowed'] else 'medium',
                                      {'path': rule['path'], 'role': rule['role'], 'expected_allowed': rule['expected_allowed'],
                                       'actual_status': result['status'], 'body_persisted': False},
                                      '서버에서 사용자·고객사·리소스 소유권을 검증하세요. 응답이 실제 보호 데이터인지 확인하세요. HTTP 상태 기반 판정이며 데이터 내용은 저장하지 않습니다.', 'policy-mismatch'))
    return findings, observed, None
