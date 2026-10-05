"""Receive a complete scoped result before admitting any finding or observation."""
import hashlib
import ipaddress
import re

from .mcp_scope import FORMAT, RequestLimits, verify_claim
from .network import in_scope, normalize_url
from .remote_mcp import _decode, _encode
from .tool_contracts import PACKAGE_SHA256, validate_result


class ExecutionResultError(ValueError):
    pass


def validate_execution_response(token, key, server_id, response, *, ceiling=None, allow_private=False):
    """Bind returned data to authority; do not infer remote runtime attestation."""
    try:
        response = _decode(_encode(response))
        claim = verify_claim(token, key, server_id)
        if response.get('isError') is not False or not isinstance(response.get('structuredContent'), dict):
            raise ValueError()
        output = response['structuredContent']
        identity = {'format': FORMAT, 'grant_sha256': hashlib.sha256(token.encode()).hexdigest(),
                    'task_id': claim.task_id, 'asset_id': claim.asset.id, 'asset_revision': claim.asset.revision,
                    'check_id': claim.check_id, 'scope_url': claim.asset.url, 'package_sha256': PACKAGE_SHA256,
                    'allow_private': allow_private and claim.allow_private}
        if set(output) != set(identity) | {'effective_limits', 'result', 'traffic'}:
            raise ValueError()
        if _encode({key: output[key] for key in identity}) != _encode(identity):
            raise ValueError()
        effective = claim.limits.effective(ceiling or RequestLimits())
        if _encode(output['effective_limits']) != _encode(effective.model_dump()):
            raise ValueError()
        if claim.observation:
            from .mcp_observation import validate
            validate(claim, output['result'])
        else:
            validate_result(claim.check_id, claim.asset.model_dump(), output['result'])
        traffic = output['traffic']
        if not isinstance(traffic, list) or not (0 if claim.observation else 1) <= len(traffic) <= effective.request_budget:
            raise ValueError()
        required = {'url', 'method', 'status', 'elapsed_ms', 'bytes', 'truncated', 'address', 'attempt'}
        for row in traffic:
            if not isinstance(row, dict) or not required <= set(row) <= required | {'body_sha256'}:
                raise ValueError()
            url = row['url']
            if (not isinstance(url, str) or len(url) > 2048 or '?' in url or '#' in url
                    or normalize_url(url) != url or not in_scope(url, claim.asset.url) or row['method'] != 'GET'):
                raise ValueError()
            for field, low, high in (('status', 0, 599), ('bytes', 0, 131072), ('elapsed_ms', 0, 60000),
                                     ('attempt', 1, effective.request_retries + 1)):
                if type(row[field]) is not int or not low <= row[field] <= high:
                    raise ValueError()
            if type(row['truncated']) is not bool or not isinstance(row['address'], str):
                raise ValueError()
            address = ipaddress.ip_address(row['address'])
            if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
                address = address.ipv4_mapped
            if (address.is_unspecified or address.is_multicast or address.is_link_local
                    or str(address) == '100.100.100.200' or not identity['allow_private'] and not address.is_global):
                raise ValueError()
            if row['status'] and 'body_sha256' not in row:
                raise ValueError()
            if 'body_sha256' in row and (not isinstance(row['body_sha256'], str)
                                        or not re.fullmatch(r'[a-f0-9]{64}', row['body_sha256'])):
                raise ValueError()
        if claim.observation and any(row['status'] == 'completed' for row in output['result']):
            if not any(200 <= row['status'] < 300 for row in traffic):
                raise ValueError()
            completed_urls = {row['url'] for row in output['result'] if row['status'] == 'completed'}
            if not completed_urls <= {row['url'] for row in traffic if row['status']}:
                raise ValueError()
        return output
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ExecutionResultError('remote_result_unconfirmed') from None
