# Security policy

This project is pre-release software. It has not received an independent
security audit. Run the console on loopback or behind a private authenticated
network boundary. Use HTTPS and `AEGIS_SECURE_COOKIE=1` for remote access.

Report vulnerabilities through the enabled
[private vulnerability reporting channel](https://github.com/SoonGwan/open-aegis/security/advisories/new).
Do not post credentials or exploitable deployment details in a public issue.

The console has admin, operator and viewer roles in one shared workspace.
Only admins approve execution and manage accounts; operators manage plans,
assets and results; viewers can read and export. Role/status/password changes
revoke existing sessions. Role decisions apply when each request is authorized;
a previously authorized in-flight action is not retroactively canceled.
Local hash-linked audit verification and manual checkpoint comparison are implemented.
They do not authenticate a completely rewritten database without a trusted independently
retained checkpoint. Tenant isolation, automatic external audit checkpoint storage,
encryption at rest and an independent security review remain incomplete.
See the [threat model](docs/THREAT-MODEL.md) for trust boundaries, implemented controls,
residual risks and test coverage, and [audit integrity](docs/AUDIT.md) for its limits.

Login admission limits each connection address to ten attempts per five minutes,
retains at most 4,096 active address buckets and admits at most four simultaneous
login verifications. Live rate histories are not evicted to admit new addresses;
overload returns 429 with Retry-After before password derivation. These in-process
limits reset on restart and do not provide distributed rate limiting or a total
authentication CPU/memory bound. See [runtime policy](docs/RUNTIME.md).

Automatic public FastAPI docs/schema routes are disabled. Administrators can inspect
the API contract through `/api/openapi.json` using their server session; operators,
viewers and anonymous clients cannot. This reduces unauthenticated API enumeration,
not a substitute for authorization. Health/setup-status and login assets remain
available as required for startup and authentication.

The runtime blocks out-of-scope origins/paths and reserved addresses, pins
target connections to validated DNS results, and checks redirects. Lab mode
intentionally permits private/loopback addresses while still rejecting
link-local and common metadata addresses. Keep lab mode off outside isolated
tests. These controls are defense in depth; deployment-level egress restrictions
remain useful.

Evidence contains metadata, hashes, and explicit policy expectations. HTTP
response bodies, credential values, cookie values, and query values are not
persisted by the target transport. User-entered names, goals, notes, rules,
and custom path segments may themselves contain sensitive information: avoid
entering secrets in them.

An LLM provider receives operator goals, asset names/types, and check IDs when
AI planning is selected. It never receives target response bodies or test
credentials. Configure only trusted provider endpoints on the server.

Schema migration creates a restricted pre-migration backup. Backup files include
password and session hashes. Offline restore refuses an active workspace,
preserves a rollback copy, validates the backup and clears restored sessions.
Keep a separately protected backup and test restoration in another directory.
