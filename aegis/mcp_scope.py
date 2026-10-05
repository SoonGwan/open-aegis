"""Signed single-use scope authority for the reviewed MCP execution server.

Issuers and the server's signing key are trusted. This is not remote attestation.
"""
import base64
import hashlib
import hmac
import math
import time
from urllib.parse import urljoin, urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .checks import CHECK_IDS
from .network import in_scope, normalize_url
from .policy_models import AuthorizationRule
from .remote_mcp import _decode, _encode
from .runtime import ExecutionPolicy
from .tool_contracts import PACKAGE_SHA256, require_contracts

FORMAT = 'aegis-mcp-scoped-get-v1'
MAX_CLAIM_BYTES = 32768
MAX_TOKEN_CHARS = 44000


class ScopeGrantError(ValueError):
    pass


class RequestLimits(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    target_rps: float = Field(default=2.0, ge=.1, le=20)
    target_parallel: int = Field(default=1, ge=1, le=4)
    request_timeout: float = Field(default=8.0, ge=.1, le=30)
    dns_timeout: float = Field(default=4.0, ge=.1, le=30)
    task_timeout: float = Field(default=30.0, ge=.2, le=3600)
    request_budget: int = Field(default=24, ge=1, le=240)
    request_retries: int = Field(default=1, ge=0, le=2)
    retry_delay: float = Field(default=.5, ge=.05, le=10)

    def effective(self, ceiling):
        # Retry delay is a minimum wait, so shrinking it would increase authority.
        values = {key: max(value, getattr(ceiling, key)) if key == 'retry_delay'
                  else min(value, getattr(ceiling, key)) for key, value in self.model_dump().items()}
        return RequestLimits(**values)

    def execution_policy(self):
        return ExecutionPolicy(**self.model_dump())


class StrictAuthorizationRule(AuthorizationRule):
    model_config = ConfigDict(extra='forbid', strict=True)


class ScopeAsset(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(default='Approved asset', min_length=1, max_length=120)
    type: str = Field(default='web', pattern=r'^(web|api)$')
    url: str = Field(max_length=2000)
    revision: int = Field(ge=1, le=9_007_199_254_740_991)
    authorized: bool
    authorization_rules: list[StrictAuthorizationRule] = Field(default_factory=list, max_length=20)

    @model_validator(mode='after')
    def approved_scope(self):
        if self.authorized is not True or normalize_url(self.url) != self.url or urlsplit(self.url).query:
            raise ValueError('scope_asset')
        if any(not in_scope(urljoin(self.url, rule.path), self.url) for rule in self.authorization_rules):
            raise ValueError('scope_rule')
        return self


class ScopeClaim(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    format: str = Field(pattern=r'^aegis-mcp-scoped-get-v1$')
    nonce: str = Field(pattern=r'^[a-f0-9]{32}$')
    server_id: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_.-]+$')
    task_id: str = Field(min_length=1, max_length=80)
    check_id: str
    package_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    issued_at: int = Field(ge=1)
    expires_at: int = Field(ge=1)
    authorization_expires_at: int = Field(ge=1)
    allow_private: bool = False
    asset: ScopeAsset
    limits: RequestLimits

    @field_validator('check_id')
    @classmethod
    def reviewed_check(cls, value):
        if value not in CHECK_IDS:
            raise ValueError('check_id')
        return value

    @model_validator(mode='after')
    def validity(self):
        if (not 1 <= self.expires_at - self.issued_at <= 300
                or not self.expires_at <= self.authorization_expires_at <= self.issued_at + 7210):
            raise ValueError('grant_lifetime')
        return self


def _key(key):
    if not isinstance(key, bytes) or not 32 <= len(key) <= 4096:
        raise ScopeGrantError('scope_key')
    return key


def sign_claim(claim, key):
    """Trusted issuer primitive, intentionally absent from the public HTTP API."""
    raw = _encode(claim.model_dump(), MAX_CLAIM_BYTES)
    payload = base64.urlsafe_b64encode(raw).rstrip(b'=')
    signature = hmac.new(_key(key), payload, hashlib.sha256).hexdigest().encode()
    return (payload + b'.' + signature).decode('ascii')


def verify_claim(token, key, server_id, *, timestamp=None):
    try:
        if not isinstance(token, str) or len(token) > MAX_TOKEN_CHARS:
            raise ValueError()
        payload, signature = token.encode('ascii').split(b'.')
        expected = hmac.new(_key(key), payload, hashlib.sha256).hexdigest().encode()
        if len(signature) != 64 or not hmac.compare_digest(expected, signature):
            raise ValueError()
        raw = base64.b64decode(payload + b'=' * (-len(payload) % 4), altchars=b'-_', validate=True)
        if len(raw) > MAX_CLAIM_BYTES:
            raise ValueError()
        claim = ScopeClaim(**_decode(raw))
        current = time.time() if timestamp is None else timestamp
        if (claim.server_id != server_id or claim.package_sha256 != PACKAGE_SHA256
                or claim.issued_at > current + 5 or claim.expires_at <= current):
            raise ValueError()
        return claim
    except (ValueError, TypeError, UnicodeError):
        raise ScopeGrantError('invalid_scope_grant') from None


def issue_grant(task, asset_id, check_id, server_id, key, *, ttl=60, timestamp=None, allow_private=False, request_budget=None):
    """Mint only from a current approved task snapshot, never arbitrary URL input."""
    try:
        require_contracts(task)
        approved = task.get('approved_at')
        if (task.get('status') not in ('queued', 'running') or type(approved) not in (int, float)
                or not math.isfinite(approved) or approved <= 0
                or check_id not in task['checks'] or type(ttl) is not int or not 1 <= ttl <= 300):
            raise ValueError()
        snapshots = [asset for asset in task['scope_snapshot'] if asset['id'] == asset_id]
        if len(snapshots) != 1:
            raise ValueError()
        asset = snapshots[0]
        relevant = {key: asset[key] for key in ('id', 'name', 'type', 'url', 'authorized')}
        relevant['revision'] = asset.get('revision', 1)
        relevant['authorization_rules'] = asset.get('authorization_rules', []) if check_id == 'api_authorization' else []
        policy = task['execution_policy']
        limits = RequestLimits(**{key: policy[key] for key in RequestLimits.model_fields})
        if request_budget is not None:
            if type(request_budget) is not int or not 1 <= request_budget <= limits.request_budget:
                raise ValueError()
            limits = limits.model_copy(update={'request_budget': request_budget})
        current = int(time.time() if timestamp is None else timestamp)
        queue_timeout = policy['queue_timeout']
        if type(queue_timeout) not in (int, float) or not 1 <= queue_timeout <= 3600 or approved > current + 5:
            raise ValueError()
        authority_end = math.ceil(approved + queue_timeout + limits.task_timeout + 5)
        expiry = min(current + ttl, authority_end)
        context = _encode([FORMAT, task['id'], asset_id, relevant['revision'], check_id, server_id, approved, PACKAGE_SHA256])
        # Job identity is independent of key rotation. MAC verification still
        # protects the entire grant; the nonce alone grants no authority.
        nonce = hashlib.sha256(context).hexdigest()[:32]
        claim = ScopeClaim(format=FORMAT, nonce=nonce, server_id=server_id,
                           task_id=task['id'], check_id=check_id, package_sha256=PACKAGE_SHA256,
                           issued_at=current, expires_at=expiry, authorization_expires_at=authority_end,
                           allow_private=allow_private, asset=ScopeAsset(**relevant), limits=limits)
        return sign_claim(claim, key)
    except (ValueError, TypeError, KeyError):
        raise ScopeGrantError('task_scope_authority') from None
