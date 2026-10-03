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

## Shared execution limits and operations (2026-10-04)

- Full backend suite: **117 passed**, one existing Starlette/httpx deprecation warning.
- After clearing stopped Future bookkeeping, the two shutdown regressions and
  documented launcher/SSE SIGTERM test passed again (3 passed).
- TypeScript/Vite build passed; selected semantic text/background pairs pass AA.
- Real loopback peers verify shared origin spacing and slots, in-flight cancellation,
  slow-drip headers/body deadlines, bounded stalled DNS, retries and total request budget,
  long Retry-After, queue expiry, updated policy review, current-scope retry plans,
  and preservation of an accepted decision when a retest times out.
- A generated test CA verifies HTTPS and hostname mismatch rejection; a real HTTPS
  compatible LLM fixture verifies tool order and token usage without persisting its key.
- The documented launcher was spawned as a process with an open SSE connection;
  SIGTERM drained the stream and exited within the three-second test bound.
- Browser: registered an owned loopback redirect fixture, approved one GET validation,
  observed scope failure, then created a retry plan that remained pending for review.
  Approved policy is visible on approval cards and task detail. Runtime screen shows
  pending=1, requests=1 during that preview process.
- Desktop and 390×844 captures: `artifacts/v1-runtime-desktop.jpg`,
  `artifacts/v1-runtime-mobile.jpg`. Mobile document width did not exceed the viewport.
- Execution/clock/OS limitations: [RUNTIME.md](RUNTIME.md). Container execution,
  live external LLM keys, production load/soak and full v1 release are not verified.

## Main-list URL navigation and query recovery (2026-10-04)

- `npm --prefix web test`: **8 passed** on Node 22.18.0. Bookmark round trips,
  scoped filters, graph parameter preservation, reset rules, malformed numeric bounds,
  literal Unicode/punctuation and surrogate boundaries are covered.
- `tests/test_records.py tests/test_graph.py`: **13 passed**, one existing
  Starlette/httpx deprecation warning. Backend code is unchanged in this increment.
- TypeScript/Vite production build passed. The nine selected semantic color pairs pass AA;
  this does not constitute a full accessibility audit.
- Isolated owned loopback fixture: 32 active assets, 3 archived assets, 32 actual GETs,
  160 findings, two completed tasks and 28 pending plans. No external hosts were tested.
- Browser: paginated all six main lists; a new tab restored asset search and rows 26–32.
  Task status Back/Forward restored search, position and insertion watermark. Changing
  a finding severity/search reset position; an offset of 10,000,000 clamped to the last page.
- Creating another plan with an old unmatched approval query opened a fresh approval list
  and showed the new pending plan (29 pending). That plan was not approved or executed.
- A real fixture-server shutdown displayed the localized connection error and retry control
  without a false empty result. After restarting the same data directory, the four-second
  automatic refresh recovered to the actual empty search result. The manual retry click was
  not observed: automatic recovery had already removed its button.
- Native history through the app's Back/Forward controls was verified, including replacing
  a forward branch with a new route and disabling Forward at the new end.
- Existing graph evidence bookmarks loaded the selected proof. Changing a graph filter
  preserved app history metadata; Back returned to assets. Archived asset filtering returned
  exactly the three archived fixtures and reset pagination.
- Desktop captures: `artifacts/v1-navigation-desktop.jpg`, `artifacts/v1-navigation-error.jpg`
  (local artifacts, excluded from Git). History buttons measure 44×44 CSS pixels.
- A requested 390×844 viewport override did not change the observed document viewport
  (1810 CSS pixels), so this increment has **no verified mobile capture**. Mobile regression
  remains on the v1 checklist. Evidence/observation/note/schedule lists and detail URL state
  also remain outside this increment; see [PAGINATION.md](PAGINATION.md).

## Bounded notes and scheduled-work lists (2026-10-04)

- Full backend suite: **122 passed**, one existing Starlette/httpx deprecation warning.
  The five new workspace tests passed again after removing a test observation race
  between task insertion and schedule completion bookkeeping.
- Frontend navigation suite: **9 passed**; TypeScript/Vite production build passed.
- New tests populate 1,050 notes and 1,100 schedules and reject unbounded `Store.all`
  reads during queries. They cover literal content search, nested schedule goal/asset
  filters, boolean enabled validation, watermarks, live updates, legacy 1,000-row caps
  with count headers and viewer read/mutation permissions.
- Scheduler tests verify oldest-due-first batches, future/paused exclusion, the next
  50 due rows after processing the first 100 and the actual SQLite due-index query plan.
  The real scheduler thread generated one pending plan with zero loopback requests.
- Browser fixture: 61 notes and 40 future schedules (35 active, 5 paused). Deleting the
  only note on page two retained the search and replaced the position with page one
  (25 remaining matches). Creating a note cleared the previous search and displayed it.
- Browser: searched 35 active weekly schedules, moved to page two and paused one;
  the page remained at offset 25 with 34 active matches. The paused filter returned that
  exact schedule. A new tab restored active search, filter and page two.
- Desktop capture: `artifacts/v1-workspace-schedules.jpg` and
  `artifacts/v1-workspace-notes.jpg` (local artifacts, excluded from Git).
  No new mobile verification is claimed in this increment.
- The main local server was restarted with the latest backend; the isolated review
  server was shut down after verification. Evidence/observation pagination, unbounded
  report/MCP collections and other remaining v1 work are still tracked separately.

## Finding evidence and retest pages (2026-10-04)

- Full backend suite: **127 passed**, one existing Starlette/httpx deprecation warning.
  The five new finding-record tests and 39 existing triage/validation tests also passed
  separately. Frontend navigation suite: **9 passed**; TypeScript/Vite build passed.
- New tests populate 1,200 proofs and 1,200 matching retests plus 2,000 unrelated retests.
  They prohibit `Store.all` and per-proof `Store.get` reads while requesting detail/pages.
  The initial detail arrays contain 25 records each with correct total/has_more metadata.
- Tests cover literal search, insertion watermarks with new references, live updates,
  duplicate/missing proof references and rejection of mismatched asset, task, check or
  fingerprint. Viewer access, missing parents, invalid collection and query bounds are covered.
- Browser fixture: 31 explicitly labelled synthetic observations and 33 synthetic retest
  records in the isolated review workspace. These are UI samples, not claims of fresh
  HTTP observations or actual retest executions; no target requests were added.
- Browser: expanded evidence only when requested, saw loading before results, moved to
  rows 26–31 and opened the original observation. An unmatched tool query showed a real
  empty result. Retests moved to rows 26–33; searching the reason for sample 01 reset to
  the first page and returned exactly that record. The two searches are independent.
- Desktop capture: `artifacts/v1-finding-evidence-page.jpg` (local artifact, excluded
  from Git). The tool display name is resolved from the loaded catalog and its searchable
  ID remains visible. Nine selected semantic color pairs pass AA; no new mobile or full
  screen-reader verification is claimed.
- API compatibility and remaining size limits: [PAGINATION.md](PAGINATION.md).
  Detail arrays now contain only the latest 25 records. Related-ID metadata, report/MCP
  history reads and detail URL persistence remain incomplete.
