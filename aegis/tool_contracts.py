"""Versioned contracts for built-in reviewed checks; not an external-code loader."""
import hashlib
import json
import math
import re
from importlib.resources import files

from .checks import CHECK_IDS
from .network import in_scope, normalize_url

MAX_RESULT_BYTES = 512 * 1024
MAX_FINDINGS = 128
MAX_OBSERVATIONS = 100


class ToolContractError(ValueError):
    pass


class ToolContractMismatch(ToolContractError):
    pass


def _source_fingerprint():
    digest = hashlib.sha256()
    def visit(folder, prefix=''):
        for child in sorted(folder.iterdir(), key=lambda item: item.name):
            name = prefix + child.name
            if child.is_dir() and child.name != '__pycache__':
                visit(child, name + '/')
            elif child.is_file() and child.name.endswith('.py'):
                digest.update(name.encode() + b'\0' + hashlib.sha256(child.read_bytes()).digest())
    visit(files('aegis'))
    return digest.hexdigest()


# Captured once for this process. This is a compatibility fingerprint, not a signature
# or proof against modification by a party controlling the running Python process.
PACKAGE_SHA256 = _source_fingerprint()


def contracts_for(checks):
    if type(checks) is not list or not checks or len(checks) > len(CHECK_IDS) or any(type(check) is not str for check in checks):
        raise ToolContractError('등록된 검증 도구 목록이 필요합니다.')
    if len(set(checks)) != len(checks) or not set(checks) <= CHECK_IDS:
        raise ToolContractError('등록된 검증 도구 목록이 필요합니다.')
    return {'format': 'aegis-tools-v1', 'package_sha256': PACKAGE_SHA256, 'checks': [
        {'id': check, 'version': 1, 'method': 'GET',
         'permissions': ['base-response'] + (['scoped-get'] if check == 'api_authorization' else ['observe-links'] if check == 'endpoint_inventory' else []),
         'result_format': 'aegis-check-result-v1', 'max_result_bytes': MAX_RESULT_BYTES,
         'max_findings': MAX_FINDINGS, 'max_observations': MAX_OBSERVATIONS if check == 'endpoint_inventory' else 0}
        for check in checks]}


def require_contracts(task):
    try:
        actual = json.dumps(task.get('tool_contracts'), sort_keys=True, allow_nan=False, separators=(',', ':'))
        expected = json.dumps(contracts_for(task.get('checks')), sort_keys=True, allow_nan=False, separators=(',', ':'))
    except (TypeError, ValueError, RecursionError):
        raise ToolContractMismatch('검증 도구 계약이 없거나 변경되었습니다. 현재 도구로 새 계획을 만들고 승인하세요.') from None
    # Python equality treats True/1/1.0 alike; the persisted JSON contract does not.
    if actual != expected:
        raise ToolContractMismatch('검증 도구 계약이 없거나 변경되었습니다. 현재 도구로 새 계획을 만들고 승인하세요.')


def _json_shape(value):
    # Inspect a bounded JSON tree before serialization. Producer allocation/execution
    # is outside this result admission check; this is not a process memory sandbox.
    stack = [(value, 0)]
    nodes = size = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > 4096 or depth > 16:
            raise ToolContractError('검증 결과 구조 제한을 초과했습니다.')
        if type(item) is str:
            size += len(item.encode('utf-8'))
        elif type(item) is dict:
            if len(item) > 256 or any(type(key) is not str for key in item):
                raise ToolContractError('검증 결과 구조가 올바르지 않습니다.')
            stack.extend((part, depth + 1) for pair in item.items() for part in pair)
            size += len(item) * 4
        elif type(item) is list:
            if len(item) > 256:
                raise ToolContractError('검증 결과 구조 제한을 초과했습니다.')
            stack.extend((part, depth + 1) for part in item)
            size += len(item) * 2
        elif type(item) is float:
            if not math.isfinite(item):
                raise ToolContractError('검증 결과 숫자가 올바르지 않습니다.')
        elif type(item) is int:
            if not -(2**63) <= item < 2**63:
                raise ToolContractError('검증 결과 숫자가 올바르지 않습니다.')
        elif item is not None and type(item) is not bool:
            raise ToolContractError('검증 결과는 JSON 값이어야 합니다.')
        if size > MAX_RESULT_BYTES:
            raise ToolContractError('검증 결과 크기 제한을 초과했습니다.')
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    if len(encoded) > MAX_RESULT_BYTES:
        raise ToolContractError('검증 결과 크기 제한을 초과했습니다.')


def validate_result(check, asset, result):
    """Validate the complete result before writing any finding or observation."""
    if type(check) is not str or check not in CHECK_IDS or type(result) not in (tuple, list) or len(result) != 3:
        raise ToolContractError('검증 결과 형식이 올바르지 않습니다.')
    findings, observed, skipped = result
    if type(findings) is not list or type(observed) is not list or len(findings) > MAX_FINDINGS or len(observed) > MAX_OBSERVATIONS:
        raise ToolContractError('검증 결과 건수 제한을 초과했습니다.')
    if skipped is not None and (type(skipped) is not str or not skipped or len(skipped) > 1000 or findings or observed):
        raise ToolContractError('건너뜀 결과 형식이 올바르지 않습니다.')
    if observed and check != 'endpoint_inventory':
        raise ToolContractError('이 도구는 관찰 링크를 반환할 수 없습니다.')
    required = {'check', 'code', 'title', 'severity', 'evidence', 'remediation', 'confidence'}
    for finding in findings:
        if type(finding) is not dict or set(finding) != required or finding['check'] != check:
            raise ToolContractError('발견 결과의 도구 또는 필드가 올바르지 않습니다.')
        for field, maximum in (('code', 128), ('title', 300), ('remediation', 4000)):
            if type(finding[field]) is not str or not 1 <= len(finding[field]) <= maximum:
                raise ToolContractError('발견 결과 문자열이 올바르지 않습니다.')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', finding['code']) or finding['severity'] not in ('critical', 'high', 'medium', 'low', 'info') or finding['confidence'] not in ('configuration', 'review', 'policy-mismatch') or type(finding['evidence']) is not dict:
            raise ToolContractError('발견 결과 형식이 올바르지 않습니다.')
    for url in observed:
        if type(url) is not str or len(url) > 2048 or normalize_url(url) != url or '?' in url or '#' in url or not in_scope(url, asset['url']):
            raise ToolContractError('관찰 링크가 승인 범위를 벗어났습니다.')
    _json_shape([findings, observed, skipped])
    return findings, observed, skipped
