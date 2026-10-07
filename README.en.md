# Open Aegis

**An open source security validation workspace connecting assets, approvals,
evidence, remediation and independent retests.**

[한국어](README.md) · [Project website](https://aegis.no-money-do-you-have-money.com/en/) · [Feature status](docs/FEATURES.md) · [ARTEX inventory](docs/ARTEX-INVENTORY.md) ·
[Release criteria](docs/V1-READINESS.md) · [Security policy](SECURITY.md)

![Dashboard from an owned synthetic test service](docs/images/dashboard.jpg)

Open Aegis is an independently written project informed by ARTEX's public feature
structure. It does not copy or fork ARTEX code. All implementation in this
repository is provided under the [MIT license](LICENSE), with no commercial tier.
The current package version is **1.0.0**. See the [validation evidence](docs/V1-RELEASE-CANDIDATE.md),
[release publication status](https://github.com/SoonGwan/open-aegis/releases) and
[signed bundle installation](docs/INSTALL-RELEASE.md). It does not
claim complete ARTEX parity or detection of every vulnerability.

## What it does

- Manage authorized assets, owners, tags and explicit GET API access policies.
- Freeze scope, tool contracts and execution limits into plans; require separate
  administrator approval before execution.
- Run bounded parallel Workers with declared dependencies, shared planning todos,
  reviewed goal decomposition and result-based proposals requiring fresh approval.
- Inspect HTTP security headers, HTTPS/HSTS and certificate expiry, cookie flags,
  CORS settings, scoped links and operator-defined API authorization expectations.
- Track evidence, coverage, traffic metadata, findings, decisions and independent
  retests; export Markdown, CSV and JSON reports.
- Review ScopeSentry imports and configured remote sources before applying assets.
- Select a configured, reviewed MCP GET server for approved tasks and atomically
  store verified results and audit events. Selected observed URLs use a separately
  registered batch tool, reuse each response across checks, and preserve provenance
  through partial retries and retests. Arbitrary registered tools do not run.
- Reuse versioned task templates, organize tasks by categories, and archive terminal
  tasks while retaining execution and evidence history.
- Review versioned prompt supplements and fixed-recipient model profiles for separate
  planner/conversation defaults; inspect the snapshots saved with each call. Model
  profiles, explicit catalog lookup, task-specific planner/conversation selections and
  a fixed-message provider connection check have passed their scoped verification.
  Model settings preserve unresolved request IDs and reviewed input across reloads
  until an explicit retry or cleanup. Creation-time planner/conversation selection
  and recovery have also passed scoped verification. Custom agent bindings and
  automatic failover remain open.
- Configure fixed webhook notifications with delivery/attempt history and explicit
  bounded manual retries.
- Use optional OpenAI-compatible or direct Claude text planning and recorded-evidence conversation;
  keep provider usage and configured price estimates distinct from actual billing.
- Use administrator/operator/viewer roles within one shared workspace, SQLite or
  native PostgreSQL storage, audit checkpoints, and backup/restore commands.

The console is currently in Korean. The backend uses Python/FastAPI and the
console uses React/TypeScript. Read-only stdio MCP exposes existing workspace
records; the separate scoped execution service has its own authorization boundary.

## Start locally

Use Linux/macOS with Python 3.11+ and Node.js 22 with npm, then run from the checkout:

```sh
./start.sh
```

Open **http://127.0.0.1:8787** and create an administrator password of at least
12 characters. There is no default password. The script installs locked runtime
dependencies and builds the console. Copy `.env.example` to `.env` for local
configuration; environment variables take precedence.

Register an asset you are authorized to test, create a plan, review its scope and
checks, and approve it. Review findings and evidence, then create and approve a
separate retest after remediation. Link observation does not automatically visit
the discovered URL. HTTPS redirects across origins require the final origin to be
registered. Credentials belong in server environment variables, not asset URLs.

For an isolated synthetic target, run `examples/lab_server.py` and start the console
with `AEGIS_LAB_MODE=1`. Keep lab mode disabled for normal deployments.

## Deployment and integrations

Docker Compose is provided; set a random `AEGIS_SETUP_TOKEN` in `.env` before
`docker compose up --build -d`. Published ports default to host loopback. Read the
[operations guide](docs/OPERATIONS.md) before exposing or restoring the service.
PostgreSQL requires the locked optional driver and a prepared schema; see
[storage setup](docs/POSTGRES-STORAGE.md).

Remote execution requires both a fixed `AEGIS_MCP_CONNECTIONS` endpoint and an
`AEGIS_MCP_EXECUTORS` entry with an independent signing key. An administrator
reviews tool definitions before a task can select the server. Each task still
requires approval. See [the execution contract](docs/MCP-EXECUTION.md).

Additional model recipients use `AEGIS_MODEL_DESTINATIONS`: fixed IDs and names
reference server environment variables containing the URL and API key. Review
profiles/defaults after credential changes. Configuration availability is distinct
from a tested provider connection. Explicit [catalog lookup](docs/MODEL-CATALOG.md)
and a [fixed-message connection check](docs/MODEL-CONNECTION.md) send separate,
reviewed provider requests; the connection check can incur provider charges.
[Task-specific selections](docs/TASK-MODELS.md) pin existing tasks to a reviewed
profile revision for planning or recorded-evidence conversation. See
[model profiles](docs/MODEL-PROFILES.md) and [prompt versions](docs/PROMPT-VERSIONS.md).

## Current limits and verification

This is a single shared workspace, not tenant isolation. Current checks validate
specific configuration and operator-defined policy expectations. They do not
provide autonomous exploitation chains, arbitrary shell/plugin execution or a
general traffic interception proxy. Remote stop prevents later dispatch and local
result admission, requests signed revocation, and records whether the server
acknowledges it. The server interrupts response waits and rejects later use of
the revoked grant. Already-transmitted requests cannot be undone; cancellation
acknowledgement after connection/process loss is recovered by a bounded durable
cancellation-only outbox when the original endpoint/key and authority still match.
Expiry, configuration changes and persistent failures remain unconfirmed. Selected
observed-response jobs use the fixed batch adapter. General plugin OS/egress
isolation, full accessibility/mobile journeys, production interoperability and
the complete v1 release criteria remain open.

Verification uses owned synthetic targets and disposable databases, including native
PostgreSQL ownership, provider-call admission, recovery, installed wheel and offline
backup/restore checks. Hosted Ubuntu24.04 image and Compose rehearsals cover startup,
authentication, retained data and clean shutdown. The current connection-enabled
100-module backend passed1,930 full native checks and606 installed-wheel checks,
with two SQLite skips for native ownership-only cases in each run; the native
variants passed. The connection console passed103 frontend checks; its latest
unresolved-model-request recovery changes passed114 frontend checks and146 related
native lifecycle checks. All six jobs passed in
[the connection main run](https://github.com/SoonGwan/open-aegis/actions/runs/37399067286)
and [the recovery PR run](https://github.com/SoonGwan/open-aegis/actions/runs/37403128445).
These are scoped results for the recorded source, rather than results for pending
feature branches. See [validation records](docs/VALIDATION.md) for source identities,
preserved receipts and the remaining v1 checks. This project has not
undergone an independent security audit.

Contributions should preserve approval, scope, evidence and recovery behavior.
See [CONTRIBUTING.md](CONTRIBUTING.md); report security issues privately following
[SECURITY.md](SECURITY.md).
