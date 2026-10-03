# Validation — 2026-10-03

## Executed

- `.venv/bin/python -m pytest -q`: **35 passed**. Final run takes about 8 seconds.
- `npm run build`: TypeScript check and Vite production build succeed.
- `npm audit --omit=dev`: **0 known vulnerabilities** reported at execution time.
- `scripts/backup.py`: online backup created from the disposable preview DB;
  `PRAGMA integrity_check` returns **ok**, with 22 persisted records in that backup.
- Browser: local synthetic asset registration → plan creation → explicit approval
  → completion → six configuration/review findings → evidence listing.
- Browser: task detail and evidence-grounded conversation produce a stored answer.
- Browser: responsive dashboard at 390×844; document scroll width stays within
  viewport width. Icon navigation has explicit accessible names.
- MCP read-only record access and protocol responses are tested locally; the actual stdio subprocess also initializes and lists four tools.

The preview uses a loopback synthetic server, not an external organization's
infrastructure. Its HTTP transport, missing headers, cookie attributes and CORS
policy deliberately produce findings. API authorization was skipped in that UI
run because the registered preview asset had no rules; the API policy check is
covered by automatic tests.

## Behavioral coverage

Authentication, session revocation, cross-origin rejection, Host validation,
no target requests before approval, repeated approval prevention, denial without
execution, scope origin/path validation, private and metadata address rejection,
DNS pinning, out-of-scope redirects, cancellation, request budget, atomic import
validation, authorization policy mismatch, missing credential failure, secret
redaction, failing-before/passing-after retest, preserved original evidence,
server failure resulting in an inconclusive retest, restart recovery, invalid
AI plan fallback, AI plan permutation constraints, provider redirect rejection,
provider plaintext rejection and response size limits, evidence-grounded record
assistant, read-only MCP and authentication data exclusion.

## Not executed

- Docker image build and Compose startup: Docker is not installed locally.
- Live LLM provider call: no provider key was supplied. Plan handling uses mocked
  provider responses; redirect behavior uses a local synthetic HTTP provider.
- Third-party target scans, full TLS fixture coverage, external penetration test,
  independent security audit, production load/soak test, multi-user deployments.
- GitHub publication: no remote repository is configured.

## Dependency notice

The test suite reports one Starlette deprecation warning about the use of httpx
in its TestClient. It does not cause test failures. Runtime dependencies are
locked to the versions used for this validation; dependency updates should rerun
the behavioral suite.

This record supports the initial implementation's tested behavior. It is not a
claim of ARTEX feature parity, complete vulnerability detection, or production
security certification.

## v1 development checkpoint — 2026-10-03

- Latest suite: **41 passed**, one existing Starlette TestClient deprecation warning.
- Latest TypeScript/Vite production build passes.
- Asset lifecycle regression: edit invalidates pending approval; archive hides assets
  from active scope, preserves findings, pauses schedules; restore does not silently
  resume schedules or reactivate stale approvals; active execution blocks mutation.
- Actual browser: edited a synthetic asset owner, archived it, viewed archive,
  restored it, and confirmed historical findings remain.
- Actual server subprocess with an open SSE response shuts down on SIGTERM without
  forced connection cancellation or ASGI exception.
- `scripts/check_design.py`: nine selected text/background pairs pass 4.5:1;
  primary action is 4.83:1, support text 9.09:1, hero 7.24:1.
- Desktop and 390×844: all twelve menus opened and document width stayed within
  viewport width. Dashboard and mobile edit dialog visually inspected.
- Initial overview loading now waits for authoritative data before rendering totals.

These checks are incremental v1 work. Multi-user roles, PostgreSQL, complete
integration coverage, migration/restore, load testing, container execution and
full interaction/accessibility audit remain incomplete; see V1-READINESS.md.

## Identity and recovery checkpoint — 2026-10-03

- Role/migration/restore regression suite passes; the latest complete test count
  is recorded below after request-limit and validation-redaction checks.
- Admin/operator/viewer routes are enforced on the server. Only admin approves
  scans or manages users; viewer mutation attempts and operator approval attempts
  are rejected. Public identity responses omit salt/password hashes.
- Role/disable/password changes revoke all old sessions; unchanged permissions and
  profile-only changes do not. Concurrent demotion cannot remove the final admin.
- Legacy credential migration preserves password and assets, backs up before
  changes, revokes sessions, is idempotent, refuses newer schema, and rolls back on
  malformed legacy auth. The running disposable preview DB was migrated as well.
- Actual online backup/CLI restore to artifacts/restore-rehearsal succeeded and
  retained the expected asset, coverage, evidence, findings, messages, task and
  traffic counts. Restore with an active workspace is rejected in regression tests.
- Restore preserves rollback state, handles encoded filenames, validates integrity
  and schema, and makes pre-restore cookies unusable after reopening the app.
- Browser: legacy administrator password login and creation of a viewer account;
  viewer UI disables creation/edit/archive and hides user management.

- Browser: viewer password confirmation mismatch shows an error; successful change
  ends the session. Latest UI also resets navigation and refreshes public identity
  after sign-out/profile changes.

Latest full suite: **58 passed**, one existing deprecation warning (15.20 seconds).
The request boundary rejects oversized and incomplete streamed bodies; error
responses omit invalid input/context. Stale user edits return 409.

Additional MCP filename/connection regression: **2 passed**; the new test verifies
read-only access with an encoded filename and unchanged DB bytes.
Browser: changed viewer password logs out, new password logs in; user management
on 390×844 has no document overflow.

## Finding triage lifecycle (2026-10-04)

- Full backend suite: 92 passed; one existing Starlette/httpx deprecation warning.
- After normalizing empty optional fields to avoid artificial revision/history changes,
  the eight triage tests passed again, including the UI-shaped no-op save regression.
- Frontend TypeScript and production build passed.
- Browser: assigned admin and saved an acceptance reason; a second stale form received
  a conflict and retained its draft; loading the current record restored the saved decision.
- Mobile 390×844: document width 390, dialog width 366, no horizontal overflow.
- Captures: `artifacts/v1-triage-desktop.jpg`, `artifacts/v1-triage-mobile.jpg`,
  `artifacts/v1-triage-mobile-top.jpg` (local artifacts, excluded from Git).
- Scope and remaining limitations: [TRIAGE.md](TRIAGE.md). This is not ARTEX feature parity
  or completion of the full v1 release checklist.
