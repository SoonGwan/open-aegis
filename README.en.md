# Open Aegis

**An open source security validation workspace connecting assets, approvals,
evidence, remediation and independent retests.**

[한국어](README.md) · [Feature status](docs/FEATURES.md) · [ARTEX inventory](docs/ARTEX-INVENTORY.md) ·
[Release criteria](docs/V1-READINESS.md) · [Security policy](SECURITY.md)

![Dashboard from an owned synthetic test service](docs/images/dashboard.jpg)

Open Aegis is an independently written project informed by ARTEX's public feature
structure. It does not copy or fork ARTEX code. All implementation in this
repository is provided under the [MIT license](LICENSE), with no commercial tier.
The current version is **0.2.0a1, a pre-release validation candidate**. It does not
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
- Use optional OpenAI-compatible planning and recorded-evidence conversation;
  keep provider usage and configured price estimates distinct from actual billing.
- Use administrator/operator/viewer roles within one shared workspace, SQLite or
  native PostgreSQL storage, audit checkpoints, and backup/restore commands.

The console is currently in Korean. The backend uses Python/FastAPI and the
console uses React/TypeScript. Read-only stdio MCP exposes existing workspace
records; the separate scoped execution service has its own authorization boundary.

## Start locally

Install Python 3.11+ and Node.js 22 with npm, then run from the checkout:

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

Verification uses owned synthetic targets and disposable databases. The cancellation-recovery change
passes 39 cases with SQLite and actual PostgreSQL. Its related MCP
integration passes 311 tests from an isolated installed wheel with
SQLite and actual PostgreSQL. The console passes 97 tests. Hosted Ubuntu 24.04
image and Compose rehearsals verify startup, authentication, retained data,
backup/restore and clean shutdown. These checks do not constitute an independent
security audit or a production guarantee. See [validation records](docs/VALIDATION.md)
for exact artifacts, dates and remaining checks.

Contributions should preserve approval, scope, evidence and recovery behavior.
See [CONTRIBUTING.md](CONTRIBUTING.md); report security issues privately following
[SECURITY.md](SECURITY.md).
