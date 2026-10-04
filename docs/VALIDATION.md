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

## Full observation records and source search (2026-10-04)

- Full backend suite: **131 passed**, one existing Starlette/httpx deprecation warning.
  Observation/record tests separately: **10 passed**. Frontend navigation tests:
  **10 passed**; TypeScript/Vite production build passed.
- The new API tests populate 1,050 observations with an archived source asset and prohibit
  unbounded `Store.all` reads. They verify complete overview count despite its 100-row
  preview, 25-row pages, source name/ID and URL search, exact asset/task filters, missing
  source labels, literal punctuation, insertion watermarks and live name/URL updates.
  Viewer access and query/auth boundaries are covered.
- An owned loopback server returned HTML with 35 in-scope links. One reviewed
  `endpoint_inventory` task completed and persisted all 35 links. The actual server log
  contained exactly one `GET /html/` and no requests to the observed links. It was then
  stopped before browsing the saved records.
- Browser: searched by the source asset's name, visited rows 26–35, verified source asset
  and task names/IDs, and restored the same search/page in a new tab. The asset preview's
  full-list action reset search and pagination. A nonmatching query returned an empty result.
- Capture: `artifacts/v1-observations-desktop.jpg` (local artifact, excluded from Git).
  No mobile or whole-app accessibility completion is claimed in this increment.
- Observed URLs are rendered as text. Observation is link inventory rather than an
  access test or vulnerability conclusion; source display names are current metadata.
  Remaining related-ID/report/MCP bounds and detail URL work: [PAGINATION.md](PAGINATION.md).

## Paged read-only MCP tools (2026-10-04)

- Full backend suite: **143 passed**, one existing Starlette/httpx deprecation warning.
  Existing/new MCP tests separately: **15 passed**. Frontend code is unchanged.
- Tests populate 1,050 assets and 1,200 proofs/retests and prohibit an unbounded reader
  call. They verify compact finding-ID counts, provenance rejection, latest-25 detail
  arrays, complete page totals, literal search and event sequence watermarks.
- SQLite `mode=ro` rejects a real DELETE, and database bytes are unchanged by MCP reads.
  A database filename containing Unicode, spaces and URI punctuation remains supported.
- A separate `python -m aegis.mcp` process completed initialize, tools/list and paged
  tools/call over stdin/stdout. It advertised seven tools and rejected a 17-request batch.
- Argument tests reject boolean integers, null snapshots, unsafe integers, invalid limits,
  offsets and archive types, long search and unknown SQL arguments without echoing input.
  A result exceeding 512 KiB is returned as a short tool error.
- Compatibility changes and practical limits: [MCP.md](MCP.md). This does not verify an
  external MCP client integration, remote transport, hard process memory bounds or full v1.

## Compact HTTP finding associations (2026-10-04)

- Full backend suite: **146 passed**, one existing Starlette/httpx deprecation warning.
  Projection/history/triage tests separately: **16 passed**. Frontend TypeScript/Vite build passed.
- Tests store 10,000 task references and 10,000 evidence references on one finding.
  Overview, paged findings, legacy findings and finding detail omit those ID arrays and
  return reference counts. The detail body is below 2,000 bytes for that synthetic record.
- Stored associations remain identical after reads and after an accepted triage decision.
  PATCH returns the new decision revision and counts without returning the association arrays.
  The pure projection preserves the supplied committed decision and does not re-read a later edit.
- Normal evidence/retest pages, human triage conflict handling and the full existing suite
  remain passing. Frontend types allow compact counts; current UI does not depend on ID arrays.
- These checks prove the selected response contracts, not every HTTP response or a hard
  memory bound. Task detail/report reads and other remaining work stay on the v1 checklist.
  Contract changes: [PAGINATION.md](PAGINATION.md).


## Paged task findings and execution events (2026-10-04)

- Full backend suite: **150 passed**, one existing Starlette/httpx deprecation warning.
  New task-record tests: **4 passed**. Frontend TypeScript/Vite build and **10** navigation
  tests passed. All nine selected semantic colour pairs pass the design contrast check.
- Tests seed 1,050 matching findings/events and foreign records, prohibit unbounded
  Store.all reads, verify latest-25 detail summaries and complete last pages, literal event
  search, role/authentication boundaries, insertion watermarks and current finding edits.
- An initial generic collection route intercepted the existing messages route. The handler
  now registers two explicit paths; the regression test and full suite verify messages GET.
- Browser QA used an existing completed loopback task with **100 findings / 205 events**.
  Finding page 26–50, event page 26–50, independent CSP/Worker searches (20 each), preservation
  across metadata polling and finding-detail navigation were checked. No new target scan ran.
- Desktop capture: `artifacts/v1-task-records-desktop.jpg`. This increment does not claim
  mobile/accessibility completion, bounded chat/report exports, retention or full v1.
  API compatibility changes: [PAGINATION.md](PAGINATION.md).


## Paged task conversation and atomic answers (2026-10-04)

- Full backend suite: **154 passed**, one existing Starlette/httpx deprecation warning.
  Message/task/validation tests separately: **39 passed**. Frontend TypeScript/Vite build
  and all **10** navigation tests passed.
- Message tests seed 1,050 task messages plus a foreign task, prohibit Store.all, verify
  the legacy 1,000-row cap and count headers, first/last pages, literal punctuation search,
  insertion watermarks, live edits, role/authentication and query validation.
- Assistant tests seed 1,200 findings and a foreign critical finding. The oldest matching
  critical finding still appears first in the bounded eight-result SQL context.
  A real SQLite trigger aborts assistant insertion; the question is rolled back too.
- Browser QA used **61 explicitly labelled synthetic messages** on an existing completed
  loopback task. It checked pages 1–25, 26–50, 51–61 and a one-result content search.
  Posting while filtered clears search and returns to the newest page. Two separately
  submitted questions added exactly four messages; a third question from page 26–50
  after the key fix added one more pair (final total **67**) with grounded replies.
  Target traffic stayed **33**; no scan or command ran.
- Newest-page open and a newly saved answer both scroll to the bottom of the message
  region (final measured scrollTop 3249.5, scrollHeight 3569, clientHeight 320).
  The initial UI review caught duplicate sibling React keys causing repeated task panels
  during polling. Distinct task-record/chat keys fix the issue; final DOM counts are
  checked across metadata polling and question submission.
  Capture: `artifacts/v1-chat-history-desktop.jpg`.
- This is still a rules-based summary, not LLM conversation or execution intervention.
  POST network-retry idempotency, report bounds, detail URL and full accessibility/mobile
  regression remain outstanding. Contract changes: [PAGINATION.md](PAGINATION.md).


## Consistent streaming report exports (2026-10-04)

- Full backend suite: **163 passed**, one existing Starlette/httpx deprecation warning.
  Existing coverage/triage/validation subset: **50 passed** before the final stream SQL
  refinement. Frontend code is unchanged.
- Nine report-stream tests cover 1,005 records in each scoped collection, complete JSON/
  Markdown/CSV, count-independent Python reads, CSV formula protection, authentication,
  viewer access and preservation of full finding associations.
- Updates to task, finding, history and coverage after the first chunk, and a newly added
  evidence row, do not change the existing export snapshot. The coverage reader uses
  the same connection rather than opening newer Store connections.
- A real write on the read-only connection fails. Unicode/space/URI punctuation filenames
  work. Early close, malformed JSON/SQL and both ASGI 2.0 disconnect events and ASGI 2.4
  send errors release the connection. The paused-iterator send-error case uses an explicit
  response cleanup wrapper.
- A 6,000-row-per-collection export is larger than **12 MB** with tracemalloc peak below
  **2 MB**. SQLite query plans have no temporary sorting tree for the report queries.
  Python allocation measurement is not native-memory/RSS or a concurrency/soak guarantee.
- Empty-workspace JSON, CSV and Markdown exports were checked separately.
- The restarted main preview served all six real HTTP downloads (workspace/task ×
  JSON/CSV/Markdown) with chunked transfer, no Content-Length, no-store headers and
  matching JSON/CSV finding counts. Saved fixtures: `artifacts/v1-report-smoke/`.
  Runtime dependency check passed; anyio was already pinned in the lockfile and is now
  declared as a direct dependency.
  Contracts, snapshot lifetime and outstanding quotas/timeouts: [REPORTS.md](REPORTS.md).


## Export admission, deadline and settings metrics (2026-10-04)

- Final backend suite: **172 passed**, one existing Starlette/httpx deprecation warning.
  Export/report subset: **18 passed**. Frontend build, **10** navigation tests and the
  nine selected semantic contrast pairs passed.
- An initial full-suite run collided with a parallel frontend build removing dist/assets
  and had one fixture setup error (170 passed). Build and subsequent suites were sequential;
  171 passed before the final SQL-disconnect test, and the final 172-test suite passed.
- Eight concurrent admission attempts accept exactly two, reject six, and release each
  slot once. HTTP capacity rejection returns 429/Retry-After before stream creation;
  missing-task validation still returns 404 and capacity recovers after release.
- Slow ASGI sends and a real expensive recursive SQLite query hit monotonic deadlines,
  release the read connection/slot and increment timed_out. A disconnect event interrupts
  active SQL before a ten-second deadline, completes cleanup in under one second, and
  increments cancelled. ASGI 2.0 blocked-send deadline was also checked separately.
- The initial SQL timeout inherited OSError through TimeoutError and was translated by
  ASGI 2.4 into ClientDisconnect. A dedicated non-OSError deadline type fixes classification;
  SQL timeout, send error, disconnect and failure outcome tests now pass.
- Browser settings QA shows 0/2 downloads, 120-second limit and all outcome counters.
  A real 355,845-byte HTTP report increments completed to one, stays at zero active and
  updates the browser panel on polling. Capture: `artifacts/v1-export-limits-desktop.jpg`.
- Limits are process-local; individual Python/native operations remain cooperative and
  multi-process quotas, retention and load/soak verification remain outstanding.
  Configuration and contracts: [REPORTS.md](REPORTS.md).


## Task and finding detail bookmarks (2026-10-04)

- Frontend TypeScript/Vite build and **12** navigation tests passed. The selected nine
  semantic contrast pairs still pass. Backend source is unchanged in this increment.
- Tests verify detail ID/type validation, removal of invalid bookmarks, source list and
  graph query preservation, closing without losing list position, normal screen navigation
  clearing details and initial navigation preserving valid detail bookmarks.
- Browser QA opened the existing 100-finding task from a searched task list, reloaded its
  URL and recovered the same task and background search. Task → finding → Back → Forward
  restored the correct IDs; Close → previous navigation reopened the finding.
- A fresh second tab opened the copied finding URL and loaded the same title/source with
  one dialog and focus on its close control. A missing task shows an explicit error/retry;
  retry remains an error and Close returns to the searched list. No target scan ran.
- A malformed `/bad` detail ID is removed on initial navigation and leaves the searched
  list with no dialog. The main preview restored its existing coverage task via a direct
  task URL with the current built frontend; no backend restart was needed.
- Capture: `artifacts/v1-detail-bookmark-desktop.jpg`. IDs restore only after authentication.
  Task polling starts after the first successful read, skips overlapping requests and
  aborts on navigation. Older responses also check the live URL before applying results.
- Nested proof/retest/task/chat search and position, scroll, unsaved triage inputs and
  other modals are not URL state yet. Full mobile/accessibility regression remains pending.
  Contract: [PAGINATION.md](PAGINATION.md).


## Modal keyboard stability and complete focus boundaries (2026-10-04)

- Frontend build and all **12** navigation tests passed; the nine selected semantic
  contrast pairs pass. Backend source is unchanged in this increment.
- Before the fix, the real asset archive dialog moved focus from Cancel to Close after
  the four-second overview refresh. Its effect reran on a new inline onClose callback.
  After the fix, focus remains on Cancel across polling. Escape returns to the original
  Archive button, removes all inert attributes and restores body scroll locking.
- The production Modal keeps the latest callback in a layout-updated ref while setting
  focus/inert state once per mount. Name/description reference its visible title/subtitle.
- The browser regression fixture imports the actual component. Tab skips a negative
  tabindex button and a fieldset-disabled input, reaches a final summary, and wraps in
  both directions. Enter expands the summary. Escape uses the latest tick (138/138)
  and restores the opener instead of calling the initial stale callback.
- With a final tabindex=0 scroll region, Shift+Tab reaches the region, ArrowDown changes
  scrollTop to 40, and Tab wraps to Close. DOM label/description references resolve to
  the expected visible text. This does not prove a real screen-reader announcement.
- Capture: `artifacts/v1-modal-focus-desktop.jpg`. Repeatable manual fixture and instructions:
  [web/tests/browser/README.md](../web/tests/browser/README.md). The fixture is not an
  automated npm test or a production entry. No asset was archived and no scan ran.
- All-page mobile/accessibility audit, opener-removal fallback and broader interaction
  journeys remain outstanding; the global v1 accessibility checkbox stays incomplete.


## Report download recovery (2026-10-04)

- Frontend TypeScript/Vite build and all **16 tests** passed (12 navigation and four
  report transport tests). Backend source is unchanged; this increment does not rerun
  or supersede the previously recorded 172-test backend suite.
- Unit checks cover all formats and filenames, task ID query encoding, credentials,
  429 status/delay, Retry-After dates/clamping, HTML/empty/interrupted body rejection,
  aborted responses and 401 status preservation. They do not exercise a real 401 UI.
- An isolated local app reserved its two export permits without opening snapshots.
  The actual UI export received 429, showed its inline error and disabled five-second
  countdown. After the fixture released the permits, manual retry started a Markdown
  download and remained on the reports URL. This does not prove a saved file on disk.
- An ASGI fixture delayed export body sends. The JSON control showed progress and
  cancellation; cancelling displayed the inline stopped state. Restoring normal sends
  and retrying started its download. The real runtime showed active=0, started=5,
  completed=2, cancelled=3 and rejected=1; two cancellations belong to the fixture's
  reserved permits, one to the real browser cancellation. Target traffic remained 33.
- Desktop captures: `artifacts/v1-report-download-error-desktop.jpg` and
  `artifacts/v1-report-download-recovery-desktop.jpg`. Main preview served the current
  bundle without restarting the backend. No target scan ran during this verification.
- Browser Blob buffering has no hard resource bound. Unexpected schema with a valid
  media type/transport, actual saved-file contents, mobile/assistive technology and
  long-running download load remain unverified. Contract: [REPORTS.md](REPORTS.md).


## Idempotent task question retries (2026-10-04)

- Backend full suite: **175 passed**, one existing Starlette/httpx deprecation warning.
  After narrowing conflict handling to MessageRequestConflict, the seven message tests
  passed again. Frontend tests: **16 passed**; TypeScript/Vite build passed.
- A test commits a keyed question/reply then loses the response. Retrying after changing
  task state returns the original reply exactly and leaves two messages. Different
  content with the same key is 409; a fresh key creates a new exchange.
- API tests verify actor/task isolation, invalid token bounds and viewer restrictions.
  Eight independent Store instances concurrently commit the same exchange and all
  receive one identical reply. Reopening the database also replays it. An insert trigger
  rejecting the reply rolls back its question. Legacy unkeyed pair tests still pass.
- Browser QA on an isolated app replaces the first successful POST response with 503
  after committing it. The screen preserves the question and shows '질문 다시 보내기'.
  Database message count is 69 after that request and remains 69 after UI retry, with
  one matching question. The screen clears the input, shows the stored reply and success
  status. Target traffic remains 33; no scan runs. This fixture models loss after commit
  with an HTTP failure, not a literal socket disconnect.
- Capture: `artifacts/v1-chat-retry-desktop.jpg`. Server deduplication persists in the
  message records; it is not a per-process cache. Existing auth and operation checks
  run on replay. No migration is required. Request IDs are optional for legacy clients.
- The UI keeps an unresolved key only in its mounted panel. Closing the detail, document
  reload, and question edits can create a new intent; automatic unresolved-intent recovery
  remains outstanding. The client uses crypto.getRandomValues for its 128-bit key so
  generation does not depend on secure-context-only randomUUID.


## Same-tab recovery of unacknowledged questions (2026-10-04)

- Frontend **19 tests passed** and TypeScript/Vite build passed. Three additional tests
  cover persistence/scoping, late acknowledgement versus a newer intent, unavailable
  and full storage, failed removal, malformed/versioned/oversized entries. Backend
  source is unchanged; the preceding 175-test result is not rerun in this increment.
- An isolated app committed the first keyed exchange, then replaced its response with
  a 503. The actual UI displayed the error and retained the question. Navigating the
  same tab to a new document at its task bookmark restored the open chat panel, original
  question and retry control. Closing the task and reopening its bookmark also restored
  it. No browser state was injected to create this recovery.
- Manual retry confirmed the original reply and cleared the pending information. The
  task's messages remained **71** before and after retry, with one matching question.
  A subsequent new document had the chat panel closed and no recovery prompt.
- A second fixture response failure created another exchange. '미확인 전송 지우기'
  cleared its input/prompt; a fresh document did not restore it. The database still
  contained that question and a total of **73** messages, proving the action did not
  delete server history. Traffic remained **33** throughout; no target scan ran.
- Capture: `artifacts/v1-chat-pending-restored-desktop.jpg`. Main preview serves the
  current frontend and reports healthy. Actor-scoping and storage-denial behavior are
  unit-tested, not a browser account-switch/storage-quota simulation.
- Storage is plaintext sessionStorage scoped by actor/task with one pending intent per
  pair. It supports same-tab document/detail transitions, not cross-device recovery,
  guaranteed restoration after closing a tab, or preservation of unsubmitted drafts.
  Automatic retries are absent. Full mobile/assistive-technology QA remains open.
  Contract: [PAGINATION.md](PAGINATION.md).


## Scoped operational reads and restart recovery (2026-10-04)

- Full backend suite: **178 passed**, one existing Starlette/httpx deprecation warning.
  Three new scoped-operation tests passed separately; existing coverage/chat/asset
  regression tests also pass. Frontend source is unchanged in this increment.
- Recovery processes 205 running/queued/stopping tasks across more than two batches
  while 1,100 completed historical tasks carry 10 KB payloads each. Tests reject Store.all
  and completed-history JSON decoding; completed check cells survive, missing cells
  become interrupted, all 205 tasks recover and the queue watchdog remains alive.
- A keyset test inserts a queued task after iteration begins and changes the first task
  status. All original 205 IDs are visited once; the later insert remains queued. Reads
  use a startup rowid upper bound and close each connection before recovery writes.
- API guards run with Store.all forbidden amid 1,100 extra assets/tasks. Duplicate
  registration, archived URL reservation, duplicate batch rejection without partial
  import, URL collision, active-task archive rejection and history URL-change rejection
  preserve their existing status codes. Archiving pauses all 105 connected enabled
  schedules, preserves unrelated/paused schedules, and restoration does not resume them.
- Coverage finalization and assistant completion counting iterate expected cells instead
  of collecting whole coverage lists. Detail/report contracts retain their current data.
  Asset URL lookup has a partial expression index created idempotently at Store open.
- Main preview restarted cleanly, reports healthy, serves the authenticated asset page
  with 200 and has a live watchdog with zero errors. Its target traffic stays at three
  records before/after restart. EXPLAIN QUERY PLAN confirms URL existence lookup uses
  records_asset_url, and the index exists in the reopened preview database.
- These are limits on selected/decoded record counts, not a measured RSS/CPU/latency
  bound. Individual task payloads, JSON relationship arrays and the archived asset's
  paused-schedule audit ID list remain size dependent. No long-running soak is proven.
  Contracts: [RUNTIME.md](RUNTIME.md), [PAGINATION.md](PAGINATION.md).


## Finding collection bookmark restoration (2026-10-04)

- Frontend **23 tests passed** and TypeScript/Vite build passed. Four new tests verify
  independent nested collection state, search/page reset, collapse preservation, detail
  change/close cleanup, background list preservation and malformed Unicode/position
  normalization. Backend source is unchanged; the prior 178-test backend result stands.
- Browser QA uses the existing explicitly synthetic 31-proof/33-retest finding. Evidence
  searched for security_headers and retests for 판정, each moved to offset 25 with its
  own insertion watermark. The DOM contains six proof rows (26–31/31) and eight retest
  rows (26–33/33). A fresh tab opened the copied URL and restored those same rows,
  searches and expanded sections without injecting browser state.
- The modal's previous navigation restores retests to the first page while leaving
  evidence on its second page; next restores retests to offset 25. Collapsing and
  reopening evidence preserves its second page. Closing the copied detail removes
  both collection prefixes and returns to page=findings. No target scan runs.
- Capture: `artifacts/v1-finding-collection-bookmark-desktop.jpg`. Main preview serves
  the current bundle without backend restart. Fixture traffic remains 33.
- Async page correction checks the live detail ID and collection state before changing
  the URL. Search input replaces history; toggles/page moves push history. Existing
  background list/detail-ID navigation tests still pass.
- Individual proof disclosure/scroll, triage drafts, decision-history/task/chat nested
  positions and remaining modals are not covered by this increment. Mobile and actual
  assistive-technology regression remain open. Contract: [PAGINATION.md](PAGINATION.md).


## Responsive document-width review and report card repair (2026-10-04)

- An isolated loopback fixture embeds the real built app in a width-controlled frame.
  App-origin metrics confirm innerWidth=320/390, rather than assuming the outer browser
  resized. With ordinary vertical scrollbars rootClient/rootScroll are 305/375; both
  remain equal. This is desktop Chromium responsive rendering, not a phone simulator.
- Fourteen main screens were measured at both widths: overview, tasks, assets,
  observations, findings, graph, approvals, traffic, reports, schedules, notes, agents,
  settings and users. Selected visible controls/headings/sections show no uncontained
  horizontal overflow. Table/graph controls outside the viewport have a horizontally
  scrolling ancestor; this observation does not prove they are touch/keyboard reachable.
- The initial 320px report screenshot showed the new download control squeezed into
  the icon card's second column, wrapping its action text. At <=600px the description
  and download now span both columns and the icon occupies only the heading row. The
  subsequent 320px screenshot shows the action on one line with a wider description.
- Changed report cards were rechecked at 320/390px, and 1280px shows no root/uncontained
  overflow. The 320px task dialog is 296px wide with no detected uncontained overflow;
  a 390px finding dialog is 366px wide. Initial and updated screenshots were inspected.
- Artifacts: `artifacts/mobile-geometry-review.json`, `artifacts/v1-mobile-reports-320.jpg`,
  `artifacts/v1-mobile-reports-320-after.jpg`, `artifacts/v1-mobile-reports-390-after.jpg`,
  `artifacts/v1-mobile-task-320.jpg`, `artifacts/v1-mobile-finding-before.jpg`. Metrics
  cover geometry, not every content/state or all visual clipping.
- TypeScript/Vite build passed, and nine selected Montage contrast pairs pass AA. No
  new tests mirror this CSS change; prior 23 frontend and 178 backend tests are not
  rerun. The saved manual QA launcher compiles and booted against the same fixture.
- The manual launcher permits only same-origin QA embedding and adds a metrics script;
  normal production CSP/X-Frame-Options and runtime entry are unchanged. Instructions:
  [web/tests/browser/README.md](../web/tests/browser/README.md). Screens are navigated
  through visible fixture controls, with no browser storage/state injection or scan.
- Final measurement artifact contains 14 entries per width. Fixture target traffic stays
  at 33, and the normal main preview serves the latest build with X-Frame-Options=DENY
  and frame-ancestors none. The QA server shut down cleanly after review.
- Touch gestures, real iOS/Android browser behavior, zoom, focus through every journey,
  keyboard table scrolling, full modal/error/recovery states and actual screen-reader
  output remain unverified. The global mobile/accessibility gates stay incomplete.

## Audit chain, schema 2 and checkpoint verification (2026-10-04)

- Full backend regression: **186 passed**, with the existing Starlette/httpx warning.
  After adding the CLI subprocess case, the audit subset was run again: **9 passed**.
  The full suite was not rerun after that test-only addition. Audit module and CLI
  compilation and diff whitespace checks pass; frontend source is unchanged.
- Independent Store instances concurrently append 80 events to one chain. A failed
  hash insert rolls back its event and head. Tests reject changed content, missing
  middle/tail records, missing hashes and unsealed inserts, including backup validation.
  Recomputed local chains can pass alone but fail against the earlier checkpoint.
- Schema 1 migration preserves existing records and seals them as a legacy baseline.
  Its preflight SQLite backup remains schema 1. Schema 2 backup/restore preserves the
  checkpoint, and opening schema 2 never silently reseals modified history.
- CLI checks run as real subprocesses: read-only verification, checkpoint export with
  mode 0600, comparison after append, refusal to overwrite, and failure on tampering.
- Main preview was stopped cleanly and restarted on schema 2. All 83 prior events and
  three target traffic records remain; the pre-schema2 backup contains the 83 events
  at schema 1. A login adds event 84, which verifies against the saved seq-83 checkpoint.
  Health and authenticated asset reads succeed. No target scan runs.
- Artifacts: `artifacts/v1-audit-before-migration.json` and
  `artifacts/v1-audit-preview-checkpoint-20261004.json`. This checkpoint is saved on the
  same host; the review does not prove independently trusted external storage.
- Local hashes are not signatures. Existing legacy history is only sealed at upgrade;
  whole-history verification is explicit, and business changes and their audit events
  are not universally one transaction. External storage automation, audit UI, retention
  and large-scale soak remain open. Contract: [AUDIT.md](AUDIT.md).

## Installed maintenance commands (2026-10-04)

- Backup, restore and audit CLI implementations now live in the Python package with
  three console entry points. Existing checkout scripts delegate to those same modules.
  This closes the missing maintenance-command path in wheel/Docker package installation;
  no backend business behavior or frontend source is changed.
- A normal isolated `pip wheel --no-deps` build succeeds. Wheel SHA-256:
  `1a8d8923b13f9d09472c4e33f784183f5a493fde5f1b772b78cbca2e5cf03edb`.
  The initial non-isolated build failed because the development environment lacks
  bdist_wheel; the standard isolated build installs its own build requirements.
- `scripts/review_installed_commands.py` installs that wheel without dependencies or
  an index in a fresh temporary venv, removes PYTHONPATH/PYTHONHOME, runs outside the
  checkout, and verifies imported code belongs to the installed prefix. All three
  actual installed executables succeed on a synthetic schema-2 fixture.
- Rehearsal verifies Unicode/space/question-mark paths, mode-0600 backup, overwrite
  refusal, check-only validation, audit export/comparison, preserved records and revoked
  sessions, workspace-lock refusal, preservation of pre-restore data, and refusal to
  restore a tampered backup before destination creation. Result:
  `artifacts/package-review/installed-commands.json`.
- Targeted audit/backup regression: **11 passed**, one existing Starlette/httpx warning.
  The prior full 186-test regression is not rerun for this CLI packaging relocation.
- The main preview's specific running session remains live. Checkout wrappers create
  and validate an online backup containing three traffic records and 84 audit events;
  it verifies against the existing seq-83 checkpoint. Artifact:
  `artifacts/package-review/live-preview-backup.db`. No scan, server restart or restore
  into the main workspace occurs.
- Docker is unavailable (`command not found`), so image build, container start/health/
  shutdown and volume permissions remain unverified. The wheel excludes built web
  assets; it is not a complete standalone web release. Container operations and the
  repeatable isolated CLI rehearsal are documented in [OPERATIONS.md](OPERATIONS.md).

## Audit malformed-data rejection and tail verification (2026-10-04)

- New controlled corruption cases reproduced **8 failures and 2 passes** before the
  fix. Empty log ID and invalid sealing boundaries could pass local verification;
  zero/negative legacy sequences could be sealed; a BLOB payload raised TypeError;
  changed tail content/link allowed another event to be appended.
- The fixed verifier/sealer checks positive sequences, finite timestamps, text/NULL
  event fields, hexadecimal IDs/hashes and a valid existing legacy boundary. Sequence
  gaps remain valid. Append recomputes the last event hash and checks its link against
  the preceding stored hash before inserting anything. It still does not verify every
  historical row on every append, and local metadata checks are not signatures.
- Initial targeted audit/backup/identity regression: **32 passed**. Three additional
  cases then verify failed schema-1 sealing rolls back and preserves its preflight
  backup; gaps work but a missing legacy boundary fails; malformed CLI input exits 2
  without a traceback or checkpoint output. Full regression with all additions:
  **200 passed**, one existing Starlette/httpx warning.
- A new wheel builds and passes the isolated installed-command rehearsal. SHA-256:
  `7a1bc19244890aa27e16a39e72e49201809d8de932a36b06ea15534d84fd9783`.
  Artifact: `artifacts/audit-validation-review/installed-commands.json`.
- Main preview stopped cleanly and restarted with the fixed code. Health, login and
  authenticated asset read succeed. Login appends event 85; the entire chain still
  verifies against the prior seq-83 checkpoint. Schema stays 2, legacy boundary stays
  83 and traffic stays three. Artifact:
  `artifacts/audit-validation-review/preview-after-restart.json`. No scan runs.
- No schema migration or frontend change is needed for this repair. External trusted
  checkpoint automation, signatures and audit UI remain open; [AUDIT.md](AUDIT.md)
  documents the stronger tail checks and the limits of metadata validation.

## JSON API response and ownership policy (2026-10-04)

- Authorization rules accept an optional bounded JSON Schema 2020-12 subset and a
  JSON Pointer with an expected string owner/customer/resource ID. Unknown fields,
  unsupported schema keywords, external references and invalid pointers are rejected
  before registration. Existing rules without these options keep status-only behavior.
- Runtime checks only complete JSON media types; duplicate keys, invalid UTF-8,
  non-finite numbers, truncation, excessive depth/nodes and absent owner paths are
  inconclusive. Schema evidence contains only keyword categories, and ownership
  evidence contains only a boolean. No response value is persisted by this evaluator.
- Targeted policy/validation regression: **57 passed**. Full backend regression:
  **226 passed**, one existing Starlette/httpx warning. After two test-only additions,
  policy tests run again: **28 passed**. The full suite is not rerun after those additions.
  `pip check`, module compilation and diff whitespace checks pass.
- Real owned loopback HTTP fixtures prove correct response, nested type mismatch,
  different owner, denied access, unexpected allowed access, HTML login content,
  oversized/truncated response and missing owner behavior. Plans send no request before
  approval; approved snapshots preserve the exact policy. Full JSON reports exclude
  both actual different-owner and secret-body sentinels.
- Changing ownership expectations increments asset revision and rejects approval of
  the old plan without sending a request. An owner finding remains open after an HTML
  inconclusive retest, then resolves after a complete correct-owner response.
- Main preview restarts cleanly with the new dependency and policy code. Health,
  authenticated asset reads and unsupported-$ref rejection (422) succeed. Existing
  assets remain two and target traffic remains three; audit events 87 still verify
  against the prior seq-83 checkpoint. Runtime evidence:
  `artifacts/api-policy-runtime-review.json`. No main target scan or asset creation occurs.
- Frontend source is unchanged; the existing rule JSON editor can submit these fields.
  Dedicated schema/ownership controls and reproducible-test export remain open. JSON
  parsing/validation has byte/structure limits but no independent CPU preemption or
  large-scale soak proof. Contracts and primary references: [API-POLICY.md](API-POLICY.md).

## Approved policy export and standalone replay (2026-10-04)

- Authenticated task export creates a versioned manifest from the approved scope,
  retaining only asset ID/revision/URL/rules, approval metadata and execution limits.
  Pending/no-policy tasks are rejected; download has a fixed attachment filename and
  no-store cache policy. The manifest is bounded to 8 MiB and contains no credential
  values, response bodies or task goals. Rule models are shared with registration.
- Installed `aegis-replay-policy` and checkout wrapper validate without DNS/HTTP by
  default. Explicit --run uses the engine's scoped, DNS-pinned GET transport and API
  check. Private targets require explicit --lab; metadata addresses remain blocked.
  Current environment limits only tighten exported limits, and requests are sequential.
- Policy subset: **35 passed**. Full backend regression: **235 passed**, one existing
  Starlette/httpx warning. Tests prove approval/auth gates, no traffic on validation,
  default loopback refusal, explicit lab replay pass/mismatch exit codes, secret-value
  exclusion, rejection of out-of-scope/credential-name/duplicate-key artifacts before
  requests, and local budget reduction to one request producing inconclusive.
- Wheel builds with SHA-256
  `264453f0448836ca1c4483d9e153d7447883e0d17a1978d572a6307a89e21a62`.
  A clean venv installs that wheel and all pinned runtime requirements; pip check passes.
  Its actual installed executable runs outside the checkout with PYTHONPATH/PYTHONHOME
  removed, on a manifest downloaded from an approved synthetic loopback task.
  Validation sends no requests; replay sends exactly / and /api/account and passes.
  Credential/body sentinels appear in neither the artifact nor CLI output. Imported
  package origin belongs to the isolated installation. Evidence:
  `artifacts/policy-replay-package/installed-replay-review.json`.
- Local editable installation exposes the new console entry point. Main preview stops
  and restarts cleanly; health, authenticated assets and export 401/404 behavior pass.
  Assets remain two, target traffic remains three and audit events 88 verify against
  the earlier seq-83 checkpoint. Evidence:
  `artifacts/policy-replay-package/main-runtime-review.json`. No main target replay runs.
- Frontend source is unchanged. Screen download controls/editor, mobile journey,
  signatures, runtime-version pinning, long-running soak and independent result-log
  storage are not proven. A manifest is unsigned metadata and does not grant current
  execution permission; standalone replay does not update the source server's records.
  Usage and limitations: [API-POLICY.md](API-POLICY.md).

## Task policy download UI (2026-10-04)

- Task details now contain an API policy reproduction section, eligible JSON download,
  visible reasons for disabled downloads, and expandable standalone-file instructions.
  It uses existing Montage tokens, borders and button states. The report download
  lifecycle is shared with the policy endpoint: same-origin credentials, media/empty
  body checks, abort/error/manual retry and session-expiry handling. Task ID is encoded
  as a path segment; each task's download component has its own identity key.
- Frontend **25 tests passed**, TypeScript/Vite build passed. Existing report format,
  quota, body-failure and abort tests still pass after extraction of the file fetcher.
  Added policy tests verify endpoint encoding/filename/409 errors and eligibility
  reasons, including missing/null legacy rule arrays. Final bundle:
  `index-DSNkh0F-.js` / `index-keBDZODJ.css`. Backend source is unchanged; prior 235-test
  backend regression is not rerun.
- An isolated explicitly synthetic workspace contains completed/pending/non-API tasks.
  These seeded completion/approval fields are UI fixtures, not real target execution
  evidence. Browser QA confirms one injected 503 becomes a visible alert and manual
  retry successfully initiates the download; it does not prove browser disk completion.
  Pending and non-API tasks show distinct reasons and disabled buttons. The disabled
  button's aria-describedby resolves to its reason; Tab from the instructions summary
  reaches the report button. Actual screen-reader behavior is not verified.
- Desktop error/success/pending screenshots were captured and visually inspected:
  `artifacts/v1-policy-download-error.jpg`,
  `artifacts/v1-policy-download-success.jpg`, `artifacts/v1-policy-download-pending.jpg`.
  The returned synthetic artifact passes the CLI's no-request validation:
  `artifacts/policy-download-fixture.json`.
- Width-controlled real-app documents measure 320/390px innerWidth, equal rootClient/
  rootScroll, modal widths 296/366px, and no selected uncontained horizontal overflow.
  Artifact: `artifacts/policy-download-mobile-geometry.json`. Instructions remain
  collapsed in these narrow-width measurements; touch, vertical reachability, expanded
  mobile instructions, cancellation/error states and real phone browsers are not proven.
- Fixture target traffic stays zero. QA tabs leave the fixture and its server shuts
  down cleanly. Main preview loads the final bundle and shows the legacy-policy reason
  on its existing task; health is good and target traffic remains three. No target
  verification/approval occurs. The dedicated policy editor and full journeys remain open.

## Structured API policy editor (2026-10-04)

- Asset create/edit now offers up to 20 GET rule forms, schema JSON and ownership
  options, plus advanced whole-array JSON editing. Unknown fields or unrepresentable
  types prevent form conversion without discarding the original JSON. Inactive options
  serialize to null; their draft text survives only while remaining in form mode.
- Frontend **28 tests passed**, TypeScript/Vite build passed. New tests cover nested
  schema/ownership round trips, false permission preservation, unknown-field refusal,
  invalid JSON/count/schema shapes and UTF-8 byte limits. Bundle:
  `index-9ZWrOIk-.js` / `index-7BINzslS.css`. Backend source is unchanged; the prior
  **235-test** backend regression was not rerun for this UI change.
- In an isolated synthetic workspace, desktop browser QA verified rule add/delete
  focus, form/JSON conversion, unknown-field preservation, invalid schema blocking,
  and a server 422 for unsupported $ref with inputs retained. Saving and reopening
  restores schema/ownership and the false permission. Changing to true via JSON then
  restoring the form selects the correct allow value and persists revision 3.
  Native select selection via automation was inconclusive; its full interaction is
  not claimed as verified. The fixture generated **zero target requests**. Evidence:
  `artifacts/policy-editor-saved.json`, `artifacts/policy-editor-updated.json`.
- Desktop saved-form and 320px component screenshots were visually inspected:
  `artifacts/v1-policy-editor-saved.jpg`, `artifacts/v1-policy-editor-320.jpg`.
  Standalone actual-component iframe documents at 320/390px have root client/scroll
  widths 305/375 respectively (normal scrollbar space), with no selected uncontained
  horizontal overflow. Metrics include textarea/fieldset/legend bounds:
  `artifacts/policy-editor-mobile-geometry.json`. This is component geometry, not a
  full mobile asset registration journey. Below-fold ownership controls, touch/zoom,
  real phone browsers, screen readers and the maximum 20-rule workload remain open.
- QA tabs leave the fixture and both isolated servers stop. Main preview remains
  healthy at version 0.1.0 with two assets and three target traffic records, unchanged.

## On-demand audit review UI/API (2026-10-04)

- Administrators can manually verify the complete local audit chain in system settings,
  optionally comparing a previously independently retained checkpoint. Results distinguish
  local match, checkpoint match, mismatch and incomplete verification; changing input or
  starting another request clears previous results. No automatic verification polling.
  The panel uses existing Montage tokens, solid borders and button states. Initial
  browser inspection exposed a narrow default textarea; the final layout adds full-width
  input, spacing and a wrapping checkpoint display.
- The administrator-only POST is read-only, omits event content, and returns no-store.
  It skips generic POST audit insertion so verification on a damaged chain can still
  return a result without repair or append. The service permits one concurrent scan,
  rejects extras with 429/Retry-After: 5, and checks a 10-second cooperative deadline
  between events and SQLite operations. A single event's encoding/hashing is not
  forcibly preempted; disconnect does not guarantee immediate server scan termination.
- Focused audit tests: **26 passed**. Full backend: **239 passed** with the existing
  Starlette/httpx warning. New tests prove auth/role gates, strict checkpoint fields,
  no event/detail leakage, unchanged audit state after scans, matching prefix and wrong
  hash comparison, altered-event detection without repair, retryable 429, zero-deadline
  incomplete results, no missing-DB creation and capacity release after completion.
  Frontend: **28 passed**, TypeScript/Vite build passes. Final assets:
  `index-B694Rvti.js` / `index-BrFX8zqJ.css`.
- Isolated synthetic browser QA verifies local match, matching/wrong checkpoints,
  malformed JSON, server 422 with input retained, and a deliberately altered event
  producing mismatch with only its seq exposed. The altered fixture message is restored
  exactly and CLI verification passes again at 10 events. Final desktop success/error
  captures are visually inspected: `artifacts/v1-audit-review-success.jpg` and
  `artifacts/v1-audit-review-mismatch.jpg`. These fixture comparisons prove functionality,
  not independent checkpoint storage or authentic historical content.
- Real app settings documents at 320/390px have equal root client/scroll widths 305/375
  and no selected uncontained horizontal overflow. Evidence:
  `artifacts/audit-review-mobile-geometry.json`. The audit panel is below the initial
  viewport; full mobile interaction, expanded results, touch, screen readers and maximum
  input/long-running scans require separate review.
- QA tabs leave the isolated app and its server shuts down. Main preview restarts cleanly
  and its new panel verifies 88 events with legacy sealing through seq 83. CLI confirms
  the same chain. Health is good; main assets remain two/target traffic three and fixture
  target traffic zero. External checkpoint automation, signatures, permanent status and
  workload validation remain open in [AUDIT.md](AUDIT.md).

## Threat model and current architecture reconciliation (2026-10-04)

- Added [THREAT-MODEL.md](THREAT-MODEL.md): protected assets and operating assumptions,
  browser/API, approval/execution, target transport, provider, storage, MCP/CLI and
  export trust boundaries; concrete threat paths, current controls, residual risks,
  source/test references, release gaps and incident preservation guidance.
- Inspected current authentication/setup/Origin handling, password/session helpers,
  DNS scope/pinning/TLS, LLM payload, request limits, reporting CSV escaping and audit
  code. The document explicitly identifies shared-workspace/OS file access, optional
  Secure cookies, absent Origin allowance, cooperative bounds, GET side effects and
  independent checkpoint limitations. These are documented limits, not newly proven
  defenses or an independent security audit.
- Updated stale security/architecture text for implemented audit review, actual graph
  relationships, configurable runtime defaults and schema 2. README and v1 tracking
  link the model; the overall release gate remains incomplete.
- Checked **79 local links** across the new model and four linked/updated entry
  documents, with zero missing targets. Main preview health remains good. Runtime code
  is unchanged; the previous 239 backend/28 frontend results were not rerun for docs.

## Bounded login admission and metrics (2026-10-04)

- Replaced the growing address-attempt dictionary with monotonic-time admission:
  ten attempts per address in 300 seconds, at most 4,096 active buckets, at most
  ten attempt records each and four concurrent login verification/session paths.
  Expired buckets are removed in last-admission order. Capacity overload rejects
  new addresses instead of evicting live rate history. Busy rejection consumes no
  attempt/bucket, and late success cannot erase newer admitted attempts.
- Rejection returns 429/Retry-After before password derivation. Failure/exception
  releases the concurrency slot. Unknown/disabled users still incur derivation cost
  after admission. Runtime metrics expose counts/limits/denial reasons, never actual
  addresses/usernames/credentials. The existing settings metric cards display them.
- Login/identity subset: **17 passed**. Full backend: **245 passed** with the existing
  Starlette/httpx warning. Fake-clock tests prove exact expiry, live-history retention
  despite 1,000 rejected new addresses at a small configured capacity, success ordering
  and exception release. HTTP tests prove ten failed hashes followed by a hash-free
  429, Retry-After, success reset, a held hash denying a second request while health
  remains responsive, and subsequent re-admission. These are invariant tests, not
  maximum-capacity RSS/CPU or realistic distributed attack benchmarks.
- Frontend **28 passed**, TypeScript/Vite build passes; final bundle
  `index-DxJlVfcH.js` / `index-BrFX8zqJ.css`. Main preview shuts down and restarts cleanly.
  Desktop browser shows 0/4 active login checks, 0/4096 tracked addresses and zero
  denial counters; `artifacts/v1-login-admission-metrics.jpg` was visually inspected.
  No browser login is submitted; HTTP rejection behavior is covered by isolated tests.
  New mobile cards, assistive technology and browser login-overload recovery remain
  unverified. Main health is good, assets two/target traffic three; audit remains 88
  valid events through the same head and legacy sealing through seq 83.
- Limits are per process and reset on restart. Address capacity exhaustion can also
  deny new legitimate clients. Proxy address trust, all authentication endpoints,
  long-running workload and total process resources remain separate requirements.
  See [RUNTIME.md](RUNTIME.md) and [THREAT-MODEL.md](THREAT-MODEL.md).

## CI package runtime rehearsal (2026-10-04)

- Existing CI lacked frontend tests and installed package execution. Added npm test,
  wheel construction and a fresh-environment runtime/maintenance rehearsal after the
  build and backend tests. Official checkout/setup-python/setup-node v7 refs are pinned
  to full commit SHAs resolved from their official release tags. Checkout credentials
  are not persisted, token permissions remain contents:read, with job timeout and
  same-ref cancellation. No remote workflow was triggered or publication performed.
- `review_runtime_package.py` installs locked runtime dependencies and the actual wheel
  in a disposable venv outside checkout, removes AEGIS settings and Python path overrides,
  checks pip consistency/installed origin and all four executable help entry points.
  It starts the actual installed server on a handed-off bound loopback socket, serves the
  separately built UI, verifies auth denial/setup/logout, synthetic asset and unapproved
  pending-plan persistence, login limit metrics and audit review. Target requests stay
  zero. The frontend bundle is not claimed to be included in the wheel.
- Rehearsal passes with wheel SHA-256
  `a16329f4899014f5c678e901fec24ed0ec66a9cca7c5fa6e11d7fec986a8cf27`.
  Shutdown proves the installed original lifespan completes, accepts Uvicorn's clean
  SIGTERM re-raise and then verifies workspace lease re-acquisition. The existing separate
  installed maintenance rehearsal also passes. Temporary files/processes are cleaned up.
- Initial harness runs exposed its wrong assumption that legacy /api/assets returns a
  page object, and its incorrect assumption that clean Uvicorn SIGTERM always exits zero.
  Both are corrected to the actual contract, with successful lifespan completion required;
  product runtime code is unchanged. Previous 245 backend/28 frontend results are not
  rerun for the workflow/script change. YAML parses locally and selected Montage contrast
  checks pass (primary action 4.83:1, support text 9.09:1). These checks do not prove hosted
  GitHub execution, Ubuntu runtime behavior, full visual/accessibility coverage or a signed,
  byte-reproducible release. Main preview health remains good.

## Reduced-motion interaction correction (2026-10-04)

- The existing media rule removed transitions but left instantaneous 1px hover/2px
  active button translation. Added reduced-motion hover/active transform overrides for
  button and .button, retaining color/shadow/focus feedback. Static centering transforms
  belong to orbit/toast selectors; the graph uses an inline scale on its graph canvas,
  so these are outside the new button selectors. Design guidance now states that limit.
- TypeScript/Vite build and selected Montage contrast/token checks pass. This is a CSS
  interaction correction; unchanged backend/frontend behavioral tests are not rerun.
  Actual OS/browser reduced-motion preference, pointer/keyboard states and full mobile
  accessibility are not claimed verified. Manual steps are recorded in the browser
  regression README and the full accessibility gate remains incomplete.

## Workspace keyboard skip navigation (2026-10-04)

- Added the first authenticated-workspace link, visible on focus and styled with
  existing Montage primary/white and hard border/shadow tokens. Activation prevents
  hash/history navigation, focuses the current page h1 and brings it into view. The
  main landmark references that heading; it is programmatically focusable without
  adding an extra stop to ordinary forward tab order.
- Desktop browser first Tab reaches the visible skip link (128px wide, 45.5px high).
  Enter focuses workspace-title with text 시스템 설정 and leaves the full URL unchanged.
  Tab from that heading reaches 새로고침 inside main. A body-selector press attempt
  timed out; pressing Tab on the focused heading verified the continuation explicitly.
  Opening the password modal makes the skip link inert; Escape restores non-inert
  state and focus to 비밀번호 변경 without submitting a change.
- Captured and visually inspected `artifacts/v1-skip-navigation.jpg`. TypeScript/Vite
  build and selected contrast/token checks pass. Bundle:
  `index-B45QAirB.js` / `index-DOqw8joG.css`. Backend logic and existing test behaviors
  are unchanged, so full backend/frontend suites are not rerun for this UI change.
  Actual screen readers, mobile/zoom, all routes/bookmarks and keyboard sequences remain
  separate verification requirements; the full accessibility checkbox stays open.

## Task detail collection bookmarks (2026-10-04)

- Task finding/event collections now use independent URL search, offset and insertion
  snapshot state. Search replaces the current entry and resets only that collection's
  position; pages push and asynchronous correction replaces. Different/closed details
  clear task collection fields, while Back restores the prior entry. Position callbacks
  check current task ID and list state before applying an asynchronous response.
- Frontend **31 passed**, TypeScript/Vite build passes. Three added tests cover independent
  round trips and source list preservation, search reset, same/different/closed details,
  invalid bookmark normalization and Unicode-safe bounds. Final bundle:
  `index-B0mQGkrx.js` / `index-DOqw8joG.css`. Backend source is unchanged; prior 245-test
  backend regression is not rerun.
- A separate synthetic workspace receives 61 labelled event fixtures. Browser QA verifies
  event search and offset 25/snapshot 71, independent empty-result finding search, both
  searches and the second event page in a new document, third page 51–61, clearing URL
  fields on close, and Back reopening the third page with both searches. Changing event
  search yields 1–1 and clears its position without changing finding search. A generic
  close locator matched both modal close buttons; the explicit aria-label close control
  is used. No backend/target execution is inferred from seeded task completion fields.
- `artifacts/v1-task-record-bookmark.jpg` is captured and visually inspected. QA tabs
  leave the fixture and its server shuts down. Fixture target traffic stays zero, main
  target traffic stays three and main health is good. Finding-list multi-page UI, native
  Forward, error recovery, mobile/assistive technology and individual record details or
  scroll restoration are not claimed verified. Chat/triage positions remain separate.

## Administrator-only API schema (2026-10-04)

- Disabled FastAPI's default docs, redoc, schema and Swagger OAuth redirect routes.
  Added an administrator-session-only /api/openapi.json returning the generated static
  contract with no-store; the endpoint itself is excluded from that contract. Schema
  visibility does not grant operation permissions or provide interactive Swagger UI.
- Schema/identity subset: **13 passed**. Full backend: **247 passed**, with the existing
  Starlette/httpx warning. Tests prove anonymous 401, operator/viewer 403, administrator
  200, disabled default routes for authenticated and unauthenticated clients, expected
  asset/approval operation paths, no schema self-entry, and exclusion of synthetic
  workspace asset/event sentinels. Frontend source is unchanged; prior 31 frontend tests
  and build are not rerun.
- The pre-change main runtime returned 200 to an anonymous /openapi.json request.
  After clean shutdown/restart, the same path, docs, redoc and OAuth redirect return 404,
  the protected endpoint returns 401 anonymously, and health returns 200. Main assets
  remain two and target traffic three. No target verification or browser operation runs.
- Rebuilt wheel SHA-256:
  `9650d479a06d269fa00e4cccaede484ef58bc9a78bcdf1691b463c98a12d0c58`.
  Fresh installed-runtime rehearsal now includes public docs/schema denial and successful
  authenticated administrator schema retrieval. All prior installed HTTP/CLI, shutdown,
  lease and maintenance checks still pass with zero target requests. Hosted CI execution
  remains unverified. Contributor/security/threat-model documentation states the path
  change, access policy and limits; health/setup-status/login assets intentionally remain
  available for startup/authentication.

## Identity form busy states and accessible actions (2026-10-04)

- User-edit row buttons now include the target username in their accessible name;
  password-reset row buttons already did so and are unchanged. User add/edit/reset
  inputs and the own-password form are wrapped in named fieldsets disabled while
  submitting. Existing cancel/submit locks and field values remain in place. The
  zero-border fieldset uses existing layout/color tokens.
- An isolated synthetic account is edited through the real built console. A 4-second
  delayed PATCH shows the name and role controls disabled. Injected 503 re-enables
  controls and retains the entered name; retry succeeds and the stored synthetic name
  matches. `artifacts/v1-identity-error-recovery.jpg` is captured and visually inspected.
- Own-password submission uses fixture inputs and a delayed injected 503, without
  reaching the real password-change handler. All three controls are disabled while
  pending, then enabled and natively valid after error. No password value is read back
  or printed; no actual password change/session revocation is inferred from this fixture.
  Add/reset variants, native role selection, real readers/mobile/zoom and request-stall
  recovery require separate journeys.
- TypeScript/Vite build and selected contrast/token checks pass. Bundle:
  `index-B_HPuQHH.js` / `index-BqS4l0El.css`. This targeted UI change is verified through
  browser behavior rather than new implementation-mirroring tests; unchanged 247 backend
  and 31 frontend suites are not rerun. QA tab leaves the fixture and its server shuts
  down cleanly. Fixture target traffic stays zero; main runtime data is untouched.

## Task chat bookmarks with pending-question recovery (2026-10-04)

- Task conversation open/search/offset/snapshot state now lives in reviewed URL fields,
  independently of the task finding/event collections and source list. Search replaces
  the current history entry and resets only chat pagination. Disclosure and page changes
  push entries; collapse preserves the chat position and stops its poll. Closing/changing
  the detail clears chat fields. Numeric/Unicode bounds and normalization match the other
  reviewed lists. No question or request ID is stored in the URL.
- Three new navigation contract tests cover independent state, detail changes/collapse,
  search resets, malformed bookmarks, Unicode boundaries and maximum positions. All
  **34 frontend tests pass**, TypeScript/Vite build passes (`index-DttydGBI.js` /
  `index-BqS4l0El.css`). Existing message API **7 tests pass**; the full 247-test backend
  suite is not rerun for this frontend change. No backend source or CSS token changes.
- Real built UI on an isolated synthetic workspace with 61 messages restores an open
  searched conversation at 26–50 in a fresh document. The task event search remains
  independent. Enter collapses and Space reopens at that page. Page 51–61 restores after
  closing the detail and using Back; Forward closes it again. Searching for exact record
  000 resets to 1–1 and removes its previous position/watermark.
- The QA app commits one keyed question/reply pair and replaces that response with 503.
  At a filtered 26–50 page the screen retains its input and URL. A fresh document restores
  that position together with the pending question and manual retry control. Capture
  `artifacts/v1-chat-bookmark-recovery.jpg` is visually inspected. Retry confirms the
  stored reply, clears question/search, shows 1–25 of all 63 messages and success status,
  and preserves the independent event search. Database message count stays **63** before
  and after retry, with **one** matching question. Target traffic stays **zero**.
- This is an HTTP failure after commit, not a literal socket loss. No actual mobile,
  screen-reader/zoom, late-response timing race, scroll restoration, unsubmitted-draft
  persistence or AI execution intervention is claimed. Pending questions remain scoped
  plaintext same-tab storage. Overall navigation/accessibility/v1 gates remain open.

## Decision-history search, bookmarks and query recovery (2026-10-04)

- Finding history API accepts bounded `search` (200 characters) and performs SQL literal
  matching on action code, reason and actor name/username within the selected finding.
  Existing pagination/watermark response and authorization remain. New API coverage uses
  60 own entries plus a matching foreign entry, denies unbounded Store.all access, checks
  actor/case/literal SQL-like queries, disjoint pages and new inserts with/without the
  original watermark, invalid inputs, missing finding, viewer access and anonymous denial.
  Triage suite **9 passes**, full backend **248 passes** (77.70 seconds; existing
  Starlette/httpx deprecation warning).
- History is a separate initially collapsed collection with the shared records/loading/
  error/pagination UI. URL state adds `finding_history_open/q/offset/snapshot` independently
  of proof/retest collections and source lists. The same reviewed numeric/Unicode limits,
  detail cleanup, stale-position guards and history modes apply. Three additional
  navigation tests bring frontend to **37 passing tests**. TypeScript/Vite build passes:
  `index-D8kzT4in.js` / unchanged `index-BqS4l0El.css`. No new CSS or color values.
- Built UI on isolated synthetic records searches 61 entries by actor username, moves to
  26–50, preserves a typed decision reason during history paging and keyboard Enter/Space
  collapse/reopen. Saving that synthetic reason increments the decision revision to 2
  and total history to 62 while preserving the filtered page. A fresh document restores
  that searched page. Independent evidence search remains after navigating to 51–61,
  closing the detail and using Back. Capture `artifacts/v1-triage-history-bookmark.jpg`
  is visually inspected. These synthetic records represent no actual target finding.
- A one-off 503 auto-refreshed before observation, so it does not prove manual error
  recovery. A controlled persistent 503 then shows '목록 조회 실패', the actual error,
  reload control, retained search and zero displayed history rows. After removing that
  synthetic fault, the latest-list control and successful query show a genuine empty
  search result. Automatic poll may also recover after fault removal; this does not
  establish that recovery required the manual click. No prior page is presented as a
  successful new query. QA app is stopped cleanly and the tab leaves it; target traffic
  remains zero.
- Main app shuts down normally and restarts with the new API. Health and data are checked
  after restart. Full mobile/screen-reader/zoom, late-response timing races, unsaved draft
  restoration and retention/load remain unverified; broader v1 gates stay open.

## Built-in tool contracts and result admission (2026-10-04)

- New plans store selected check contracts and a process-start package Python-source
  compatibility fingerprint. Server approval and pre-Planner execution reject missing,
  changed, extra-field and bool/float-version manifests; Worker admission checks again
  before its base GET. Approval events retain the snapshot. Check outputs are validated
  in full before any finding/observation write, with JSON structure/count/size limits,
  exact finding fields/check identity, finite numbers and scoped query-free observed URLs.
  This is fixed built-in check admission, not external registration or code isolation.
- **17 new backend cases** cover independent/deterministic manifests, legacy/version/hash/
  type/field mismatch with zero requests, held-queue rejection before Planner, invalid
  second finding rejecting the entire check without marker leakage, oversized/nonfinite/
  mixed-skip/foreign observation results and valid results. Final full backend **265 tests
  pass** in 82.50 seconds with the existing Starlette/httpx warning. An earlier full run
  had one setup error because a concurrent Vite rebuild temporarily removed dist/assets;
  that run is not reported as passing. Rebuilds and final full backend verification are
  sequential thereafter.
- Two frontend contract tests cover field-order independence, selected order, missing/
  changed snapshots, versions, permissions, result budgets, method and extra fields.
  Full frontend **39 passes** and TypeScript/Vite build passes: `index-DR8T903p.js` /
  `index-fNMAZXjt.css`. New layout uses existing semantic colors; selected contrast/token
  checks pass. Actual browser review finds adjacent contract paragraphs too close;
  explicit 12px spacing is added and recaptured, with read-only bounds confirming separation.
- Isolated built UI displays old-fingerprint and legacy approval cards disabled with
  guidance, and the current card enabled. Keyboard Enter expands contract details.
  `artifacts/v1-tool-contract-stale.jpg` is captured and visually inspected. The current
  synthetic task is approved and reaches queued state; fixture submissions are deliberately
  held so target traffic stays **zero**. Clean fixture shutdown marks it stopped. The
  screenshot precedes the final extra-field UI guard, which does not alter its layout.
- Rebuilt wheel SHA-256:
  `37af81fc37ea421c079f35eee7a45e90d0d4d9b9bf297f388691253f888bbee5`.
  Installed runtime rehearsal succeeds outside checkout, exercising resource-based source
  fingerprint initialization and new-plan creation, prior auth/schema/CLI/audit/maintenance
  checks, clean shutdown and lease release with zero target requests. A first harness
  invocation omitted required CLI arguments and was corrected before successful execution.
- Final main process restarts normally, health returns 200, assets stay two and target
  traffic stays three. Contracts are compatibility data, not signed attestation or live
  code/OS/dependency measurement. Result validation does not bound producer CPU/RSS or
  automatically scrub arbitrary future evidence. UI guidance is not authorization; JSON
  numeric representation may collapse in JavaScript, while server comparison stays strict.
  Legacy pending tasks require new plans. External tool input/registration/execution
  isolation, extension review, whole mobile/readers/zoom and full v1 remain incomplete.

## Pending-plan refresh and preserved provenance (2026-10-04)

- Administrator/operator `POST /api/tasks/{id}/replan` recreates only pending plans
  using current asset revisions, execution policy and built-in contracts. Selected
  assets/checks/goal and retest/schedule links remain; current triage revision is captured.
  Source retains its snapshots, becomes rejected/replanned and links to the pending
  replacement. Both tasks and both coverage changes share one SQLite transaction;
  audit events follow separately. Same-process approval/replan locking prevents both
  actions succeeding. Repeated/concurrent requests return the existing replacement.
- Six new backend tests cover legacy snapshots and full pending capacity, current policy/
  scope/contracts, idempotent concurrency, approval races, injected SQLite rollback,
  role/anonymous/nonpending/missing/archived rejection, and retest/schedule provenance.
  Targeted related suites **52 pass**; final full backend **271 pass** in 86.40 seconds
  with the existing Starlette/httpx deprecation warning. Frontend remains **39 passing
  tests**; TypeScript/Vite build passes: `index-CoXUoKrd.js` / `index-BZKzfnn-.css`.
- Actual built desktop UI on isolated synthetic data shows a scoped first-request 503
  alert, retains the pending source, then manual retry creates exactly one pending plan.
  The fault is injected before the handler; rollback after database mutation is established
  by the separate backend trigger test, not this browser fault. Current scope is
  `https://replan-after.invalid/`, revision 2, while source remains
  `https://replan-before.invalid/`. Approval remains explicit and approved_at is null.
  Source/new detail buttons navigate both ways and old coverage displays cancelled while
  new coverage displays unexecuted. Capture `artifacts/v1-pending-plan-refresh.jpg` is
  visually inspected. QA submissions are held and target traffic stays **zero**.
- Fresh wheel SHA-256 `915afb9de59b8aa414dd16a8da61df9b8cbca402a5cdc98f46bb3388c75fd601`.
  Installed runtime outside checkout passes dependency, CLI, authentication/schema,
  asset/pending persistence, audit and backup/restore, shutdown and lease checks with
  zero target requests. This package smoke does not specifically invoke the new endpoint;
  its behavior is covered by source tests and the built UI review.
- QA server stops cleanly; main preview restarts cleanly with the new backend. Health is
  200, assets remain two and traffic remains three. No real target scan is performed.
  Whole mobile/readers/zoom, navigation during late action responses, multi-instance
  concurrency, audit/business atomicity and broader v1 release gates remain open.

## Late mutation responses and local modal ownership (2026-10-04)

- Previous turn made authoritative progress: pending-plan refresh, backend/UI evidence,
  package smoke and commit `2d5850b`. This turn reproduces two actual built-console faults:
  a delayed replan success redirects from the user's newer workspace view to approvals;
  a delayed note save closes a freshly opened note modal at the identical URL, discarding
  its unsaved draft. The fixture commits the owned mutation then explicitly holds the
  response; failure cases return controlled 503 before the handler. Each hold has a
  50-second deadline and a file-based release, with no production data or target execution.
- Navigation now maintains an in-memory visit revision, invalidated synchronously on
  route changes, Back/Forward and session-expiry events. Main local form/archive modal
  changes invalidate a separate scope. Returning to the identical URL or reopening the
  same modal cannot restore an older response's ownership. The common action runner
  reconciles successful persisted mutations regardless of current view, but returns no
  navigation result to a stale caller. Previous-view failure does not alter the current
  inline error/recovery state. Completion is still communicated through the existing
  status toast. Main forms capture the same scopes, defer navigation until reconciliation,
  preserve newer modals, and share the synchronous action-in-flight submission gate.
- Eight new native tests use controlled request/refresh promises and assert current
  success/error, late success/error, navigation during reconciliation, Back to identical
  URL and local modal replacement. Full frontend **47 tests pass** (269.26 ms); bounded
  command is `npm --prefix web test`. TypeScript/Vite build passes via
  `npm --prefix web run build`: `index-CDxDl58J.js` / unchanged `index-BZKzfnn-.css`.
  No Python or stylesheet changes; backend full-suite evidence remains the previous
  turn's 271 passes and is not reported as rerun here.
- Actual built desktop console asserts: late success retains a different task detail;
  late failure leaves its URL/detail and zero inline alerts; Back to the identical task
  retains that detail when the old success arrives; unmodified-view replan still navigates
  to approvals. At identical note URL, both delayed success and failure retain the new
  modal's title/content; failure adds no inline error to it. Normal note save closes its
  own modal and displays its stored note. Current-modal failure keeps original input and
  displays the controlled error. Synthetic successful notes each store once; failure
  stores none; target traffic remains zero. Parallel old/new mutation completions are
  inapplicable to this main runner because the shared submission gate serializes requests.
- Captures `artifacts/v1-late-action-navigation.jpg` and
  `artifacts/v1-new-draft-late-response.jpg` are visually inspected. They precede the final
  logout-button guard, which does not alter these modal layouts. These cases establish
  main-console visit ownership, not universal async safety across every separate component.
  Other component mutations, draft editing inside the same submitted modal, whole mobile/
  assistive technology, long-lived sessions and broader release criteria remain open.
- Final built-console save is held while Enter is pressed again in the title input.
  SQLite verifies exactly one note. After closing the saving modal, logout is observed
  disabled; after response release it is asserted enabled again. Logout now waits for
  a successful action result before changing local identity, and is disabled during a
  shared main action. No actual logout, session-expiry race or logout-failure browser
  sequence is performed here. QA stops normally and leaves no held request. Main preview
  stays healthy (200), assets two and target traffic three; the new UI is served without
  restarting the unchanged Python process.

## ScopeSentry file review, provenance and transactional apply (2026-10-04)

- Previous turn changes authoritative main action/modal ownership and verifies actual
  stale responses (`306670a`): progress. This turn addresses a missing integration feature.
  Original ScopeSentry export/service/model contracts are read at pinned commit
  `8203c4932795f35d741dd54871345b9eca0943a8`, including Go MongoDB ObjectID serialization.
  `asset` JSON export encodes one BSON document per line. The independent adapter supports
  only that HTTP-asset NDJSON contract; real remote authentication/paging is not implemented.
- New operator/admin preview validates UTF-8 1 MiB/100 nonempty lines, strict JSON keys/
  constants, ObjectID identity and bounded HTTP URL with no userinfo/query/fragment/control.
  Irrelevant original body/header/title/etc. are discarded before preview storage.
  Fifty actor-bound, 15-minute active previews bound temporary admission; new previews
  clear expired temporary records. Apply requires explicit IDs and permission acknowledgment.
  Entire selection checks reviewed asset/source digests before writing, then commits
  assets, source links/history, idempotent result and its import audit event in one SQLite
  transaction. Common request audit and other service mutations remain separate.
- Same URL reuses a locally configured asset; multiple IDs/instances may link to one.
  Repeated import only confirms its source. Changed original URL requires an explicit new
  reviewed link, retains old asset/scope/evidence and preserves previous source history.
  Missing rows in a partial file never delete or archive assets/sources. Source read API
  offers scoped SQL search, insertion watermark and default 25/max 100 paging with an
  asset reference index. No scan/task/approval is created by apply.
- **24 new backend cases** cover preview-only selection/privacy/no requests, concurrent
  idempotency, local metadata preservation, original address changes and pending snapshots,
  partial files, many-to-one/source identity, stale all-or-nothing conflicts, archives,
  roles/actor/anonymous binding, expiry and changed retries, source paging/search/watermark,
  admission/cleanup/audit validity, invalid URL/JSON/UTF-8/count/fields/duplicate identities.
  Injected audit-link insertion failure rolls back assets, source records, result and audit.
  Initial ScopeSentry/audit suites **44 pass**; final full backend **295 pass** in 90.97 s
  with the existing Starlette/httpx warning. Complete frontend remains **47 passes**.
- Actual built desktop console distinguishes two ready HTTP rows and one disabled TCP row,
  starts with no selected IDs, requires acknowledgment and shows create/link details.
  Controlled first apply commits then loses its response (503). UI locks the reviewed
  selection and offers same-selection result recovery. Retry returns one created asset
  and two links; SQLite remains assets 5 vs initial 4, sources 2, tasks unchanged 18,
  traffic zero. A synthetic body marker is absent from assets/previews/sources/history.
  This is committed-response-loss recovery; database rollback is the separate trigger test.
- Same original ID with a changed URL is then visibly reviewed/acknowledged in the console.
  Apply creates the new address's asset and keeps the old one; current sources remain two
  and previous-link history becomes one. Old asset's history filter displays original URL/
  ID, first/last confirmation and replacement time; explicit SHA-256 disclosure shows the
  saved file fingerprint. Source instance search displays its matching record. An initial
  keyboard disclosure attempt and immediate history toggle did not establish the intended
  state; later explicit toggle, observed checked state, click disclosure and DOM assertions
  establish the reported history/display behavior. No keyboard disclosure claim is made.
- Actual initial screenshot shows source explanatory text/search too close. Source content
  gets an explicit 12px grid gap, inherits existing semantic colors and hard borders, and
  is rebuilt/reviewed. Final TypeScript/Vite build passes: `index-78Ib1nZu.js` /
  `index-C0PcrrCO.css`. Selected semantic-token/AA pair checks pass; full rendered/mobile/
  screen-reader/zoom/touch/new modal timing QA is not claimed. Visually inspected final
  `artifacts/v1-scopesentry-provenance.jpg` shows preserved previous source and expanded
  fingerprint; its list label is during an ordinary background refresh.
- Wheel SHA-256 `0d69bf63b1a3a7a915937d9fa1893b9f38db5c41f19a453b9396c094b81056b8`.
  Installed-runtime harness now exercises actual review/apply/idempotent retry/source read
  outside checkout plus dependency/CLI/auth/schema/audit/maintenance, zero target requests,
  normal shutdown and lease release. An earlier package run precedes that harness extension;
  the final extended run is the evidence for the new API. No frontend rebuild runs during
  full backend tests or package smoke.
- QA stops cleanly, with final synthetic assets six/current sources two/history one/tasks
  eighteen and zero traffic. Main preview restarts normally with new backend; health/data
  checks follow. ScopeSentry overall release gate remains open for actual source instance,
  remote auth/paging/resume/concurrent original changes, full mobile/accessibility, larger
  file-batch journeys and history retention/load. This file adapter is not full parity.
- A final additional backup/restore regression verifies the newly introduced source/link
  history kinds and the applied preview's same-selection retry result survive an online
  snapshot/offline restore. Restored sessions are revoked, login is explicit, original
  URL/history and current source remain, retry creates no extra asset/task. That targeted
  case **1 passes** in 0.56 s. It is added after the 295-case full run; current suite has
  296 cases and is not described as a full 296-case rerun. Python service code is unchanged
  after its full run and wheel build. Main final health is 200, assets two, traffic three,
  and the served document references the final frontend bundle.


## 2026-10-04 — configured ScopeSentry JWT remote review and page recovery

- Independently reads the pinned ordinary REST JWT auth/search/asset-list contract; MCP
  API keys are distinct. New configured-only adapter requests `/api/assets/asset` with
  type/project filters and 50-row positional pages. HTTPS is default; explicit loopback
  HTTP/private flags exist solely for owned synthetic fixtures. Browser input cannot set
  source URLs, credentials, arbitrary tool names or write/scan endpoints.
- Twenty new native loopback cases validate exact endpoint/Bearer/filter/page contract,
  read-only collection and zero target traffic, private-field/token exclusion, actor-bound
  continuation, cached same-parent next-page response, empty terminal page, changed previous
  boundary, duplicate IDs, rotated credentials, provider 401/403/302/500 recovery, malformed/
  oversized responses, missing IDs, deadline/admission/role/config rejection, and rollback
  of next pointer plus preview when a SQLite trigger rejects the child. Targeted **20 pass**
  in 11.25 s; prior file tests **25 pass**. Full backend **316 pass** in 102.18 s, frontend
  **47 pass**. No Python service edits or frontend rebuild during the full backend run.
- Real console QA uses a separate loopback REST fixture (8813), QA app (8811), and dedicated
  synthetic administrator. Page 1 has 50 rows; no rows are preselected. A fixture 401 on
  continuation visibly retains the console session and page 1. Next successful continuation
  rechecks page 1 and saves page 2, but the QA middleware returns a synthetic 503 **after
  commit**. The same visible button restores saved page 2 without another source request.
  Exactly four source requests occur: first page, failed boundary request, successful
  boundary request, second page. No real ScopeSentry instance is contacted.
- Page 2 contains one row. Explicit select-all/authorization/apply produces one new asset
  and one source link. QA database assets grow 6→7, source links 2→3, tasks remain 18,
  target traffic remains zero. The fixture body marker and JWT are absent from stored
  records. Page 1 is intentionally skipped without reflection; this is not a complete
  import of every remote asset.
- Final visual review finds generic text-input styling enlarging the radio selector. A
  scoped 20px radio rule and wrapping source label fix it. Rebuild and fresh-document
  screenshot are viewed: `artifacts/v1-scopesentry-remote.jpg` shows the selected configured
  connection, visible focus outline, and enabled first-page button. Final build is
  `index-OQwQHPR-.js` / `index-B5ysGB7c.css`. Selected token/AA pair checker passes; full
  mobile, touch, screen reader, zoom, and connection-list error recovery are not claimed.
- Wheel SHA-256 `48375e478cf2079dfbb129facdb209055248f9497338f07aa06ba79bfb536eba`.
  Initial no-build-isolation attempt fails because this development environment lacks
  `bdist_wheel`; normal isolated build succeeds. Outside-checkout locked-runtime rehearsal
  passes, including remote configuration listing and refusal of an unconfigured connection,
  existing file review/apply/retry/source reads, CLI/auth/schema/audit/backup/restore,
  zero target requests, normal shutdown and lease release. It runs again with final CSS/UI.
  It does not exercise a TLS ScopeSentry source or remote paging inside the installed wheel;
  native loopback tests and desktop QA supply the remote paging evidence.
- Provider positional pagination has no snapshot/cursor: previous-boundary checks and ID
  deduplication cannot guarantee whole-source consistency or eliminate all concurrent-change
  omissions. First-page requests are not idempotent, and TTL/admission limits remain shared
  with file previews. Real source deployment/TLS/JWT issuance and expiry, long imports,
  history retention/load and full accessibility remain open. Overall ScopeSentry/v1 gates
  stay unchecked.
- QA app and owned source server stop normally. Main preview restarts with the new
  backend and final bundle; health is 200, original assets remain two and traffic three.


## 2026-10-04 — source TLS/JWT lifecycle and connection-list recovery

- Five new native source cases use a real owned HTTPS server and generated local
  certificate. A trusted IP SAN certificate succeeds through the configured base path;
  an untrusted certificate and trusted but mismatched SAN certificate each return local
  502 before the server observes any HTTP Authorization request. Default private-address
  refusal likewise produces no source HTTP request or preview. No TLS verification bypass
  is added to the product.
- The fixture issues HS256 JWTs and checks signatures plus expiry against a controlled
  source clock. Moving that clock beyond exp makes continuation fail without advancing
  its saved parent. Wrong-signature JWTs fail. Correct renewal makes old continuation
  contract return 409 before a source request, and a fresh collection succeeds. A genuine
  app/lifespan/workspace-lease restart then resumes the current collection and returns
  the same cached next preview on retry, without duplicate source requests. Assets,
  tasks and target traffic stay zero. This is a synthetic provider, not an actual
  deployed ScopeSentry JWT issuance/permission integration.
- Initial targeted **5 pass** in 3.78 s; full backend **321 pass** in 105.72 s; frontend
  **47 pass**, TypeScript/Vite build passes. After the full run, the fixture assertions
  additionally require exact Bearer/HS256 and exclude all issued JWT strings from persisted
  previews. Those strengthened five cases pass again in 3.86 s; the entire 321-case run
  is not repeated after this test-only assertion strengthening. Service Python is unchanged.
- Connection loader now separates loading/error/empty/success, supports explicit refresh/
  retry, guards completion by current AbortController and mounted instance, and aborts
  on close. List errors/loading disable remote requests and preserve file drafts. A
  successful refresh clears a removed or unconfigured selected connection; newly enabled
  sources still require explicit selection. Source page buttons require a current selection.
- Actual desktop console on isolated QA app 8811 receives synthetic list 503, then a held
  successful response. Error is distinct from empty state; retry shows loading with both
  refresh and first-page buttons disabled. Release restores the configured list, selecting
  its radio enables first-page lookup, and switching back to file mode shows the original
  `draft-preserved` identifier and NDJSON text. A DOM value-attribute probe on textarea is
  null (not proof); the visible DOM snapshot is the evidence for restored text.
- A held error refresh is closed; reopened modal fetches a successful list after gate
  release and displays no old error. Further QA metadata changes exercise selected source
  removal (empty message, first-page disabled), missing server credential (radio disabled),
  and restored credential (radio enabled, first-page still disabled until explicit choice).
  These are controlled fixture configuration changes; production configuration reload is
  not implemented. No remote page or target request is made in this metadata-only journey.
- Final viewed `artifacts/v1-scopesentry-list-recovery.jpg` shows the new refresh button,
  selected radio/focus outline, source label and enabled first-page button. Final bundle
  `index-DnMVWxb_.js` / `index-B5ysGB7c.css`; selected semantic token/AA checks pass. No full
  screen reader, touch, mobile or whole UI concurrency claim is made.
- Reuses previous wheel SHA-256
  `48375e478cf2079dfbb129facdb209055248f9497338f07aa06ba79bfb536eba`: byte comparison confirms
  all 36 packaged Python sources exactly match current service files. Installed runtime
  outside checkout with final frontend passes locked dependencies, CLI/auth/schema,
  file import/retry/source, empty remote listing/unconfigured-source refusal, audit and
  backup/restore/shutdown/lease checks, zero target requests. TLS paging evidence remains
  the new native fixtures, not the installed-runtime harness.
- QA stops normally; its existing assets seven/source links three/tasks eighteen/traffic
  zero remain unchanged. Main stays live without unnecessary backend restart; health 200,
  assets two/tasks four/traffic three, served document references final bundle. Actual
  source deployment, whole positional-source consistency, larger imports/retention, other
  v1 integration and UX gates remain open.


## 2026-10-04 — native radio modal focus boundaries

- Production Modal's last native radio group reproduces a keyboard trap failure in the
  no-API fixture: with first radio checked, Tab leaves document BODY focused, outside
  the dialog. Every radio's DOM tabIndex is zero, while the native group has one Tab
  stop; the old last-element comparison incorrectly selected the trailing unchecked
  radio as its boundary. This is an actual browser reproduction before service UI edit,
  not a synthetic DOM assertion or a claim that a current workspace screen ends in radios.
- Focus candidate filtering now picks the focused/checked member or direction-specific
  unselected entry within each name/form/tree group. It preserves native arrow-key and
  checked behavior and the existing disabled/hidden/negative-tabindex filters. The
  boundary list is recalculated on every Tab. References are the
  [W3C modal](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) and
  [radio group](https://www.w3.org/WAI/ARIA/apg/patterns/radio/) keyboard guidance.
- Real production-component fixture after reload proves checked first and arrow-selected
  second each Tab-wrap to Close; reverse Tab returns to the checked member. Unselected
  reverse entry reaches third without checking it, then Tab wraps. Fresh-document forward
  entry reaches first; reverse Tab returns to summary. A previously visited unselected
  group can remember its last member on native entry; containment/selection are asserted
  without forcing a remembered group back to first. An inspection initially attempted
  `instanceof HTMLInputElement` in the browser evaluation sandbox, which is unavailable;
  subsequent read-only DOM inspection of type/checked/labels establishes the reported
  focus, without altering app state.
- Same-name groups owned by different forms remain independent: reverse from Close
  reaches the trailing checked member, another reverse reaches separate form's checked
  member, and forward returns through trailing member to Close. A disabled fieldset and
  negative-tabindex control remain skipped on the fresh forward sequence. Existing final
  scroll region receives reverse Tab, ArrowDown moves scrollTop to 40, and Tab returns
  to Close.
- Parent tick advances from 0 to 61 while focus stays on selected second radio. Escape
  closes with recorded close tick 61/current 61, restores opener, and clears body overflow
  lock. This proves callback freshness in this fixture; full nesting/assistive technology
  and every component's asynchronous state are not covered.
- New fixture wrapper measures actual iframe documents, not CSS scaling/device emulation.
  Three synthetic long source labels use the production Modal/stylesheet. At 320/390/768,
  root scrollWidth equals clientWidth (320/390/768); dialog scrollWidth equals clientWidth
  (277/347/621). Dialog bounds fit each viewport: 12–308, 12–378, 64–704.
  Vertical content heights 2193/1740/1046 exceed client heights 789/789/756 and show native
  vertical scrollbar. Viewed `artifacts/v1-modal-radio-320.jpg` confirms narrow wrapping,
  readable header/close, selected radio and scrollbar. This does not prove touch, zoom,
  screen reader, bottom-content reachability on actual phones or all product dialogs.
- Frontend **47 pass**, TypeScript/Vite production build passes: `index-DAehDeWO.js` /
  `index-B5ysGB7c.css`. The new DOM regression is manual fixture coverage, not part of
  those 47 Node tests. Selected Montage semantic-token/AA checks pass. No Python service
  change; no repeat full backend suite is claimed. Browser fixtures stay outside the
  production Vite entry and make no API or target requests.
- Installed runtime outside checkout uses the unchanged prior wheel SHA-256
  `48375e478cf2079dfbb129facdb209055248f9497338f07aa06ba79bfb536eba` plus newly built UI.
  Dependency/CLI/auth/schema/file-import/remote-refusal/audit/backup/restore/clean-shutdown
  checks pass with zero target requests. Main preview health/bundle check follows; full
  v1 accessibility/visual/remote integration gates remain open.
- Vite's manual fixture uses page reload when its Fast Refresh export check declines a
  fixture update; all reported final keyboard checks start from explicit fresh navigation.
  QA Vite stops, main remains live: health 200, final bundle references match, assets two/
  tasks four/traffic three unchanged. No production backend restart was required.


## 2026-10-04 — finding triage late replies and assignee recovery

- Code review finds FindingTriage always invoking a parent success callback after unmount;
  the parent compares finding ID but not screen visit. Reopening the same ID makes the
  old acknowledgement update its selectedFinding and revision key, remounting the fresh
  form with old submitted content. Save now captures the existing action-view guard,
  checks mounted state, and reports current/stale to parent. Both acknowledgements notify
  global lists/overview; only current acknowledgement updates the local finding. Stale
  success shows a completion notice; stale failure cannot enter the new form's local alert.
- Initial rapid UI sequences lack a proven live-node input boundary. One apparent reset
  happens before releasing the failed request; it cannot be attributed to that response.
  Exorcist diagnosis adds owned-QA-only visible DOM node/input-event tracing and GET/PATCH
  start/completion logs. The attempted new input is absent from the live node's input
  trace; after explicitly observing the new dialog DOM, the input event is recorded on
  the new node and remains. No cache/React timing cause is inferred, and these unmatched
  early probes are not the evidence for the fix. `artifacts/triage-live-input-trace.json`
  records the distinction. The observer reads only synthetic dialog textareas; it is not
  in product sources or bundle and never reads login inputs.
- To obtain actual before/after evidence, archive commit 87c1557's web sources into
  `artifacts/triage-before-code`, reuse current locked node_modules, and build separately.
  Owned QA server alone uses that directory via AEGIS_WEB_DIR; main preview retains current
  UI. With PATCH held before persistence, close/reopen same finding, observe fresh DOM,
  type `verified-before-new`, and confirm that live value before releasing. Original
  200 response then replaces it with `verified-before-old`. Recorded trace is
  `artifacts/triage-before-verified-trace.json`.
- Restart only QA server with final frontend and repeat the same verified live-input
  sequence. `verified-after-new` remains after old 200 acknowledgement; visible completion
  notice confirms the original save. `artifacts/triage-after-verified-trace.json` records
  this. Repeat with held 503: `verified-failure-new` is observed before and after release,
  new dialog alerts are empty; `artifacts/triage-failure-verified-trace.json`. Synthetic
  source requests are bounded by the QA's 45-second hold deadline. Engine submissions
  are held Futures; no validation/target action is created.
- Current-view stale revision yields existing 409 and keeps new draft. Explicit latest
  record recovery replaces it with server state, matching the visible warning. A current
  synthetic 503 leaves inputs enabled and `current-failure-draft` intact; normal retry
  later saves it. Backend revision advances 2→7 over five deliberately changed successful
  QA writes (including isolated before/after comparisons); conflicts and failures add
  no successful write. This is not an automatic draft merge or saved draft across closing.
- Assignee listing now distinguishes loading/error/total, disables stale selection/page
  controls and offers same-query retry. Actual 503 on search `remote` preserves search
  and resolution draft; selection is disabled and count says unconfirmed. Retry returns
  one matching account while both inputs remain; unrelated save error is not cleared.
  Final viewed `artifacts/v1-triage-directory-recovery.jpg` has no diagnostic overlay and
  shows error/retry alongside preserved `directory-recovery-draft`. Selected semantic
  token/AA checker passes; no full narrow-width/touch/screen-reader directory claim.
- Frontend **47 pass**, TypeScript/Vite builds pass, final `index-Bo6cqMOR.js` /
  `index-B5ysGB7c.css`. Native UI comparison supplies component-specific evidence; the
  Node tests are existing helper/guard coverage. Final formatting-only rebuild follows
  the 47-case run. No Python service edit or full backend rerun is claimed.
- Unchanged wheel SHA-256 `48375e478cf2079dfbb129facdb209055248f9497338f07aa06ba79bfb536eba`
  with final UI passes outside-checkout installed dependency/CLI/auth/schema/import/
  remote-refusal/audit/backup/restore/shutdown/lease rehearsal, target requests zero.
  Main and QA health/data checks follow. Chat-specific late navigation and other component
  asynchronous flows remain part of the open full v1 UX gate.
- QA stops normally. Main health 200 and final bundle names match; main assets two/tasks
  four/traffic three remain unchanged. QA assets seven/tasks eighteen/target traffic zero
  remain unchanged; only explicitly exercised synthetic triage records/user metadata change.


## 2026-10-04 — late chat replies preserve changed navigation

- Owned synthetic response-after-commit fixture holds only task-message POST replies;
  it writes the real question/answer pair before delaying HTTP 200 or replacing the
  reply with 503. No target checks execute. Before the fix, sending
  `chat-before-late-search`, then changing the live search to `북마크 기록 050`,
  loses that search and URL on acknowledgment. Both the live value and URL were
  observed before release. After the fix, that search remains and the global
  prior-question saved notice is observed. Closing the chat preserves its folded
  state and search URL on late success.
- A committed 503 after changing search to `북마크 기록 049` keeps that search,
  editable pending question and no local error from the earlier view. Explicit
  same-question retry returns the stored reply: task-message count remains 71 and
  the matching question occurs once. These are native browser/manual observations,
  separate from the existing 47 helper tests.
- Intermediate review exposed a second issue: generic record reload/global mutation
  notification discarded the old-page snapshot despite retaining offset 25. Chat
  acknowledgment now refreshes workspace summary without resetting unrelated
  record snapshots, and only reloads chat when the originating view is current.
  Final build `index-DPpjUbjJ.js` / `index-B5ysGB7c.css` preserves exact
  `task_chat_offset=25&task_chat_snapshot=190` through a held successful reply.
  The visible range remains 26–50 of the original 73-message snapshot. A normal
  current-view submission then returns to latest 1–25 of 77, with no offset/snapshot
  query. Final search-plus-collapse review retains its exact folded q050 URL.
- Closing task detail before successful acknowledgment leaves the task list open.
  Reopening after completion does not restore unconfirmed intent; explicitly
  unfolding chat shows an empty question and no recovery prompt. The ephemeral
  close-case toast was not independently captured; the earlier stale-search toast
  was. Request-ID guarded storage clearing runs even after unmount, without
  clearing a newer intent. An already remounted panel's local restored intent is
  not automatically synchronized; same-ID retry remains available.
- Synthetic task messages progress 63→81 across nine distinct submissions, including
  before-fix and intermediate diagnostic submissions; retries add no pair. Final
  QA assets seven/tasks eighteen/target traffic zero remain unchanged. Screenshot
  `artifacts/v1-chat-late-navigation.jpg` is saved and visually reviewed: retained
  search, one matching message, empty question, saved status and visible focus ring.
  This is desktop evidence, not full mobile/accessibility/soak coverage.
- Final frontend build and 47 existing Node tests pass. Selected Montage contrast
  pairs pass the design script; whole rendered accessibility audit remains open.
  No Python service edit or full backend rerun is claimed. Unchanged wheel SHA-256
  `48375e478cf2079dfbb129facdb209055248f9497338f07aa06ba79bfb536eba` with final
  UI passes outside-checkout installed runtime/dependency/auth/schema/import/remote
  refusal/audit/backup/restore/clean shutdown and lease checks; target requests zero.
  Main health is 200, served bundle matches, assets two/tasks four/traffic three
  remain unchanged. Owned QA is stopped normally; main preview stays live.


## 2026-10-04 — stale unauthorized replies do not expire a newer session

- Before fix, the real `api()` module starts a deferred overview request, completes
  synthetic login, then receives the old 401. A controlled-response test fails
  because it dispatches `aegis-session-expired` against the newer session. The same
  test passes after adding a browser-document session revision captured at request
  start. No cookie contents are read. Successful login/setup/logout/password response
  headers advance the revision, even if parsing the success body fails. Current
  unauthorized expiration advances it once, so sibling old requests cannot repeat
  the event. An aborted request does not trigger expiration after a late body.
- Eight new API/session tests exercise the actual API and download helpers: late
  401 after login; one expiration for concurrent old requests and another after
  re-login; failed login/status reads do not invalidate current requests; successful
  logout/password/setup; 401 body decode held across login; late aborted body;
  held report HTTP error with newer session; malformed successful auth body. Final
  frontend suite is **55 passed** (47 existing plus eight), with build success.
  Report component captures the same session at initiation and uses the shared
  guarded expiration helper; unrelated local errors still return to their callers.
- Rerunnable native browser fixture `web/tests/browser/api-session-review.html`
  imports production `api` and `ReportDownload`. Its own fetch stub delays only
  synthetic responses and performs no real login/cookie or target request. Browser
  clicks show late API 401 after new login leaves expiration count zero; late report
  401 after another login also leaves zero, while retaining its visible error/retry
  control. Current API 401 increments to one; after re-login, current report 401
  increments to two. Snapshot and screenshot `artifacts/v1-api-session-review.jpg`
  are inspected. This is real browser event/component evidence with synthetic
  transport, not real multi-account/cookie races or cross-tab session proof.
- Final assets are `index-C64hz38T.js` / `index-B5ysGB7c.css`. Unchanged wheel
  SHA-256 `48375e478cf2079dfbb129facdb209055248f9497338f07aa06ba79bfb536eba`
  with this UI passes outside-checkout installed runtime/dependency/CLI/auth/schema/
  import/remote-refusal/audit/backup/restore/shutdown/lease rehearsal, target requests
  zero. Python service code is unchanged; no full backend suite rerun is claimed.
  Main health 200, final bundle served, assets two/tasks four/traffic three unchanged.
  Browser fixture server stops normally and main preview remains live.
- Revision is document-local response-order protection, not a server permission
  boundary or cross-tab synchronization. Generic successful replies are not filtered
  by this change. Full authentication transition/data-isolation UX remains open.


## 2026-10-04 — stale successful reads and downloads across session changes

- Two failing-before controlled-response tests show that the actual API returns an
  old successful overview after another login and returns old identity when its JSON
  body finishes after login. Both now reject with AbortError. GET success checks the
  captured session and abort signal before JSON interpretation and after its awaited
  completion. Successful POST/PATCH acknowledgments retain their existing semantics
  so a committed action can still be reconciled; this is not blanket mutation-response
  cancellation. Current reads return normally.
- Four new tests cover held successful read across login, held identity JSON body,
  current reads plus old committed POST acknowledgment, and aborted successful body.
  Final suite **59 passed** (55 prior plus four). Build succeeds. Main overview refresh
  and initial/retry identity loaders additionally ignore old-session success/error.
  The unauthenticated transition invalidates refresh sequence and clears summary,
  tools/settings, task/detail/finding/traffic/edit selections and old error/toast state.
  These main cleanup branches are source/type-check evidence, not a complete native
  multi-account UI transition rehearsal.
- Production ReportDownload now checks the captured session before creating the Blob
  URL/save anchor and before handling local failures. Extended native browser fixture
  imports actual API/ReportDownload but stubs synthetic transport. A previous GET 200
  after new login reports canceled old read, never successful old data. A current read
  succeeds. A report 200 after new login leaves file-save-path count zero and no saved
  status; current-session report 200 increments to one and shows download-started.
  Previous-session report 401 after login leaves no alert/countdown/expiration, with
  file count unchanged. This supersedes the prior fixture's stale-error display claim.
  The helper still returns its HTTP error; the component discards the stale local UI.
- Fixture wraps createObjectURL to count the real component save path and replaces
  anchor click with a no-op, so no Downloads file is created. Screenshot
  `artifacts/v1-session-read-isolation.jpg` is inspected. Fixture endpoints/login are
  synthetic and do not touch real cookies, target services or production records.
  Cross-tab transitions and full mutation-callback isolation remain open.
- Final assets `index-hbwyEmNd.js` / `index-B5ysGB7c.css`; main health 200 and exact
  final assets served, assets two/tasks four/traffic three unchanged. Browser fixture
  server stops; main preview stays live. No Python source edit/full backend rerun.
  Unchanged wheel SHA-256
  `48375e478cf2079dfbb129facdb209055248f9497338f07aa06ba79bfb536eba`
  with final UI passes outside-checkout installed runtime/dependency/CLI/auth/schema/
  import/remote-refusal/audit/backup/restore/shutdown/lease rehearsal, target requests zero.


## 2026-10-04 — identity callbacks and stale authentication changes

- Native production PasswordPanel with synthetic fetch reproduces a prior password
  success callback after the panel has unmounted and a new login remounts it: before
  release, callback count zero on generation two; after old HTTP 200, count one.
  This callback is what App uses to leave its authenticated screen. The fixture
  uses synthetic passwords/accounts and no actual cookie or server credential.
- API controlled-response regression also fails before fix: held password success
  after a newer login resolves rather than rejecting. Authentication changes now
  reject stale successful headers before advancing the browser session revision.
  Current auth changes advance once and capture the completion session; a body
  finishing after another login cannot complete the older transition. Generic
  committed mutation acknowledgment behavior remains unchanged.
- PasswordPanel ignores callbacks/errors after unmount and guards duplicate submit
  with a ref. UserPanel captures the initiating session, checks mount/session before
  closing forms/notices/reloading/session callbacks, guards duplicate submits, and
  guards user-list success/failure/loading by mount/session/request sequence. Current
  self role/state/password reset invokes guarded shared expiration, invalidating
  outstanding old reads before its explicit session-change callback.
- Two added actual API tests cover old auth success headers after login and auth
  body finishing after newer login; final Node suite **61 passed** (59 prior plus
  two), frontend build passes. Native fixture
  `web/tests/browser/identity-session-review.html` uses production identity panels.
  Click a five-second remount/login reservation before opening/submitting a modal,
  then release its held response after the reservation: background controls correctly
  remain inert while the modal is mounted. After fix, previous password completion
  across new login leaves callback count zero; previous self-reset completion across
  panel remount also leaves zero. The latter is after-fix evidence, not a separately
  executed old-build comparison. Busy text is observed before each remount.
- Current PasswordPanel success still calls onChanged once. A subsequent current
  synthetic 503 shows its local alert, re-enables new-password input and leaves
  callback count one. Screenshot `artifacts/v1-identity-session-recovery.jpg` is
  saved and visually inspected, passwords masked. No actual credential is used.
  Current self-role/reset callback branches are code evidence here, not native
  production-server cookie/revocation proof. Cross-tab/Set-Cookie races and whole
  authentication transition coverage remain open.
- Final frontend assets `index-dMpWcS3T.js` / `index-B5ysGB7c.css` served by main;
  health 200, assets two/tasks four/traffic three unchanged. Synthetic identity
  transport touches no real records or target service. Owned Vite fixture stops;
  main preview remains live. Python code unchanged, no full backend rerun claimed.
  Unchanged wheel SHA-256
  `48375e478cf2079dfbb129facdb209055248f9497338f07aa06ba79bfb536eba`
  with final UI passes outside-checkout installed runtime/dependency/CLI/auth/schema/
  import/remote-refusal/audit/backup/restore/shutdown/lease rehearsal, target requests zero.


## 2026-10-04 — policy editor error descriptions and narrow documents

- Before change, invalid schema has visible alert/custom validity but its textarea
  has no aria-invalid or aria-describedby. Production PolicyRulesEditor now gives
  schema and rule-array JSON textareas error state plus unique useId help/error
  references. Failed mode-switch buttons describe the warning; the JSON textarea
  also describes it when applicable. Credential-environment input describes the
  existing no-secret/environment-name instruction. Alerts use the existing shared
  Montage negative background/ink border style, preserving text and native validation.
- Native standalone owned form fixture imports the real editor, never calls any API.
  Invalid schema submit leaves synthetic submit count zero and focuses its textarea;
  DOM reads show aria-invalid true and both existing help and rendered error text.
  JSON mode switch with that invalid schema keeps form mode and links both mode
  buttons to the switch alert. Apply example, switch to JSON, enter malformed JSON
  and press Enter on save: count stays zero, focus moves to invalid textarea with
  intro/final-validation help/error references. Repair to [] and press Enter: count
  becomes one, aria-invalid false, alert count zero. These are native manual checks,
  separate from the unchanged **61 passing** Node helper tests.
- Extended iframe fixture's schema_error query supplies an owned JSON object above
  the 16 KiB canonical UTF-8 bound; the alert is present in the frame DOM. Actual
  iframe viewport 320/390/768 measures document client/scroll widths respectively
  305/305, 375/375 and 753/753 (15px vertical scrollbar), no outside/contained
  horizontal overflow. This is real narrow-document layout, not actual mobile
  touch/zoom/browser or whole asset registration rehearsal. The iframe's scrolling
  error below the initial screenshot fold is not claimed visually reached at 320.
- `artifacts/v1-policy-error-320.jpg` records/reviews the narrow top-form layout;
  `artifacts/v1-policy-json-error.jpg` separately records/reviews the desktop JSON
  alert/focus outline/save-blocked state. Fixture reload after source edits reset
  its prior mode, so a fresh DOM snapshot and explicit mode selection precede the
  final screenshot. No cache or production-state defect is inferred from that reset.
- Final build `index-CL9bPnqI.js` / `index-B5ysGB7c.css` passes. Selected contrast
  pairs pass the design script; real screen-reader output/full rendered audit remain
  open. No Python source edit or full backend rerun. Unchanged wheel SHA-256
  `48375e478cf2079dfbb129facdb209055248f9497338f07aa06ba79bfb536eba` with final
  UI passes outside-checkout installed runtime/dependency/CLI/auth/schema/import/
  remote-refusal/audit/backup/restore/shutdown/lease rehearsal, target requests zero.
  Main health 200 and final bundle served, assets two/tasks four/traffic three
  unchanged. Owned fixture server stops and main preview remains live.


## 2026-10-04 — owned read/export resource-load rehearsal

- New `scripts/review_resource_load.py` creates an isolated temporary workspace,
  passes a bound loopback socket to the actual AegisServer, seeds 1,000 owned
  synthetic assets and 1,000 findings, authenticates with a synthetic password and
  runs four clients over paginated assets, overview, runtime and full JSON reports.
  AEGIS environment settings are removed. No tasks are created/approved/executed,
  and target-request counter/traffic count remain zero. Runtime service code is
  unchanged. This is actual HTTP/SQLite/streamed-export resource evidence, not an
  installed-wheel run or real target/LLM/authentication-failure load.
- Initial harness mistakes are corrected before the successful load: Uvicorn can
  exit -15 after completing lifespan, so both shutdown marker and actual lease
  reacquisition are required instead of exit 0 alone. JSON report has findings/
  tasks/evidence/history/coverage/traffic rather than assets; the erroneous assets
  assertion caused KeyError failures in a diagnostic run. Synthetic findings are
  added so the export workload verifies a full 1,000-row report instead of an empty
  report. These were harness faults, not production endpoint failures.
- Successful five-second smoke precedes the 60-second run. Actual duration 60.028s,
  **3,289** requests: assets 822 HTTP 200, runtime 822 HTTP 200, overview 823 HTTP
  200, exports 434 HTTP 200 plus 388 expected slot-limit HTTP 429 with positive
  Retry-After. Unexpected failures zero. Final server exports started/completed
  434, rejected 388, active/cancelled/timed-out/failed zero. Assets/findings each
  1,000 and tasks/traffic zero remain after clean lifespan shutdown/lease reacquisition.
- On darwin, RSS KiB baseline **62,192**, sampled peak **77,552**, final **62,704**
  (about 60.73/75.73/61.23 MiB). Thirty two-second resource samples are retained.
  Child CPU during load 68.66s, which is cumulative across process threads and can
  exceed elapsed wall time. Last 2,000 successful/expected-admission responses:
  p50 5.345ms, p95 212.024ms. These are mixed-route local measurements, not per-route
  or all-request latency percentiles/SLOs. `/proc` FD counts are unavailable on macOS.
  Raw local evidence: `artifacts/resource-load-60s.json`. Source SHA-256
  `65487a3e60dddcfd238ba87d6d8a9d91d2331684c403915d250946f0736cf8d8`.
- After metadata-only output additions, final five-second smoke passes with 280
  requests, 39 completed exports, 32 expected 429, no unexpected failures, counts
  preserved and shutdown/lease verified. Final output records Python 3.11.6/arm64,
  SQLite 3.44.0, FastAPI 0.142.2, Starlette 1.7.0, Uvicorn 0.54.0, AnyIO 4.15.1,
  httpx 0.28.1. Final fixture-count fields specify exactly assets/findings/tasks/traffic.
  Sixty-second run predates these metadata-only result-field additions; workload
  and runtime service code are unchanged. Final smoke evidence is
  `artifacts/resource-load-final-smoke.json`. Compilation and CLI help succeed.
- Duration/client/seed bounds and bounded 2,000-latency/1,000-sample buffers keep
  the harness's reporting history finite. No hard memory/latency budget is enforced;
  sampling can miss transient peaks and parent client memory is excluded. One-minute
  rehearsal does not prove leak-free or long-duration/production performance, disk
  retention, slow consumers, many SSE clients, network failures or actual execution
  workloads. The full v1 resource/soak gate stays open, with instructions in
  `docs/RESOURCE-LOAD.md`. No full backend or frontend suite rerun is claimed for
  this scripts/docs-only change. Main preview health/data verification follows.


## 2026-10-04 — open event streams during load, rollover and shutdown

- Resource harness adds bounded optional `--sse-clients` 0–32, default zero. Each
  owned authenticated HTTP stream verifies SSE media type, receives a first line,
  reads IDs/JSON/heartbeat without retaining payload, and reconnects immediately
  after natural EOF with the last cursor. It does not simulate the product UI's
  three-second reconnect wait. At shutdown it requires the configured number of
  streams still open; SIGTERM must yield normal EOF and joined client threads.
  Stream transport/JSON errors fail the run; marker/lease checks remain required.
  Initial indentation caught by compilation is corrected before server execution.
- Five-second smoke with four streams plus four read/export clients, 1,000 assets
  and 1,000 findings: 282 read/export requests, no unexpected failures; four streams
  open before shutdown, four normal EOF, four data messages, forty heartbeats, zero
  stream errors. Shutdown/client cleanup 0.535s, clean lifespan/lease, target zero.
  Evidence `artifacts/resource-sse-smoke.json`.
- Sixty-second run: actual 60.130s, **3,321** read/export requests (assets/runtime/
  overview each 830 HTTP 200, exports 434 HTTP 200 plus 397 expected admission
  HTTP 429). Unexpected failures zero. Four stream readers open eight HTTP streams
  total, reconnect four times at natural lifetime rollover, receive four data messages
  and 476 heartbeats. Four are open just before SIGTERM; all four reach normal EOF,
  active ends zero, errors zero. Shutdown/client cleanup 0.140s; lifespan completes
  and workspace lease can be reacquired. Final report slots zero, all 434 admitted
  exports complete, rejected 397, failed/cancelled/timed-out zero. Counts of assets/
  findings each 1,000 and tasks/traffic zero are preserved; target requests zero.
- Child RSS KiB baseline 62,224 / sampled peak 77,712 / final 70,528 (about
  60.77/75.89/68.88 MiB); thirty samples, CPU load time 68.83s. Last 2,000 mixed
  normal/admission replies p50 5.263ms / p95 210.412ms. These are observations,
  not a no-leak or resource-SLO proof. Evidence `artifacts/resource-sse-60s.json`;
  service source SHA-256 remains
  `65487a3e60dddcfd238ba87d6d8a9d91d2331684c403915d250946f0736cf8d8`.
- Default no-SSE regression with one client, 25 assets/findings and two seconds
  passes: 49 requests, zero errors, no stream counters, 12 reports complete, clean
  shutdown/lease. It overlapped the beginning of the 60-second run on this host,
  so these timings are not an isolated comparison benchmark. Final CLI rejects
  sse-clients 33 with exit 2 before producing an output file. Compile and diff checks
  pass. Runtime/frontend service source is unchanged; no full backend/frontend or
  wheel reinstall rerun is claimed for this scripts/docs-only change.
- This verifies four consuming subscribers, one normal rollover and loaded graceful
  shutdown in an owned loopback scenario. It does not cover stalled consumers,
  session revocation/expiry under load, many subscribers, real mobile EventSource
  recovery, network failure, actual targets/LLM or extended soak. The v1 gate stays
  open. Main health 200 and assets two/tasks four/traffic three remain unchanged;
  owned child servers exit, main preview remains live.


## 2026-10-04 — logout revokes live event streams without revoking another login

- Resource harness adds `--revoke-stream-session`, requiring nonzero SSE clients
  and duration at least two seconds. It creates a separate synthetic login for
  the stream clients, leaves original-login read/export workers active, and invokes
  real HTTP logout on the stream session during load. Revocation is scheduled at
  min(half duration, ten seconds), before the normal approximately thirty-second
  stream lifetime could otherwise make EOF appear to prove revocation. Normal
  lifetime rollover and SIGTERM cleanup remain separate scenarios.
- Five-second initial revocation smoke passes with four streams and four workers:
  all four open at logout, all reach normal EOF as revoked (not shutdown), old
  cookie reconnect returns 401, old auth status false, original login auth true.
  Close/probes complete in 0.513s; 109 worker replies complete after the phase
  checkpoint. Unexpected failures zero, target requests zero, fixture counts and
  clean shutdown/lease preserved. Evidence
  `artifacts/resource-stream-revocation-smoke.json`; this precedes the final early-
  revocation scheduling/result-field refinement.
- Final twenty-second run, 1,000 assets/1,000 findings, four workers/four streams:
  1,123 read/export replies (assets 280, overview 280, runtime 281 HTTP 200;
  exports 146 HTTP 200/136 expected slot-limit HTTP 429). Unexpected failures
  zero. Four streams are open at logout and close normally as revoked; zero natural
  reconnects/stream errors, old reconnect 401, old auth false, original auth true.
  After the revocation checkpoint, **567** worker replies complete, including
  expected admission rejections; these are not all successful report payloads.
  Revocation EOF plus probe checks take 0.039s in this run, not a universal deadline.
  Final server shutdown cleanup 0.143s, no streams left open. Target requests zero;
  assets/findings each 1,000, tasks/traffic zero, lifespan and lease checks pass.
- Twenty-second child RSS KiB baseline 62,464/peak 75,616/final 75,616, CPU
  22.69s, last 1,123 mixed normal/admission responses p50 5.245ms/p95 211.188ms.
  Sampled local observations do not establish memory stability or latency SLOs.
  Raw evidence `artifacts/resource-stream-revocation-20s.json`; service source SHA
  `65487a3e60dddcfd238ba87d6d8a9d91d2331684c403915d250946f0736cf8d8` unchanged.
- Final non-revocation regression with two streams, one worker, 25 assets/findings
  and three seconds also passes: 63 replies, zero errors; two streams remain open
  until SIGTERM, two shutdown EOF, zero revoked EOF, cleanup 0.199s, lease and
  counts preserved. Evidence `artifacts/resource-stream-normal-regression.json`.
  CLI rejects revocation with zero subscribers or one-second duration before output/
  server creation. Compilation and diff checks pass.
- No production runtime/frontend edit, full suite rerun or installed-wheel rerun is
  claimed for this scripts/docs-only change. This verifies one token's logout with
  a second token for the same account, not multi-user/tenant isolation, all-session
  password/role revocation, time expiry, UI/cross-tab recovery, slow subscribers,
  network partitions or cancellation of an already authorized batch. Full v1 gate
  remains open. Main health 200, assets two/tasks four/traffic three unchanged;
  owned servers stop and main preview stays live.

## 2026-10-04 — account changes revoke independent live sessions during read load

- The owned HTTP resource harness adds mutually exclusive
  `--stream-revocation logout|password|role|disable`; the existing
  `--revoke-stream-session` remains a logout alias. Account-change modes require
  at least two SSE readers and create a separate synthetic operator with two
  distinct login tokens. Readers alternate tokens; administrator read/export
  workers keep their original session. No production runtime source changes.
- Three sequential eight-second scenarios, each with 25 assets/25 findings, two
  read workers and four consuming streams, pass. Before each change all four
  connections are open; afterward four normal revoked EOFs, zero stream errors,
  zero natural rollovers, and both old tokens return stream HTTP 401 and auth
  false. The separate administrator remains authenticated and completes positive
  read/export responses after the revocation verification checkpoint.

  | Change | Regular HTTP 200 replies | Replies after checkpoint | Request-to-stream-close seconds | Additional checks |
  |---|---:|---:|---:|---|
  | Own password | 348 | 142 | 0.559 | Old password 401; new password authenticates operator |
  | Operator to viewer | 354 | 170 | 0.031 | Fresh login reports viewer; asset creation 403 |
  | Account disabled | 343 | 162 | 0.047 | Login 401; administrator directory shows disabled |

- Evidence: `artifacts/resource-account-password.json`,
  `artifacts/resource-account-role.json`, `artifacts/resource-account-disable.json`.
  All have zero target requests/unexpected failures; assets/findings each remain
  25 and tasks/traffic zero. Lifespan markers, process exit and workspace lease
  reacquisition pass. Shutdown durations respectively 0.247/0.190/0.198 seconds.
  These are observed times, not universal deadlines or resource SLOs. The current
  `closed_seconds` excludes subsequent credential/reconnect probes, unlike the
  previous logout result format. Shared result keys now use revocation rather
  than logout; documentation records the change.
- Legacy logout alias regression: three seconds, 25 assets/findings, one worker,
  two streams sharing a distinct administrator token; 62 HTTP 200 replies, two
  revoked EOFs, old-token 401, original session retained, 19 replies after
  checkpoint. Normal non-revocation regression: three seconds, one worker/two
  streams, 64 HTTP 200 replies, two open at SIGTERM/two shutdown EOFs, zero revoked
  EOFs. Both preserve counts, target requests zero and shutdown/lease checks.
  Evidence `artifacts/resource-logout-alias-regression.json` and
  `artifacts/resource-normal-account-regression.json`. These two regression runs
  overlap briefly; their timing is not an isolated comparative benchmark.
- Four invalid CLI configurations exit 2 without creating output: account change
  with one SSE reader, one-second duration, zero readers, and simultaneous alias/
  explicit modes. Compilation and diff checks pass. Source fingerprint remains
  `65487a3e60dddcfd238ba87d6d8a9d91d2331684c403915d250946f0736cf8d8`.
  No full backend/frontend suite or installed-wheel rerun is claimed for this
  scripts/docs-only change. Actual browser/cross-tab recovery, tenant isolation,
  admin password-reset path, time expiry, already-authorized batch cancellation,
  slow consumers and prolonged soak remain outside these scenarios. v1 gates
  stay open. Main preview health remains HTTP 200; owned children terminate.

## 2026-10-04 — session replacement cannot revive pending workspace mutations

- Three new runViewAction regressions fail before the change: previous-session
  success still refreshes/notifies/returns a navigation result, previous-session
  failure still notifies, and a session replaced during refresh still completes.
  After the change all 64 frontend tests pass. Same-session navigation/closed-modal
  acknowledgment and reconciliation behavior remains covered by existing tests.
- Common workspace actions capture session identity; the helper suppresses
  reconciliation and callbacks across a session change, and checks again after
  reconciliation. Main's reconcile callback guards records-changed after refresh.
  Registration forms similarly guard post-mutation refresh, notifications, close,
  navigation and errors. General API mutation acknowledgments remain available.
  Each pending main action/form owns a unique lock; the unauthenticated transition
  releases it, and an old finally cannot release a newer action's lock. Logout now
  invokes the guarded auth API directly and transitions to Login, avoiding reads
  with the logged-out cookie.
- Added disposable built-app HTTP launcher `scripts/review_session_ui.py` and
  injected `web/tests/browser/session-review.js`, with no production routes/bundle
  changes. Two owned synthetic users share a real temporary workspace. Notes are
  committed by the actual HTTP API; only successful note response delivery is held.
  Browser sequence passes: admin's note pending → real server logout → periodic
  real 401 returns Login → operator login shows operator identity and hides user
  management → a second note can submit while the old acknowledgment is pending.
- With two held responses, releasing the old admin response leaves the operator's
  note dialog, title/body and disabled saving state intact, records-changed zero,
  no old toast. Releasing the operator response closes the dialog, emits exactly one
  records-changed event and unlocks controls. Product Logout then returns Login.
  Screenshot `artifacts/v1-session-mutation-preserved.jpg` inspected visually:
  focused synthetic title/body and disabled saving button remain in the actual
  desktop modal. This is not mobile or real screen-reader validation.
- Final TypeScript/Vite build passes: `index-BZ98Asdc.js` / `index-B5ysGB7c.css`.
  Installed wheel + this separate built UI smoke passes with locked runtime deps,
  outside-checkout HTTP/auth/persistence/import/audit/backup/restore/shutdown/lease,
  zero target requests. Backend source unchanged; wheel SHA remains
  `48375e478cf2079dfbb129facdb209055248f9497338f07aa06ba79bfb536eba`.
  No full backend suite rerun is claimed. No actual before-build browser reproduction
  of the new main form guards is claimed; failing-before evidence is the shared
  helper tests, and the actual built-app sequence verifies the final integration.
- Owned QA server reports completed shutdown and exits on requested Ctrl+C (130);
  its initial launcher displayed Uvicorn's post-shutdown KeyboardInterrupt traceback.
  Launcher now handles that interrupt without a traceback. Main preview remains live.
  Cross-tab identity recovery, actual role/password-change browser flows, stale
  generic mutations in other standalone panels, fault injection and all mobile
  journeys remain separate open v1 requirements.

## 2026-10-04 — common registration inputs lock during submission

- Actual previous built app reproduces input loss: save a note while its successful
  HTTP acknowledgment is held, edit the still-enabled title, then release success.
  Dialog closes and the list shows only the originally submitted title; the later
  title disappears. This is a same-modal user sequence, distinct from closed-view
  or previous-session callback races.
- Main's common asset/plan/import/note forms now wrap their inputs in a native
  disabled fieldset while busy or without operator permission. The wrapper removes
  its own border/padding/background and preserves inner tool/policy groups. Form
  aria-busy and a separate status explain the waiting state. Submit and cancellation
  controls stay outside the fieldset. FormData is captured synchronously before
  React applies the disabled state. Cancellation keeps the existing view guard.
- Final actual built-app note scenario passes: held successful save shows title and
  body matching :disabled, original submitted values retained, aria-busy true and
  progress status; releasing response closes the modal and shows the stored note.
  Fixture F7 intercepts the next note POST with synthetic 503 before network send:
  the error appears, title/body remain, aria-busy false and inputs become enabled.
  Edit the title and retry: native inputs lock again, release the real HTTP success,
  dialog closes and the edited title is present. Final workspace has three notes
  (before reproduction, successful lock, successful retry), no failure-created note.
- Screenshot `artifacts/v1-submission-input-lock.jpg` inspected: submitted synthetic
  title/body, progress message, disabled saving button and existing desktop modal
  border/shadow remain readable. No color tokens changed. Selected design AA pairs
  pass via scripts/check_design.py; this is not full rendered accessibility checking.
- Existing 64 frontend tests pass (artifacts/submission-lock-tests.txt); no new
  implementation-mirroring test added for native fieldset behavior. TypeScript/Vite
  build passes: index-BN7GnyGW.js / index-rJkCwRk2.css. Installed unchanged wheel plus
  final built UI smoke passes, locked deps/auth/persistence/import/audit/maintenance/
  shutdown/lease, target requests zero. Wheel SHA remains
  48375e478cf2079dfbb129facdb209055248f9497338f07aa06ba79bfb536eba.
  No backend source changes or full backend rerun claimed. Actual browser before/
  after evidence covers the note form; asset/plan/import share the fieldset in source
  but their full busy-state journeys, mobile/zoom and assistive technology remain open.

## 2026-10-04 — authentication submission is single-flight and recoverable

- Previous actual built app reproduces two real login HTTP requests from one
  synchronous native form-submission burst. Both wrong-password responses are held;
  username remains enabled and can be changed while authentication is pending.
  This establishes duplicate submission and mutable pending credentials, not a
  demonstrated account takeover or server authorization failure.
- Auth now checks/sets a ref synchronously before requesting login/setup, disables
  username/password/setup-token inputs while pending, exposes form aria-busy and a
  separate progress status, and links the form to its error via useId/aria-describedby.
  Active-instance guards suppress callbacks after unmount; a stale authentication
  AbortError is not presented as a current error. Controlled inputs remain across a
  failed attempt. No credential/cookie inspection or runtime auth contract changes.
- Final real login fixture burst causes exactly one HTTP request and one held
  response; username/password native disabled, aria-busy true and progress visible.
  Release actual server 401: busy false, both inputs enabled, error '비밀번호를
  확인하세요.' and describedby resolves to the alert. Correct the synthetic password
  and repeat: cumulative requests two with only one new response pending; release
  reaches the actual administrator workspace. Product Logout works.
- Disposable launcher adds --setup for a truly empty workspace. Separate real setup
  fixture, synthetic username/password and empty local token: burst sends exactly
  one setup request, all three inputs disable, release reaches administrator controls
  and product Logout returns Login. Screenshot artifacts/v1-auth-setup-pending.jpg
  inspected: progress, disabled submit, password masking and existing Neo-brutalism
  layout remain visible. This is desktop evidence, not mobile/AT or remote token QA.
- Authentication fixture query hold_auth=1 adds burst/release controls and request
  counters without storing credentials/cookies or altering server results. Build
  passes index-ByZ4UnbC.js / index-rJkCwRk2.css. Existing frontend tests 64 pass
  (artifacts/auth-submission-tests.txt); no native-behavior mirroring tests added.
  Selected design AA pairs pass. Final built UI plus installed unchanged wheel
  passes locked-dependency/outside-checkout HTTP/persistence/maintenance/shutdown
  smoke, target requests zero; wheel SHA
  48375e478cf2079dfbb129facdb209055248f9497338f07aa06ba79bfb536eba.
  No backend edit or full backend suite rerun claimed. Full v1 gates remain open,
  including cross-tab behavior, remote setup-token failures, mobile/keyboard/AT
  review, and all authentication failure/recovery sequences.

## 2026-10-04 — explicit bounded AI planner usage with atomic provenance

- AI planner previously persisted raw provider usage on accepted plans only. New
  normalization retains just prompt/completion/total counters, integer range
  0..2^53-1, and explicit reported/partial/missing/invalid status. Missing values
  stay null, real reported zero stays zero. Booleans, strings, floats, negatives,
  oversized counters and inconsistent totals cannot become validated usage.
  Provider extra fields/response bodies/error strings are not persisted by this
  new path; historical audit events are not rewritten.
- Each actual configured planner call records outcome accepted/invalid_plan/
  request_failed, configured model, observation time, approved checks and normalized
  tokens in task metadata and audit event in one SQLite transaction. Invalid plans
  retain returned usage while falling back to approved checks. Transport/response
  failure keeps unknown usage instead of zero. Audit failure rolls back metadata.
  Scope/tool execution boundaries remain unchanged; no calls added to rule planning.
- Added 17 backend cases for numeric/data boundaries, rejected-plan usage, failure
  secrecy and atomic rollback. Targeted suite 24 passed; full backend 338 passed
  in 105.42s, one existing Starlette httpx deprecation warning. Evidence
  artifacts/llm-usage-backend-tests.txt. After that run, strengthened existing TLS
  test assertions verify task metadata plus actual JSON and Markdown HTTP exports;
  that selected test passes in 1.47s. It uses the actual trusted local HTTPS provider
  with 32 input/16 output/48 total and approved synthetic lab execution, not a
  commercial model. No further production Python edits occurred after the full run.
- Task detail includes the production PlannerUsage card; JSON task records and
  Markdown exports include call metadata. CSV remains a findings report. Synthetic
  browser component fixture displays all four usage states and accepted/fallback
  outcomes. Actual iframe documents client/scroll widths 320/320, 390/390, 768/768.
  Screenshot artifacts/v1-planner-usage-320.jpg inspected; values and unknown/error
  labels wrap without horizontal overflow. This is component QA, not a real phone
  or complete task-detail journey. Initial fixture measurements 316/386/764 were
  border-box widths; explicit content-box sizing corrected the requested documents.
- Existing frontend 64 tests pass (artifacts/llm-usage-frontend-tests.txt).
  Production build index-B3gq2ef6.js / index-BDg0otot.css passes; selected color AA
  pairs pass. New wheel SHA 866374d6c3317f0c51fa185444d7ededbc2cb9162b327b5a2b3d8e834476ad77
  matches all 36 current service Python files. Installed locked-runtime package +
  final UI smoke passes outside checkout, auth/persistence/import/audit/backup/
  restore/shutdown/lease with zero target requests. Evidence
  artifacts/llm-usage-package-review.json. Initial non-isolated wheel attempt failed
  because local bdist_wheel was absent; standard isolated pip wheel build succeeded.
- Main preview was gracefully stopped and restarted to load changed backend source;
  port 8790 health 200 and assets two/tasks four/traffic three preserved. Vite QA
  stopped. Provider-reported counters are not invoice verification; conversation
  citations/intervention, pricing provenance/costs, iterative calls, aggregate usage,
  live commercial models and full mobile/AT validation remain open v1 gates.

## 2026-10-04 — authenticated exact planner-usage aggregate

- Adds GET /api/llm/usage and a system-settings summary card. All/7-day/30-day
  windows aggregate the latest recorded planner call per task from one SQLite read
  snapshot. Counts distinguish reported/partial/missing/invalid usage and accepted/
  rejected/failed/unknown outcomes. Only consistent bounded integer reported values
  contribute; rejected plans with valid usage still contribute. No verified reports
  returns null totals; a real zero report returns decimal string "0".
- SQLite custom aggregate uses arbitrary-precision integer accumulation and decimal
  strings, avoiding SQLite SUM overflow and JavaScript number rounding. SQL computes
  projections/counts without Store.all/full-record Python materialization. Endpoint
  returns no model, task body, credentials or IDs and writes no audit event. Metadata-
  free, invalid-time and future records are outside this recorded-call window.
- Five new tests cover empty/missing versus true zero, mixed states and corrupt
  claimed-reported values, exact accumulation of 2,100 maximum-safe reports (sum
  18,915,118,434,956,081,100), old/future records, readonly/auth/admin/operator/viewer
  access and period validation. Initial integer-Literal query annotation rejected
  string HTTP days=7; explicit string Literal parsing fixes both supported windows.
  Targeted five pass, full backend **343 passed in 106.71s**, one existing Starlette
  httpx deprecation warning. Evidence artifacts/usage-summary-backend-tests.txt.
- Production summary component uses abort/session/active guards and explicit loading,
  error, retry and period state. Synthetic browser fixture verifies exact large-total
  display, pending refresh status/disabled refresh, 503 error and successful manual
  retry. Final actual iframe client/scroll widths 320/320, 390/390, 768/768. Screenshot
  artifacts/v1-usage-summary-320.jpg inspected; explanation/button horizontal margins
  improved after initial review. Native select keyboard attempts did not change the
  fixture's selection, so actual picker/period-change and delayed prior-period response
  interactions are **not verified** by this browser sequence. API period behavior is
  separately verified; no speculative browser/runtime cause claimed.
- Existing frontend 64 tests pass (artifacts/usage-summary-frontend-tests.txt).
  Final TypeScript/Vite build index-YDHBRw0g.js / index-B0bfSZoV.css and selected
  color AA pairs pass. New wheel SHA
  637a43d09402616cb323f2e6c6ef6eadba8edd05fbca04d2a85dfe78b3d7ebc9 matches
  current service source. Final installed locked-runtime wheel + UI review additionally
  checks empty usage, both supported periods, invalid period 422 and post-logout 401,
  alongside existing HTTP/persistence/maintenance/shutdown/lease checks; target requests
  zero. Evidence artifacts/usage-summary-package-review.json. Smoke was repeated
  after final CSS and these new endpoint assertions; backend source was unchanged.
- Main preview restarted gracefully with new backend; health 200, assets two/tasks
  four/traffic three preserved. Owned Vite stopped. This is a recorded single-call
  task aggregate, not all-provider billing, multi-round call ledger or model cost
  analysis. Historical events are not retroactively imported. Large-query resource
  limits/soak, full native/mobile/AT picker recovery, citations/intervention and
  commercial models remain open v1 requirements.

## 2026-10-04 — usage period selection and delayed-response recovery

- Follow-up closes the semantic period-selection gap recorded above. Browser
  combobox `selectOption('7'|'30'|'')` changes the actual native select. Seven days
  displays zero calls with unknown token totals; 30 days displays one missing-only
  call with unknown totals; all records restores 2,102 calls and the exact
  18,915,118,434,956,081,100 token total. Earlier keyboard attempts do not establish
  a production control defect; hardware keyboard/touch/AT journeys remain open.
- Enhanced the isolated synthetic fixture with visible pending period/HTTP status
  and a bounded six-request history. Confirmed a held `7 HTTP 200`, switched to 30
  days and observed its result, then released the old response: 30 days stayed
  selected with one call and unknown totals. Confirmed a held `7 HTTP 503`, switched
  to all records and observed its result, then released: all records and exact
  totals remained without an error alert. The fixture deliberately delivers held
  responses despite cancellation; no real API/provider requests occur.
- Current 30-day refresh returned synthetic 503 with the selected period intact.
  Manual Retry recovered its one-call/missing-only result while preserving 30 days.
  Final DOM snapshots inspected and artifacts/v1-usage-period-recovery.jpg visually
  reviewed. An earlier fixture edit triggered HMR and cleared a held request; that
  abandoned sequence is excluded from the evidence above and was repeated with
  the stable fixture and explicitly observed pending labels.
- This change affects only the browser fixture and documentation; production
  service/UI source, bundle and wheel are unchanged. Previously recorded 343
  backend and 64 frontend tests/build/package results were not rerun for this
  fixture-only follow-up. Full native/mobile/accessibility journeys and the broader
  open v1 requirements remain unverified.

## 2026-10-04 — recorded conversation citations and consistent context

- New recorded-rule replies label the task and up to eight priority findings and
  persist provenance version/mode, observation time, total finding count, source IDs,
  titles and only the fields used in the answer. A single SQLite read transaction
  spans task, compact finding page and validated coverage rows. Source updates
  after the first read cannot produce a mixture of old task/new findings or coverage.
  More than eight findings is explicitly disclosed; raw responses/fingerprints and
  growing evidence/task arrays are excluded from citation snapshots.
- Three new backend tests cover persisted citations after source edits, original
  reply/provenance replay, remediation-specific fields, foreign-task exclusion,
  bounded selection disclosure, missing task and real concurrent SQLite writes.
  The concurrency case commits task/finding/coverage updates on another connection
  after reading the task and confirms all cited values stay at the earlier snapshot.
  Existing exchange atomicity, idempotency, role and page tests remain passing.
- Targeted conversation/message tests: 10 passed. Full backend **346 passed in
  106.90s**, one existing Starlette/httpx deprecation warning; evidence
  artifacts/conversation-backend-tests.txt. Existing frontend **64 passed** in
  332.69ms; artifacts/conversation-frontend-tests.txt. TypeScript/Vite build succeeds:
  index-DsrmiRhf.js / index-D9FSMAbC.css.
- Production MessageProvenance uses native details, source labels, historical values
  and current-record links. Legacy messages have no fabricated provenance. Standalone
  fixture keyboard Enter opens details; link destinations and displayed values read
  from DOM. Later fixture default-open mode provides actual iframe documents with
  long title/remediation: widths 320/320, 390/390, 768/768. Screenshot
  artifacts/v1-message-provenance-320.jpg visually inspected. No provider/API calls
  occur in that component fixture; synthetic link IDs have no backend destination.
- Separate disposable actual HTTP server and built UI: authenticated admin creates
  an owned pending task, submits a question, reads stored reply, keyboard-opens
  provenance, follows the current-task link to the actual matching dialog, and opens
  a fresh document to recover the original reply/provenance. Screenshot
  artifacts/v1-message-provenance-built.jpg inspected; native message-region scrolling
  means it shows only part of expanded provenance. No task approval/target execution.
- New wheel matches all **38** current service Python files. SHA256
  56153fc0905e95f2fe7f997b4d243ca055ee3f5ec60f610e7535e4dc0052143c.
  Installed locked runtime outside checkout passes actual conversation citation,
  request-ID retry and persisted pair assertions alongside usage/auth/HTTP/maintenance/
  shutdown/lease checks; target requests zero. Evidence
  artifacts/conversation-package-review.json has valid=true. Owned Vite and disposable
  HTTP server shut down gracefully. Main preview updated separately to current code.
- This is task/finding-record provenance for rules summaries, not individual proof
  excerpts, model-grounded conversation, historical database integrity guarantees or
  execution intervention. Whole v1 gate stays open; remaining contracts are described
  in docs/CONVERSATION.md and docs/V1-READINESS.md.

## 2026-10-04 — same-task observation evidence in conversation citations

- Each selected finding now cites the most recently stored matching observation
  from the current task. The existing verified evidence query requires membership
  in the finding's references, matching asset/check/fingerprint and task membership;
  an additional current-task filter excludes other retest attempts. Task, finding,
  coverage and evidence reads share the same SQLite read transaction.
- Citation snapshots store source IDs/check/time, matching count, at most 4,096
  characters of formatted observation JSON and an explicit truncation flag. Invalid
  observation shape/time or no matching source produces an unavailable-evidence
  notice. No guessed proof or substitution from another task. Evidence ID was added
  to literal SQL search fields so the current-proof link can open a filtered finding
  history; its provenance checks still apply. Historical replies remain untouched.
- Twelve new backend cases exercise actual citations/retry preservation/ID search,
  cross-asset/check/fingerprint/task and malformed proof rejection, reference exclusion,
  same-task latest selection, excerpt bounds, and a concurrent committed evidence
  update after the first task read. Targeted conversation/finding/message suite:
  **27 passed**. Strengthened the real loopback check integration: every cited excerpt
  equals the engine's persisted observation and target requests stay at one after
  asking the question. Synthetic UI seeds are separate from that execution evidence.
- Initial full backend run overlapped Vite's asset replacement and one fixture setup
  failed because web/dist/assets momentarily did not exist: 357 passed, one setup
  error (artifacts/conversation-evidence-backend-build-race.txt). Build was complete
  before the next run: final **358 passed in 108.01s**, one existing Starlette/httpx
  deprecation warning. Evidence artifacts/conversation-evidence-backend-tests.txt.
  Existing frontend **64 passed in 364.27ms**; TypeScript/Vite build passes:
  index-D_jFmUmd.js / index-C-57Ezt8.css. Corresponding artifacts use the
  conversation-evidence-frontend-tests/build prefixes.
- Disposable actual HTTP/built-UI review seeds explicitly synthetic observations.
  Admin submits a question, keyboard-opens provenance, reads both missing-evidence
  and truncation notices, follows the proof link to one matching source, and opens
  its 7,135-character original. A new task document restores the 4,096-character
  excerpt and missing notice. Literal script text produces zero script nodes in
  excerpt/original. This proves text rendering, not model prompt-injection defenses.
  The focused excerpt supports PageDown: scrollTop 0 to 216 with its label retained.
  Screenshot artifacts/v1-conversation-evidence-built.jpg visually inspected.
- Component fixture at iframe viewport widths 320/390/768 gives root client/scroll
  widths **305/305, 375/375, 753/753**: the vertical scrollbar consumes 15px and no
  horizontal overflow appears. Long titles/remediation/observation and missing proof
  included; screenshot artifacts/v1-conversation-evidence-320.jpg visually reviewed.
- Wheel matches all 38 current service files; SHA256
  42720086a232318b858c1a043e8b53c6608fa33595e297a81ee6f52d19f2113c.
  Installed wheel + final UI review outside checkout passes existing persisted
  conversation/usage/auth/maintenance/shutdown assertions with target requests zero;
  artifacts/conversation-evidence-package-review.json valid=true. That installed
  scenario has a pending task without proof; observation-specific coverage is the
  backend/owned-UI evidence above. Full v1 remains open, including external-model
  conversations/intervention and full mobile/accessibility/operational review.

## 2026-10-04 — opt-in AI conversation drafts with cited-record recovery

- Adds explicit `mode=ai` messages (request ID required) behind server
  AEGIS_LLM_CHAT_ENABLED=1 plus configured key/model. Default rules requests never
  call a provider. UI checks configuration and offers a disabled-until-configured
  AI choice with a question/record/observation transmission notice. Pending-question
  storage preserves answer mode across retry/new readers and rejects invented modes.
- Provider prompt uses only the current task snapshot, selected finding fields and
  matched observation excerpts. UTF-8 JSON budget 64 KiB; response transport retains
  HTTPS/DNS/redirect/1 MiB guards and an eight-second deadline. Strict output has
  1–12 text/citation blocks, at most 1,500 text characters per block, and known source
  labels only. Extra action fields/foreign or absent citations/bad JSON/schema and
  literal configured-key echoes are rejected. No tool/target execution path is added.
  This validates citation membership/shape, not semantic entailment or all injections.
- Accepted replies are marked recorded_ai and visibly called drafts. Invalid output
  or request failure restores recorded rules and explains recovery. Reported usage
  survives invalid answers; failed-response usage is unknown. Question/reply/generation
  metadata and task-specific usage audit are atomic. Provider raw exceptions/rejected
  text are excluded. Current session/role and shutdown state are checked before commit.
- Single process admission rejects overlapping AI requests with 429/Retry-After.
  Committed request IDs replay without another call; same ID with a changed question
  or answer mode gives 409. A rules write racing an in-flight AI call also gives 409
  and preserves the committed rules pair. AI request IDs are not provider-side billing
  keys; crash/failed commit/revocation can leave consumed usage outside saved history.
- Eighteen new backend cases cover citations/usage/audit/replay, malformed output and
  key echoes, provider failure/configuration, rollback, concurrent admission, logout/
  role revocation, context budget, real loopback HTTP completion and a rules/AI race.
  Initial test harness assertions mistakenly counted a seeded foreign message and
  used a nonexistent logout method; corrected to task filtering and actual logout.
  Targeted initial AI/message suite subsequently 21 passed. Broader runs were repeated
  only after added race/key validation. Final **376 passed in 110.54s**, one existing
  Starlette/httpx deprecation warning; artifacts/conversation-ai-backend-tests.txt.
- Frontend **65 passed in 375.69ms** including answer-mode persistence. Final
  TypeScript/Vite build index-C9LagHtH.js / index-a5815QM7.css; evidence
  artifacts/conversation-ai-frontend-tests.txt and artifacts/conversation-ai-build.txt.
- Owned disposable built-UI/HTTP review with --ai-fixture: normal draft accepted with
  reported 20/10/30; foreign source output rejected with the same reported usage;
  HTTP 503 restores rules with unknown counters. Fresh task document restores all
  saved messages and mode selection/transmission notice. Initial screenshot found a
  flex row compressing the new selector/question/button; changed form to a single
  grid column. Final measured labels/button widths all 533px and screenshot
  artifacts/v1-conversation-ai-recovery.jpg visually inspected after rebuilding.
  Actual commercial providers and full mobile/AT flows were not exercised.
- New wheel matches all **39** current service files; SHA256
  58300c24aea7b1d1bddadbb30c13ad272bd489ec7700d0e4e7a1e4dc27211af1.
  Installed wheel + final UI review outside checkout valid=true, target requests zero;
  artifacts/conversation-ai-package-review.json. Repeated after final CSS and key guard.
  That installed scenario uses default rules mode, so provider-specific evidence is
  the checkout integration/owned UI above. Whole AI intervention, usage dashboard/
  cost ledger and v1 release gates stay open; docs/CONVERSATION.md defines limits.

## 2026-10-04 — signed release verification and offline update backup

- Adds installed aegis-release create/verify/prepare commands. Builder signs canonical
  manifest bytes with an explicitly supplied Ed25519 private key; verifier requires
  a separately trusted public key and checks its DER fingerprint, signature and all
  payload hashes/sizes. Payload includes one Open Aegis wheel, built UI and runtime
  lock. No bundle code is executed and no installation/service switch is performed.
- Strict manifest/path/type checks reject wrong keys, changed payload/manifest/
  signature, extra or missing files, symlinks/special files, traversal and malformed
  signed contracts. Creation rejects existing output and output inside UI input.
  Bounds: 256 KiB manifest, 10,000 files, 2 GiB per file. OpenSSL CLI errors/timeouts
  are bounded and do not print private material. Platform prerequisite is OpenSSL
  3.x on supported Linux/macOS; locally OpenSSL 3.6.4 used. Documentation links the
  primary OpenSSL signing/key command contracts in docs/RELEASES.md.
- Preflight verifies release before acquiring workspace lease, validates SQLite/
  JSON/foreign keys/audit, rejects unsupported read schema and unfinished execution
  tasks, then writes a validated backup and receipt in a new protected directory.
  Current DB is not migrated/installed. Backup/receipt modes 0600, directory 0700.
  Existing restore path supplies data rollback and session revocation; previous
  runtime/UI/configuration must also be preserved by the operator.
- Fifteen new cases pass, including actual OpenSSL signatures, all tamper/contract
  variants above, active lease refusal, incompatible schema/running task refusal,
  offline backup and restored original records after simulated failed-update writes.
  These unit fixtures use metadata-only synthetic wheels and do not prove wheel
  installation; the real wheel scenario below covers that separately.
- First full run: 390 passed and existing test_provider_response_size_is_bounded hit
  its HTTP read deadline. Isolated retry passed in 0.53s; underlying cause remains
  unproven, not claimed as a repaired race/resource bug. Initial failure evidence
  artifacts/release-backend-initial-deadline.txt retained. Final full rerun after CLI
  exception handling: **391 passed in 111.94s**, one existing Starlette/httpx warning;
  artifacts/release-backend-tests.txt. Frontend source/build is unchanged this turn;
  previous 65-test/final index-C9LagHtH.js/index-a5815QM7.css evidence remains applicable.
- Final wheel matches all **41** current service Python files. SHA256
  b105c8c3d814ed47ec60ba62076702a097f6ab8c5bb91df31091ac51c3c7a0aa.
  Installed locked runtime outside checkout passes five CLI help checks, actual
  server/auth/data/UI/maintenance/shutdown review, then installed release creation,
  separately supplied public-key verification, changed-UI rejection with exit 2,
  offline preflight backup and restored data after an injected note write. Installed
  restore revokes sessions and keeps a pre-restore copy. Ephemeral test key and dummy
  Git revision are explicitly synthetic and removed with the temporary installation.
  artifacts/release-package-review.json valid=true, target requests zero.
- This provides artifact verification, backup and data rollback building blocks.
  Official signing authority/key distribution/rotation, old/new-version process and
  configuration switching, failure injection across real upgrades, Docker volumes,
  CI/public publication and the whole v1 release gate remain open. No existing main
  workspace was restored or deployed in this review.

## Installed artifact transition and startup-failure recovery — 2026-10-04

- `scripts/review_release_transition.py` installs two distinct real wheels into
  separate fresh environments outside the checkout with locked dependencies and
  `pip check`. Old artifact revision 4a0717e58eb250d07588454de9607f59b0835034,
  SHA256 58300c24aea7b1d1bddadbb30c13ad272bd489ec7700d0e4e7a1e4dc27211af1;
  new revision 809a88cf95ead0f4307a2bcb9bbee7544ff453a9, SHA256
  b105c8c3d814ed47ec60ba62076702a097f6ab8c5bb91df31091ac51c3c7a0aa.
  Each wheel/UI/lock bundle is signed and verified with a separately supplied
  ephemeral public key. Private signing key is removed before server review.
- Actual HTTP old startup creates synthetic asset, pending unapproved task and
  note; offline signed preflight backs up the DB; new installed server reads the
  original records, serves its separate copied UI, writes a note, verifies audit,
  then shuts down. Its next startup runs original app startup, writes a distinct
  note and raises an injected exception before readiness. The child must exit
  unsuccessfully, stop serving health, and release the workspace lease.
- Old installed restore CLI restores the backup, revokes sessions and preserves
  the pre-restore DB. Retained old signed artifacts are verified again. Old runtime
  and retained UI/configuration restart; actual HTTP rejects the old cookie and
  permits password login. Original asset/task/note survive, both later notes are
  absent, audit is verified and target request count remains zero. All successful
  processes finish original lifespan cleanup and release their leases.
- Initial and final rehearsals pass. Final machine-readable evidence:
  `artifacts/release-transition-review.json`, valid=true, target_requests=0,
  four process-stage outcomes. Only the review script and docs changed; production
  service/UI remain the previously verified artifacts, so full suites/build were
  not repeated. `py_compile` and `git diff --check` pass.
- Both wheels are **0.1.0/schema 2**, sharing UI input, lock and common settings.
  This proves distinct installed-artifact/process switching and controlled startup
  failure recovery, not migration across released versions/schemas or configuration
  and UI changes. Signing authority is rehearsal-only. No automatic service manager,
  Docker, publication or existing-workspace restore is performed. Whole v1 stays open.

## Combined planner/conversation usage — 2026-10-04

- Authenticated `/api/llm/usage` now accepts source=planner/conversation/all, retaining
  the original planner-only default. The UI defaults to combined usage and offers
  source and period selections. One SQLite query/read snapshot joins latest task
  planner metadata with persisted assistant generation metadata. Questions, rules
  replies, missing metadata, invalid timestamps and future records are excluded.
  Reported values are revalidated and summed as exact decimal strings; missing,
  partial and invalid values are not treated as zero. Result counts distinguish
  rejected plans, rejected answers and failed requests.
- Targeted usage/conversation tests: **27 passed**. New coverage includes source
  separation, rejected and failed answers, wrong-source outcomes, periods, bool and
  inconsistent counters, combined totals exceeding SQLite/JavaScript integer ranges,
  authenticated viewer/operator access and private payload exclusion. Existing AI
  exchange tests now assert retry counts once and audit rollback counts zero.
- Initial full run: 394 passed, one backup test failed while the simultaneous UI
  build replaced `web/dist/assets`. This was a review scheduling error; evidence
  `artifacts/combined-usage-backend-initial-build-overlap.txt` retained. With the
  build finished and files fixed, full backend rerun: **395 passed in 112.93s**,
  one existing Starlette/httpx warning (`artifacts/combined-usage-backend-tests.txt`).
- Final frontend suite: **65 passed in 346.96ms**. Final TypeScript/Vite build passes;
  UI bundle index-BsfIISmt.js/index-a5815QM7.css. Backend source did not change after
  the full rerun; later changes were UI response compatibility handling and review
  scripts/docs. A fresh default-isolated wheel build succeeds; an initial attempt
  without isolation could not build because this local venv lacks bdist_wheel.
- Synthetic browser component review: source switch while prior planner response
  is held, delayed response release, 503 and same-condition retry all preserve the
  current selected source/result. Separate native source/period controls have labels.
  Old server metadata without source/source_counts originally blanked the component;
  reproduced then fixed to show a compatibility alert and retry. Retry with current
  metadata recovers. 320px viewport yields client/scroll 305/305 (vertical scrollbar),
  390px 390/390, 768px 768/768. Actual 320 screenshot visually inspected:
  `artifacts/combined-usage-320.jpg`. Whole mobile/touch/SR journeys remain open.
- Actual built UI + temporary owned HTTP AI provider: accepted draft, invalid
  citation and HTTP 503 each committed one answer. Combined and conversation cards
  show 3 calls, 2 reported/1 missing, accepted/rejected/failed 1 each, input40/output20/
  total60; planner-only shows zero calls and unknown totals. Final rebuilt UI reload
  preserves the result. Text evidence `artifacts/combined-usage-live-all.txt` and
  `combined-usage-live-chat.txt`; visually inspected final screenshot
  `artifacts/combined-usage-live-final.jpg`. No target requests or commercial calls.
- Final wheel SHA256 788a41d9d8c7343399a4a9a235812fc83f74d9eda08ec0adf2ca8cab5b198f9e
  byte-matches all 41 service Python files. Fresh locked installed package outside
  checkout passes real HTTP usage source/period validation, auth, UI, backup/restore,
  signatures/preflight and clean shutdown. `artifacts/combined-usage-package-review.json`
  valid=true, target_requests=0. Temporary QA server/provider/Vite/tabs stopped.
  Main preview restarted with preserved data and final matching UI; health HTTP200.
- This is persisted usage reporting, not a billing ledger: provider attempts without
  a committed reply (revocation/write failure) are absent, retry attempts/repeated
  planner rounds/model costs are not accounted for. Price sources, actual commercial
  provider verification, full accessibility and the whole v1 gate remain open.

## Call-time price quotes and exact token cost estimates — 2026-10-04

- Optional `AEGIS_LLM_PRICES` supplies bounded model/provider-matched flat text-token
  quotes with currency, decimal-string input/output rates, source URL and as-of date.
  Planner and conversation snapshot quotes before provider calls and persist exact
  cost metadata with existing usage/audit transactions. Invalid configuration is
  explicit and does not persist raw parser messages or become a zero-cost estimate.
  Quote URLs are never fetched. No published provider rates are hardcoded; all review
  rates/URLs below are synthetic. Contract and official unit reference: LLM-COSTS.md.
- New cost tests cover exact fractional and zero amounts, call-time quote retention
  across config changes, 15 malformed quote variants, unknown model/provider,
  duplicate identities/JSON keys, deep configuration rejection, separate currencies,
  changed amounts/models, old unrecorded costs and large-plus-tiny precision.
  Real test-client conversation retries keep the original quote and one aggregate
  call; planner test changes config during provider response and keeps the start
  quote. Targeted cost/usage/LLM/conversation run: **68 passed**.
- Initial full backend: **416 passed in 112.98s**. Review then added rejection of
  valid reported usage mislabeled as usage_unavailable; cost/usage rerun **30 passed**.
  Final full backend: **416 passed in 112.35s**, one existing Starlette/httpx warning
  (`artifacts/costs-backend-tests.txt`). No further backend edits. Frontend **65 passed
  in 296.99ms**. Final TypeScript/Vite build after cost heading alignment passes:
  index-DIxRRKfh.js/index-DozFChs7.css. Neither UI rebuild ran during backend checks.
- Browser planner component: Enter opens native price-proof summary; Space closes.
  Opened long synthetic source URL fits 320/390/768 documents: client/scroll
  305/305, 375/375, 753/753 with vertical scrollbars. Screenshot
  `artifacts/costs-price-proof-320.jpg` visually inspected. Aggregate cost card with
  exact USD18915118434956.081107 also fits those document widths; source switching
  with held prior response and 503/retry retains current conversation cost0.000007.
  `artifacts/costs-summary-320.jpg` records its narrow document.
- Actual built UI + disposable owned provider + synthetic price fixture: accepted
  and invalid-citation answers each retain reported20/10/30 and USD0.00005. Native
  price-proof reveals model, loopback provider, source URL, as-of and rates1.25/2.5.
  HTTP503 reply shows unknown cost with retained valid price proof. System settings
  shows estimated2/unknown1, currency-specific USD0.0001, and token total60. Final
  UI bundle reload/requery preserves values. `artifacts/costs-live-all.txt` and
  visually inspected `artifacts/costs-live-all.jpg` record the result. No target or
  commercial provider calls.
- Final wheel SHA256 f005480879200b074698923cddfd43a09fbb9511096d170566de56eb793b2397
  byte-matches all **42** service Python files. Installed locked runtime outside
  checkout verifies empty cost states/totals without inferring zero, authentication,
  real HTTP/UI, maintenance, signed release/preflight/rollback and clean shutdown.
  Review was repeated with final UI bundle; `artifacts/costs-package-review.json`
  valid=true,target_requests=0. Temporary provider/server/Vite/browser tabs closed.
  Main preview refreshed with same data (assets2/tasks4/traffic3), final UI and HTTP200.
- This is an operator-quoted flat token-price estimate and partial currency total.
  Cached/context-tier/service-mode/tool fees/tax/discounts/exchange rates, real bill
  reconciliation, model-level cost grouping, uncommitted provider attempts and
  repeated planner history remain unimplemented/unverified. Price source authenticity,
  commercial models, full accessibility/mobile and the whole v1 gate stay open.


## Independent provider attempt ledger (2026-10-04)

- New `llm_calls` records preserve start/observation independently from result
  persistence. Start plus audit commits before contacting the provider; observation
  plus audit commits before final reauthentication/result write. Final result and
  committed state share one transaction. Failed final writes retain observation and
  become uncommitted; exclusive app startup recovers pending states as interrupted.
  Ordinary Store construction never recovers calls. No prompts/questions/response
  bodies/credentials enter this ledger. Contract: LLM-CALLS.md.
- Six new backend tests cover session revocation, actual audit-failure transaction
  rollback, failed-write retry vs successful replay, start-audit refusal before
  provider contact, restart recovery/idempotence and authenticated filtered pages.
  Targeted suite: **74 passed**. Full backend: **422 passed in 114.36s**, one existing
  Starlette/httpx warning (`artifacts/ledger-backend-tests.txt`). Frontend modules:
  **65 passed in 328.23ms** (`artifacts/ledger-frontend-tests.txt`). Final TypeScript/
  Vite build passes after the retry-cost notice change; index-Ciak_MNC.js and
  index-DozFChs7.css. No backend changes after the full pass.
- Real built UI plus disposable owned provider: session revocation during a valid
  response yields no saved exchange; after login, attempts show uncommitted1,
  reported20/10/30 and synthetic USD0.00005 while persisted calls remain0
  (`artifacts/ledger-live-uncommitted.txt`). A later normal answer commits; provider
  HTTP503 plus exchange-write failure preserves an additional attempt with unknown
  usage, rather than inventing zero. Three-call aggregate: committed1/uncommitted2,
  reported total60, estimated2/unknown1, USD0.0001
  (`artifacts/ledger-live-final.txt` and visually inspected screenshot).
- The initial fixture's generic provider-failure substring overlapped its storage
  failure trigger. Separated those conditions and restarted the disposable fixture:
  provider HTTP200 followed only by exchange-write failure leaves no messages and
  persisted calls0, but attempts1/uncommitted1 with reported20/10/30 and USD0.00005.
  Built UI explains a retried AI call may cost extra. Evidence:
  `artifacts/ledger-live-write-failure.txt` and visually inspected full-page JPG.
  These are synthetic local checks, not commercial billing or target requests.
- Browser component held old persisted responses cannot replace selected attempt
  results; 503/retry preserves selection. A response retaining source/source_counts
  but missing ledger/state metadata shows compatibility error; retry recovers.
  Default persisted aggregate with the new controls fits 320/390/768 documents:
  client/scroll widths305/305,375/375,753/753. Narrow screenshot visually inspected:
  `artifacts/ledger-summary-320.jpg`. Whole mobile/touch/AT journeys remain open.
- Final wheel SHA256 d42baada0833bfbe099799bfeefe316a96f69892e73be81a0ba812f89c28545a
  byte-matches all **43** service Python files. Installed locked runtime outside
  checkout validates authenticated empty attempt aggregate/page and bad state422,
  normal HTTP/UI, maintenance and signed release/preflight/rollback. Additional
  installed exclusive create_app startup plus actual lifespan marks seeded started
  and observed records interrupted, retains reported5, keeps missing usage unknown
  and validates audit integrity. This is controlled startup recovery, not a live
  process-crash or billing reconciliation test. Final UI included in review:
  `artifacts/ledger-package-review.json` valid=true,target_requests=0.
- Preview restarted cleanly on8790 with final UI, HTTP200 and assets2/tasks4/traffic3.
  Attempt detail UI/export, disk retention, model grouping, actual billing and
  unobserved-response loss windows remain open. Existing whole v1 release gates,
  PostgreSQL/migrations, external tool isolation, repeated autonomous planning,
  long-running resource/accessibility checks and official release work remain open.


## Individual call history UI (2026-10-04)

- Added system settings CallHistory using the existing authenticated `/llm/calls`
  SQL API and25-row useRecords paging. Search, source, storage state and task-ID
  filters plus offset/watermark persist in `llm_calls_*` URL parameters. Filter
  changes reset page/watermark; invalid enum/IDs and unbounded/inexact positions
  normalize before API calls. Two focused navigation tests cover bookmark
  roundtrip, independent URL fields, filter boundaries and hostile inputs.
- Per-call native details show sanitized provider origin, actor ID, observation/
  settlement times, shape outcome separately from storage state, token status/
  values, operator-quoted cost proof and linked result ID. Missing observations
  do not fabricate response times or zero usage. Task navigation preserves call
  filters. Question/response bodies and detailed failure causes are not present
  in the ledger; the UI explicitly avoids claiming a precise failure cause.
- Frontend **67 passed in335.05ms** (`artifacts/call-history-frontend-tests.txt`).
  Existing call-ledger API tests **6 passed in1.20s**, one existing Starlette/httpx
  warning (`artifacts/call-history-api-tests.txt`). Service Python is unchanged;
  previous full backend422-pass evidence remains applicable. Final TypeScript/
  Vite build passes: index-cPS8RbeC.js/index-DniDnrrf.css
  (`artifacts/call-history-build.txt`). No production changes after this build.
- Browser production component + synthetic29-row fixture: page26–29 and fresh
  document restoration verified; changing storage filter returns first page.
  Back/Forward restores uncommitted/started filters and their matching lists.
  Enter opens call detail; unknown interrupted record shows missing usage and no
  fabricated observation. Visible held-request counter confirms a pending prior
  response; release after selecting started cannot overwrite that selection/list.
  Persistent503 across refreshes labels last received list and exposes alert;
  manual recovery retains selected state (`artifacts/call-history-error.txt`).
- All details/long model and quoted-price source opened in320/390/768 iframe
  documents; client/scroll widths301/301,371/371,749/749. Width includes the4px
  frame border plus vertical scrollbar. `artifacts/call-history-320.jpg` visually
  inspected. This is geometry/native keyboard coverage; complete mobile/touch,
  zoom, screen-reader and full user journeys remain open.
- Actual built app with owned synthetic provider: normal20/10/30 answer saved;
  a second valid20/10/30 response followed by exchange-write failure retains its
  uncommitted record and USD0.00005. Both calls appear with distinct IDs. Native
  price proof inspected; uncommitted filter survives fresh document and task
  navigation/re-entry. `artifacts/call-history-live.txt` and visually inspected
  full-page JPG. These are actual local HTTP requests with synthetic observations/
  prices, not commercial billing or target execution evidence.
- Reused unchanged wheel SHA256
  d42baada0833bfbe099799bfeefe316a96f69892e73be81a0ba812f89c28545a with final UI.
  Installed locked runtime outside checkout review remains valid=true,
  target_requests=0 (`artifacts/call-history-package-review.json`), including
  authentication, maintenance, attempt recovery and signed release/preflight/
  rollback rehearsal. The installed script checks HTTP/UI artifact availability;
  interactive CallHistory coverage above comes from the built-app browser review.
- Detail expansion/inner scroll bookmarks, dedicated export and direct message-ID
  navigation remain open. Existing whole v1 PostgreSQL, external tool isolation,
  repeated planning, long-running/accessibility and official release gates stay
  open. No whole v1 gate is closed by these component checks.

- Temporary provider/server/Vite and browser tabs were closed after review. Main
  preview8790 serves the final UI with HTTP200 and retained assets2/tasks4/traffic3.


## Offline PostgreSQL transfer and provider bounds (2026-10-04)

- Added optional psycopg[binary] dependency and separate pinned3.3.6 lock, plus
  installed `aegis-transfer-storage` CLI. SQLite2 → fresh PostgreSQL schema uses
  read-only source + workspace lease, active-task refusal, atomic DDL/COPY,
  preserved original TEXT JSON/details/credential hashes/rowids/event seq and
  timestamp values, per-table framed SHA256 and original audit checkpoint checks.
  Sessions are omitted from the destination; source sessions remain valid.
  Existing schemas/output files are refused. Contract: POSTGRES-STORAGE.md.
- Reverse export validates transfer metadata/table types/audit in REPEATABLE READ,
  READ ONLY. Server-side cursors bound client-side history collection. A0600 staged
  SQLite database must pass exact manifests, audit and SQLite validation, then
  PostgreSQL read transaction/connection termination before no-overwrite hard-link
  publication + directory fsync. Event sequence high watermark survives the roundtrip.
  Known unsupported textual NUL input is refused, never silently stripped.
- Actual owned PostgreSQL16.15 tests cover schema-name refusal/SQL identifier quoting,
  roundtrip exact data/users/audit and source-session retention vs destination
  revocation, next SQLite event101 from saved sequence100, duplicate target refusal,
  busy source/active task/corrupt audit refusal, actual COPY failure and injected
  final verification failure rolling back the entire new schema, altered PG audit
  preventing publication, real pg_dump/pg_restore to a new DB then return, private
  CLI error redaction, stage verification cleanup and a concurrent PG record edit
  leaving the exported reading snapshot consistent. Final full suite includes all
  **17** PostgreSQL cases, explicitly opted in with AEGIS_TEST_POSTGRES=1.
- Publication ordering defect reproduced on the actual transfer/file path with a
  controlled exception after the real read transaction exits. Before: error raised
  but output file exists (`artifacts/postgres-publication-before.txt`). After moving
  publication beyond successful transaction/connection exit: unchanged assertion
  passes and stage/output remain absent. This is transaction-exit fault injection,
  not a physical network outage/crash test; no claim of actual network interruption.
- Initial full run434-pass plus provider-size timeout; isolated original case passes.
  An intermediate436-pass run was followed by a final439-case run where that same
  unchanged original size test returned ConnectionResetError during body read.
  No timeout/test expectation was relaxed. A deterministic owned provider sends
  declared oversize headers and withholds its body: before code waits then times
  out (`artifacts/llm-header-bound-before.txt`). Now known oversize is refused before
  body read; undeclared and chunked responses still enforce actual-byte size, and
  exactly1 MiB valid JSON remains accepted. Related LLM/runtime/ledger/conversation
  suite **71 passed in18.34s** before adding the exact-boundary positive control.
  The observed full-suite body failures do not independently prove why a peer reset
  or delayed that transfer; the known-oversize dependency on body arrival is proven
  and removed. Existing8-second guard, TLS/scope/redirect protections remain.
- Final full backend with all17 real PostgreSQL cases and four new actual HTTP
  response controls: **443 passed in118.10s**, one existing Starlette/httpx warning
  (`artifacts/postgres-transfer-backend-final.txt`). No further service Python edits.
  UI source/build is unchanged from the prior67-pass review; it was not rebuilt.
- Final wheel SHA256
  7f847db38ccdcb3961d6f1d2b1502036d7ff7763d4d49d31ebb46a37a9902d19
  byte-matches all **45** current service Python files. Default installed runtime
  outside checkout verifies all six entry points, locked dependencies/pip check,
  real HTTP/UI/authentication, maintenance/attempt recovery and signed release/
  preflight/rollback (`artifacts/postgres-runtime-review.json` valid=true,
  target_requests=0). Same final wheel plus locked optional dependency independently
  passes installed transfer CLI → actual PG COPY → real custom-format dump/restore
  → installed SQLite return, session revocation, password verification/exact amount
  and subsequent audit event (`artifacts/postgres-installed-review.json` valid=true,
  target_requests=0,service_postgres_backend_enabled=false). Owned UNIX-socket
  PostgreSQL server fsync=on is queried and asserted; this is not power-loss/PITR proof.
  Disposable clusters/installations are stopped/removed by the successful runners.
- CI gained an opted-in PostgreSQL16 job with the locked optional dependency, actual
  cluster tests and installed migration rehearsal. GitHub hosted execution is not
  yet verified. PostgreSQL service Store/queries/locks/reporting/authentication/
  lifecycle/operational backup and remote TLS/resource cases remain unimplemented
  or unverified; the whole v1 PostgreSQL gate stays open. Source is not copied into
  a live PostgreSQL service merely by setting AEGIS_POSTGRES_DSN.

- Final preview restarted cleanly with current code/UI on8790, HTTP200 and retained
  assets2/tasks4/traffic3. CI PATH append format was locally executed against a
  disposable file and verified to write an actual newline; this does not establish
  hosted CI completion. No remote publication or real target/provider requests.

### Native PostgreSQL Store foundation (service integration remains open)

- Added `PostgresStore` using native psycopg transactions, bound parameters and
  PostgreSQL JSON queries. Reads use REPEATABLE READ/READ ONLY; cooperative writes
  take a database/schema transaction advisory lock. Constructor reads metadata and
  audit state without recovering tasks or revoking sessions. HTTP/engine/reporting/
  lifecycle selection is not yet connected; no `AEGIS_POSTGRES_DSN` runtime switch.
- Actual PostgreSQL16.15 tests compare representative Store pages/search/array
  proof filters/compact severity order/observation source names/revision coverage
  and scheduler/recovery records to SQLite. Verified session security revocation,
  atomic batch refusal, read-only rejection and consistent reads during a separate
  Store update, thirty concurrent events across two Store instances, checkpoint/
  tamper rejection, message replay/conflict and planner-attempt/audit rollback.
- Failed audit transactions consume PostgreSQL identity values. Reverse transfer
  now reads the actual sequence high water mark as well as metadata. A real native
  write, injected failure after event/hash/head writes, custom pg_dump/pg_restore
  and SQLite return preserve the unused allocation: committed seq1 followed by
  failed seq2 returns with the next event seq3. Audit contains only committed rows.
  This is controlled transaction failure, not physical power-loss/crash proof.
- Targeted integration run: **28 passed in3.83s**, comprising17 transfer cases and
  11 native Store cases (`artifacts/postgres-native-targeted.txt`). An earlier run
  failed because the test's injected failure remained enabled during its positive
  continuation control; resetting that injection fixed the fixture, preserving
  the rollback and sequence assertions. No production workaround/test relaxation.
- Full opted-in backend suite: **454 passed in121.20s**, one existing Starlette/
  httpx warning (`artifacts/postgres-native-backend.txt`). UI source/build unchanged.
- Wheel SHA256 e771b1c319c98edc5615fc35a5df59d9c368a33889502d36d5ccb9c383312471
  byte-matches all **47** service Python files. Outside-checkout installed native
  PostgreSQL Store writes/search/session revocation followed by actual dump/restore
  and SQLite return pass (`artifacts/postgres-native-installed-review.json`,
  valid=true,target_requests=0,service_postgres_backend_enabled=false). Default
  installed SQLite HTTP/UI/auth/maintenance/recovery/signed-release checks pass
  with the same wheel (`artifacts/postgres-native-runtime-review.json`,valid=true,
  target_requests=0). Successful runners stop/remove disposable clusters/envs.
- CI PostgreSQL job includes both transfer and native Store tests; hosted execution
  is not verified. Advisory locking is cooperative, initial writes are serialized,
  connections are not pooled, and PostgreSQL query indexes/throughput/soak/remote
  TLS/operational restore and multi-server service ownership are still open. Raw
  TEXT transfer preservation is distinct from jsonb query parity for malformed,
  duplicate-key or out-of-range-number records. The full v1 gate stays open.

### PostgreSQL attempt lifecycle and usage foundation

- The shared call ledger now persists native PostgreSQL start/observation/abandon/
  recovery transitions with audit in the same write transaction. Final result
  commits reuse the shared validation in both stores. Recovery keeps100-record
  transaction batches and requires caller-owned exclusive startup authority;
  PostgreSQL service ownership/startup wiring is still open, not enabled here.
- Actual PG tests prove start/observe/abandon/recover audit failures roll back their
  transitions, two independent Store instances accept only one concurrent
  observation, final successful message replay keeps one committed attempt, and
  a second recovery batch failure preserves the first100 settled records while
  rolling back the next batch. Retrying recovery completes206 interrupted rows
  without modifying an already settled row or double-appending completed recovery.
- Native usage streams only selected metadata with a200-row server cursor in one
  read-only snapshot. Counts/tokens use exact integers and existing validated cost
  quotes retain exact per-currency units. Source/window/persisted/attempt results
  match SQLite; tested boolean/inconsistent/partial/missing usage and huge-plus-tiny
  costs.2100 maximal valid usages sum beyond int64/JavaScript ranges exactly. A
  separate actual DB write during cursor iteration does not mix token/cost snapshots.
  Initial metadata transfer still scales with call count; no claim of aggregate
  performance/soak SLO or individual-record resource bound.
- Owned loopback HTTP provider sees its durable started attempt before receiving
  the synthetic request. Its validated response is observed then committed with
  the native message pair/audit; usage agrees between attempts and saved messages.
  Synthetic key is absent from saved attempt data. No external provider/target.
- Related SQLite ledger/conversation/runtime: **48 passed in15.67s**. Final native
  ledger/Store plus SQLite usage/cost/ledger subset: **60 passed in5.86s**
  (`artifacts/postgres-ledger-targeted-final.txt`). Full opted-in backend:
  **467 passed in121.99s**, one existing Starlette/httpx warning
  (`artifacts/postgres-ledger-backend-final.txt`). No UI edits/rebuild.
- Wheel SHA256 a3199d69e6fb811e7f0034b5df4c10a45b931b7c3f712d929e13dcafd13cc55b
  byte-matches all48 service Python files. Installed native lifecycle/standalone
  recovery/exact usage, real pg_dump/pg_restore and SQLite return pass outside the
  checkout (`artifacts/postgres-ledger-installed-review.json`,valid=true,
  target_requests=0,service_postgres_backend_enabled=false). Same wheel's default
  installed SQLite HTTP/auth/UI/maintenance/release checks pass
  (`artifacts/postgres-ledger-runtime-review.json`,valid=true,target_requests=0).
  Successful runners stop/remove their owned clusters/installations. CI includes
  native ledger tests; hosted CI is still unverified.
- HTTP/engine queries, graph/finding/import transactions, PostgreSQL reporting/
  bounded audit readers, service startup exclusion and operational restore remain
  required before enabling the PostgreSQL service backend. The full v1 gate stays
  open; an optional DSN alone does not change the HTTP backend.
- After the full suite, strengthened the snapshot control to change both valid
  reported tokens and a valid USD quote-derived amount during the native read:
  snapshot retains10 tokens/USD0.0000175; next read sees105/USD0.00013375.
  That unchanged production path passes the targeted actual PG control
  **1 passed in1.22s** (`artifacts/postgres-ledger-cost-snapshot.txt`). No service
  Python edits after the full suite or wheel build. Owned preview restarted with
  current code on8790 (PID90617), normal shutdown completed first; HTTP200.

### Native PostgreSQL Engine and atomic finding decisions

- Engine queue metrics and bounded oldest overdue IDs now use reviewed Store
  methods with SQLite/native PostgreSQL queries. Engine has no direct SQLite SQL
  connection; approved standalone execution uses the existing scope/tool contracts,
  Transport/Worker limits and coverage/finding APIs. HTTP backend selection and
  PostgreSQL service ownership/loss-of-ownership handling are still unimplemented.
- Observation, human triage and retest read/validate/update within one Store write
  transaction, including assignee lookup and related evidence/history/retest rows.
  PostgreSQL uses its advisory write order; SQLite uses BEGIN IMMEDIATE. Two
  independent Store instances on either backend retain one finding,17 proof/task
  references and17 histories after16 concurrent repeat observations. Two decisions
  for revision1 yield one revision2 winner and one conflict; an older retest keeps
  that decision. Failure after real batch writes rolls back related rows in all
  three paths. No claim of arbitrary external SQL writers following this protocol.
- Owned standalone PostgreSQL Engine tests cover approval with no pre-approval
  request, actual loopback validation/traffic/evidence/observations/coverage, a
  hardened follow-up retest resolving the selected finding, changed asset revision
  refusal, pending rejection, startup interruption coverage, queue expiry, and
  stop during an actual held HTTP request. Queue watchdog stays error-free; audit
  chains verify. This is an isolated exclusive test process, not multi-server
  service ownership or production PostgreSQL HTTP execution.
- Related SQLite triage/runtime/validation: **64 passed in29.02s**
  (`artifacts/postgres-engine-sqlite.txt`). Final native Engine/Store/ledger subset:
  **34 passed in6.58s** (`artifacts/postgres-engine-targeted-final.txt`). Full backend
  with explicit PG opt-in: **477 passed in123.13s**, one existing Starlette/httpx
  warning (`artifacts/postgres-engine-backend-final.txt`). No UI edits/rebuild.
- Wheel SHA256998ba3fa16b342353ff73701b56ed7725dce41ac663c7cc33f655750e07af13a
  byte-matches all48 service Python files. Outside-checkout installed standalone
  Engine executes one approved GET against its owned loopback server, persists
  findings/proofs/coverage, then shuts down before manifest/dump/restore/SQLite
  return verification (`artifacts/postgres-engine-installed-review.json`,valid=true,
  target_requests=1,owned_lab_requests=1,external_target_requests=0,
  service_postgres_backend_enabled=false). Default installed SQLite runtime's
  HTTP/UI/auth/maintenance/attempt recovery/signed release checks pass the same
  wheel (`artifacts/postgres-engine-runtime-review.json`,valid=true,target_requests=0).
  Successful runners stop/remove disposable clusters/installations. CI includes
  engine tests; GitHub hosted execution remains unverified.
- Whole v1 PostgreSQL gate stays open: HTTP queries/graph/import/reporting/bounded
  audit readers, startup ownership and operational backup/restore are required.
  No public PostgreSQL service configuration or remote publication was enabled.
- Owned preview shut down cleanly before restarting current code on8790
  (PID11671/session65747); HTTP200. Existing preview workspace retained.

### PostgreSQL runtime ownership and operation fencing

- Added database/schema runtime ownership: exclusive session admission, shared
  ownership acquired on that same session before exclusive unlock, and shared
  transaction gates for owner-bound Store operations and target/provider requests.
  Each operation verifies the original dedicated PID/backend_start/granted lock.
  Already admitted work fences replacement admission until transaction/request end;
  old Store never adopts a replacement owner or reconnects. Closed Store stays
  closed. Offline native writes and reverse transfer require exclusive gates.
- Native Engine acquires ownership before ledger/task recovery, releases on startup
  recovery/pool-construction failure, and shuts Workers down before normal release.
  Confirmed ownership loss closes admission, sets stops and halts queue watching.
  Lost-owner shutdown cannot overwrite replacement recovery. Native conversation
  provider requests and Planner completion use execution permits; SQLite uses the
  existing path with null permits. HTTP PostgreSQL selection is still not enabled.
- Actual dedicated backend termination proves stale writes/next target and provider
  requests refused, admitted write and held HTTP/provider requests block takeover,
  old Store rejects a new owner, and replacement recovery preserves unknown usage
  when a response wasn't durably observed. No inferred zero/reporting of lost usage.
  Separate Python process holds the lease and excludes parent admission; ordinary
  non-superuser schema/table/sequence grants work. Two schemas remain independent.
  Active owner refuses offline writer (existing5-second lock guard) and export
  without publishing/staging a result. Startup failures release ownership.
- Foundation native transfer/Store/ledger/Engine tests: **51 passed in10.10s**.
  Ownership+engine+ledger+SQLite runtime/conversation: **75 passed in28.21s**
  (`artifacts/postgres-ownership-targeted-final.txt`). Final ownership cases after
  adding ordinary-role/schema controls: **12 passed in8.61s**
  (`artifacts/postgres-ownership-roles-final.txt`). Full backend with explicit PG:
  **489 passed in131.36s**, one existing Starlette/httpx warning
  (`artifacts/postgres-owner-backend-final.txt`). No UI edits/rebuild.
- Wheel SHA256cda7641f380095c9b27f7d9cb945cd5b5cde36f2e075445a3cbee04748551acf
  byte-matches49 service Python files. Outside-checkout installed native Engine
  refuses duplicate ownership and live export, then performs one owned loopback
  GET, clean shutdown, actual acquired-backend termination/stale write refusal,
  replacement audit, real dump/restore and SQLite return
  (`artifacts/postgres-owner-installed-review.json`,valid=true,target_requests=1,
  owned_lab_requests=1,external_target_requests=0,service_postgres_backend_enabled=false).
  Same wheel's installed default SQLite HTTP/auth/UI/maintenance/release checks
  pass (`artifacts/postgres-owner-runtime-review.json`,valid=true,target_requests=0).
  Successful runners stop/remove owned clusters/installations. CI includes ownership
  tests; hosted execution is still unverified.
- This proves direct owned DB session termination, not remote TCP blackhole/proxy/
  HA failover/power loss or latency/connection SLO. Advisory cooperation does not
  constrain raw administrator SQL. Empty-session export restriction remains;
  running-service sessions/operational restore contract, HTTP/graph/import/report/
  bounded audit integration and full service lifecycle QA remain required. Full v1
  gate stays open. No remote publication or external target/provider requests.
- Owned preview completed normal shutdown before restarting current code on8790
  (PID47419/session73026); HTTP200. Existing preview data retained.


### PostgreSQL session-aware return and native bounded graph

- Stopped owned-schema PostgreSQL databases may now contain sessions during
  reverse transfer. The exclusive runtime gate still refuses active ownership.
  Return validates a consistent read-only snapshot, omits sessions from the new
  SQLite database, records `omitted_session_count` and
  `source_sessions_preserved=true`, and leaves source sessions valid. Users,
  password hashes, records, audit chain and sequence state remain preserved.
  `sessions_revoked` describes the returned copy, not source deletion. Stage
  validation failure publishes nothing and preserves source authentication.
- Added explicit native PostgreSQL graph queries within one read transaction,
  sharing rendering with SQLite. Normal typed fields, proof ownership and
  fingerprint checks, distinct reference counts, watermarks and filters match.
  Output retains 25 findings, two proofs per finding and ten endpoints. Coverage
  reads only the selected asset even with 500 sibling assets. Cases with 10,000
  missing references and concurrent proof mutation exercise bounded rendering and
  a consistent owner-bound snapshot. This is not a universal single-record or
  query-time resource bound, malformed JSON type parity or production latency SLO.
- Final graph/transfer/ownership subset: **44 passed in13.56s**
  (`artifacts/postgres-return-graph-targeted-final.txt`). Full backend with PG
  explicitly enabled: **497 passed in133.67s**, one existing Starlette/httpx warning
  (`artifacts/postgres-return-graph-backend-final.txt`). No UI edit or rebuild.
  Test corrections used the existing notes API and isolated the large-reference
  graph check from unrelated endpoint nodes; production limits were not weakened.
- Wheel SHA2565be9f75e9b822640aa912beecac27b1260c4fc1b61436c201eb015e8fc0f22ea
  byte-matches all50 service Python files. Outside-checkout installed package
  validates native graph, real dump/restore containing a session, session omission
  with source preservation, then starts the returned SQLite HTTP service and
  proves old-cookie refusal, preserved-password login, notes and persisted graph
  (`artifacts/postgres-return-graph-installed-review.json`,valid=true,
  target_requests=1,owned_lab_requests=1,external_target_requests=0,
  service_postgres_backend_enabled=false). An initial review script stopped before
  HTTP startup because its socket directory variable shadowed the socket module;
  the module alias fix and fresh full rerun passed using the same wheel.
- Same wheel's default installed HTTP/auth/UI/maintenance/release review passes
  (`artifacts/postgres-return-graph-runtime-review.json`,valid=true,target_requests=0).
  Successful runners stop/remove their disposable clusters and installations.
  Hosted CI execution remains unverified; its PG job now includes native graph.
- This is offline migration into a new SQLite database. Live PostgreSQL backup,
  full PostgreSQL operational restore, native HTTP selection, imports/reporting/
  bounded audit integration and whole service lifecycle QA remain required. The
  complete v1 gate remains open; no remote publication or external target request.
- Owned preview completed normal shutdown before restarting current code on8790
  (PID88314/session85734); `/api/health` and root HTTP200. Existing preview data
  retained. Initial preview probe of nonexistent `/healthz` returned404; the
  documented service health route succeeds.


### PostgreSQL complete report streams and cancellation

- Added explicit native report queries with named server-side cursors (batch32),
  complete scoped JSON/CSV/Markdown output and the same renderers as SQLite. One
  read-only repeatable-read transaction pins before the first byte and includes
  coverage/history lookup. Orphan evidence/traffic are excluded; task values are
  bound, including literal SQL-like IDs. CSV formula guards remain. The HTTP
  export route now accepts its Store rather than assuming a SQLite file path.
- Actual PostgreSQL tests compare all three scoped formats and full JSON against
  SQLite, with1005 findings/proofs/history/traffic each. Concurrent task/finding/
  coverage/history edits and a new proof do not enter the active snapshot. Native
  readonly refusal, invalid JSON failure, early synchronous/asynchronous close
  release connections. Export of6000 rows in each main collection exceeds12MB
  while Python traced peak stays below2MB; all six report cursors use batch32 and
  close. This does not prove server sorting memory, huge single-record bounds,
  long-lived snapshot vacuum behavior or production resource SLO.
- Native transaction permits set remaining-time statement_timeout and use a joined
  cancellation watcher. Actual pg_sleep(10) is interrupted by a .2-second permit
  and by ASGI2.0 disconnect, each under2 seconds. ASGI2.4 slow-send expiry releases
  connection and admission slot. No cancellation watcher remains. Killing the
  dedicated owner during an admitted report still fences replacement until the
  report closes; stale-owner future reports are refused. Connection establishment
  before the guard retains the existing5-second connection timeout. Remote network
  blackhole, old-libpq cancellation fallback, proxies and HA remain unverified.
- Native+SQLite report/export subset: **27 passed in14.37s**
  (`artifacts/postgres-reports-targeted.txt`). Full backend with explicit PG opt-in:
  **506 passed in144.57s**, one existing Starlette/httpx warning
  (`artifacts/postgres-reports-backend-final.txt`). No UI edits or rebuild.
- Wheel SHA2562ec9d5b5d9d759e366b8d4b2424cc3b0f8f93ed4e0cf052966bf0152cfad5723
  byte-matches all52 service Python files. Outside-checkout installed native Engine
  produces real persisted proofs and reads JSON/CSV/Markdown reports under runtime
  ownership, then completes ownership-loss/dump/restore/session-aware SQLite return
  and returned HTTP authentication/graph checks
  (`artifacts/postgres-reports-installed-review.json`,valid=true,target_requests=1,
  owned_lab_requests=1,external_target_requests=0,service_postgres_backend_enabled=false).
  Same wheel's default installed HTTP/auth/UI/maintenance/release checks pass
  (`artifacts/postgres-reports-runtime-review.json`,valid=true,target_requests=0).
  Successful runners stop/remove disposable clusters and installations. CI now
  includes native reports; hosted execution remains unverified.
- Full PostgreSQL service selection, import transactions, bounded audit review,
  startup/HTTP lifecycle and operational backup/restore remain required. No remote
  publication or external target/provider request; the complete v1 gate stays open.
- Owned preview completed normal shutdown before restarting current code on8790
  (PID3544/session42309); `/api/health` and root HTTP200. Existing workspace retained.


### PostgreSQL bounded administrator audit review

- AuditReview now accepts a Store or legacy SQLite path. HTTP construction passes
  its Store; native PostgreSQL uses one owner-aware readonly repeatable-read
  transaction and the shared chain verifier with named cursor batch32. Deadline
  checks cover SQL admission, each record and successful response return. Native
  query cancellation/statement_timeout use the previously tested transaction
  permit guard. SQLite keeps its readonly URI and SQL progress handler.
- Actual native tests cover empty and normal chains, prefix and invalid/future
  checkpoints, event edit/hash deletion/tail deletion/bad state/unsealed append,
  normal responses without event payloads, and unchanged raw manifests after
  verification or mismatch. A DELETE attempt in the review transaction is refused
  by PostgreSQL readonly enforcement; its transaction error becomes inconclusive
  and the original chain remains valid. Read failures and closed owners return
  generic inconclusive results without database SQL details. No repair or appended
  verification event is performed.
- Concurrent append stays outside the current snapshot and appears on the next
  review. Single-slot concurrency rejects a second invocation and permits a later
  retry. Actual pg_sleep(10) is interrupted by a .15-second deadline in under2s;
  connection, cancellation watcher and slot are released, followed by a successful
  fresh verification. An admitted review fences replacement after actual owner
  backend termination until the review finishes; future stale-owner reviews are
  inconclusive.10,000 actual chained events with2KB detail each use Python traced
  peak below2MB and a closed server cursor with batch32. This proves representative
  local cases, not remote network cancellation, server memory, huge single-event
  limits, long-lived vacuum effects or operational SLO.
- Native+SQLite review/audit subset: **39 passed in3.64s**
  (`artifacts/postgres-audit-review-targeted-final.txt`). No UI edits or rebuild.
- Wheel SHA256a6ff2fe38a052f5375bb218cab8c62df00a56e7b54a0d1fd2f08d911e9d1908b
  byte-matches all52 service Python files. Outside-checkout installed native Engine
  generates real proofs, reads native reports and verifies the audit against its
  checkpoint without appending records, then passes ownership/dump/restore/session
  return and returned HTTP checks
  (`artifacts/postgres-audit-review-installed-review.json`,valid=true,target_requests=1,
  owned_lab_requests=1,external_target_requests=0,service_postgres_backend_enabled=false).
  Same wheel's default installed HTTP/auth/readonly audit/maintenance/release checks
  pass (`artifacts/postgres-audit-review-runtime-review.json`,valid=true,target_requests=0).
  Successful runners stop/remove disposable clusters and installations. CI now
  includes native review tests; hosted execution remains unverified.
- Whole PostgreSQL HTTP Store selection/auth lifecycle/import/configuration and
  operational backup/restore remain required; PostgreSQL CLI audit selection and
  external checkpoint automation are not implemented. Complete v1 remains open.
  No remote publication or external target/provider requests.
- Final full backend with explicit PG opt-in: **519 passed in147.74s**, one
  existing Starlette/httpx warning (`artifacts/postgres-audit-review-backend-final.txt`).
- Owned preview completed normal shutdown before restarting current code on8790
  (PID17981/session33460); `/api/health` and root HTTP200. Existing workspace retained.


### PostgreSQL atomic ScopeSentry import and source request fencing

- Added explicit SQLite/PostgreSQL import operations. Preview expiry cleanup,
 50-preview admission, reviewed asset/source inspection and parent-child page
  updates use one Store write transaction. Apply validates the entire selected
  batch before strict asset/history inserts, source upsert, applied retry result
  and native audit append in the same serialized transaction. No shadow SQLite
  or SQL translator. Local asset metadata, earlier scope and pending task remain
  intact when source URL changes. Import never starts an execution task.
- Native representative results match SQLite with fixed IDs/clock. Tests cover
  reviewed fields and private-field exclusion, repeated files/two sources/shared
  URL, old-source history, same-selection retry, changed selection, actor ownership,
  unknown/duplicate selection, missing/expired previews, stale assets/source,
  archived/missing links and duplicate existing URL. Two Store instances applying
  the same review return one committed result; competing reviews yield one commit
  and one409.49 active previews allow only one of two concurrent new previews;
  expiry cleanup keeps the50 limit. These are cooperative local Store instances,
  not arbitrary raw SQL writers or a full multi-process service certification.
- Actual PostgreSQL trigger failure at audit hash insertion rolls back created
  assets, source history/current link, applied result and audit together; the raw
  manifest remains unchanged and the subsequent retry succeeds. Actual next-page
  preview INSERT failure rolls back its parent pointer too. Owned loopback source
  retry/resume/cache uses pages1,1,2,1,2 with no target requests or raw body/JWT
  persistence. Its50 selected assets are imported without creating tasks.
- Native source reads acquire execution permits before DNS/network handling.
  Unowned source collection refuses before a request. Actual owner backend
  termination during a held source POST blocks replacement until the admitted
  request ends, then refuses preview persistence and all future source/manual
  imports. No partial records are published. Source connections and local server
  threads are closed by their owned test fixtures.
- Native import subset: **12 passed in2.84s**
  (`artifacts/postgres-import-native-targeted.txt`). Existing SQLite import/remote/
  TLS subset: **50 passed in18.89s** (`artifacts/postgres-import-sqlite.txt`). One
  existing Starlette/httpx warning. No UI edits or rebuild.
- Wheel SHA256ce9fd89c41d039402168991e76741805afd43970b4192b8018746fb28dde2bee
  byte-matches all53 service Python files. Outside-checkout installed package
  performs one source POST against its owned synthetic server under runtime
  ownership, reviewed import, idempotent retry and changed-source history, then
  native graph/reports/audit/owner-loss/dump/restore/session return and returned
  HTTP checks (`artifacts/postgres-import-installed-review.json`,valid=true,
  target_requests=1,owned_lab_requests=1,owned_source_requests=1,
  external_target_requests=0,external_source_requests=0,service_postgres_backend_enabled=false).
  Same wheel's default installed HTTP/auth/UI/import/maintenance/release review
  passes (`artifacts/postgres-import-runtime-review.json`,valid=true,target_requests=0).
  Successful runners stop/remove disposable clusters and installations. CI now
  includes native import tests; hosted execution remains unverified.
- Native HTTP Store selection, full authentication/concurrent API/startup lifecycle,
  schema configuration/upgrade and operational backup/restore remain required.
  Actual external ScopeSentry operational source, database network fault timings,
  malformed record parity and long-term resource SLO remain unverified. Complete
  v1 stays open. No remote publication or external target/provider/source request.
- Final full backend with explicit PG opt-in: **531 passed in149.86s**, one
  existing Starlette/httpx warning (`artifacts/postgres-import-backend-final.txt`).
- Owned preview completed normal shutdown before restarting current code on8790
  (PID33670/session28978); `/api/health` and root HTTP200. Existing workspace retained.


### Configured PostgreSQL HTTP app and lifecycle

- HTTP server now selects SQLite by default or explicitly configured PostgreSQL
  via AEGIS_STORAGE_BACKEND, AEGIS_POSTGRES_DSN and AEGIS_POSTGRES_SCHEMA. Only a
  prepared supported schema is accepted; invalid backend/config/schema refuses
  without SQLite fallback or creating a local data directory. Native Engine
  acquires ownership before recovery. Duplicate app startup cannot recover a live
  task. Source configuration failure shuts Engine down and releases ownership.
  Native normal restart preserves sessions and interrupts unfinished task/call
  records without inventing lost outcomes. SQLite Engine startup failure now also
  releases its workspace lease.
- Replaced remaining inline HTTP SQLite operations with explicit named native/
  SQLite queries: active retry/retest lookup, coverage/severity overview, bounded
  literal assignee search and note deletion. Existing user-name constraint errors
  map to409 for either backend. Settings report the selected backend. Conversation
  summaries use Store read_transaction so task/findings/coverage/proofs share the
  native snapshot. Middleware database lookups and audit appends run in threadpool;
  native database/ownership errors return generic no-store503. Scheduler handles
  ownership refusal without issuing replacement writes or exposing SQL.
- Actual HTTP PostgreSQL tests cover fresh-schema setup, roles, duplicate users,
  ASCII-only search parity, notes, imports, audit review, usage, session logout,
  default policy, approval/no pre-approval target requests, actual owned lab
  execution, grounded recorded conversation, failing/passing and inconclusive
  retest, report secret redaction, rejected plans and atomic asset import. Restart
  retains cookie/note and recovers a running task and started call; duplicate
  startup is refused before recovery. Actual dedicated backend termination yields
  no-store503 on health/read/write. Startup config failures release ownership.
- Initial native HTTP run had3 failures/8 passes: two exposed conversation's old
  SQLite-only connection, which was replaced with the shared read transaction.
  The third came from the role fixture starting/stopping the same app lifespan
  twice; separate clients now share one running lifespan and have separate cookies.
  Final native HTTP+SQLite conversation subset: **26 passed in10.67s**
  (`artifacts/postgres-http-targeted-final.txt`). Full backend with PG opt-in:
  **542 passed in160.14s**, one existing Starlette/httpx warning
  (`artifacts/postgres-http-backend-final.txt`). No UI changes or rebuild.
- Wheel SHA256dcd8801f4c21d26f46e25ff854b2cefbd2b17fbc2f81b9a20a53a7590bf488ec
  byte-matches all54 service Python files. Outside-checkout installed package starts
  an actual native PostgreSQL HTTP server, checks authentication/operator role
  denial/settings/overview/assignees/note add-delete/graph/report/conversation/
  persisted pending plan/runtime/logout, stops cleanly and reads its final native
  manifest before real dump/restore and session-aware SQLite return. Initial
  review reached logout but called its POST-only route with GET; the script method
  fix and fresh full rerun pass using the same wheel
  (`artifacts/postgres-http-installed-review.json`,valid=true,target_requests=1,
  owned_lab_requests=1,owned_source_requests=1,external_target_requests=0,
  external_source_requests=0,service_postgres_backend_enabled=true).
- Same wheel's default installed SQLite HTTP/auth/UI/import/maintenance/release
  review passes (`artifacts/postgres-http-runtime-review.json`,valid=true,target_requests=0).
  Successful runners stop/remove disposable servers, clusters and installations;
  the failed review also terminated its server and cluster before retry. CI includes
  native HTTP cases; hosted execution remains unverified. README/config/architecture/
  operations/storage/readiness describe actual selection and separate SQLite CLI
  contracts. Native API success is not native browser/mobile journey verification.
- Complete v1 remains open: full native HTTP/auth/provider/SSE/scheduler failure and
  load combinations, schema upgrade, live PostgreSQL backup/operational restore,
  CLI/MCP native selection and broader product gates remain required. Remote DB
  network blackhole/proxy/HA/power loss and resource SLO are unverified. No remote
  publication or external target/provider/source request was performed.
- Owned default SQLite preview completed normal shutdown before restarting
  current code on8790 (PID61320/session26793); `/api/health` and root HTTP200.
  Existing workspace retained; no user workspace migration was performed.


### Native read-only MCP and audit CLI selection

- MCP uses the HTTP backend/DSN/schema environment selection. PostgreSQL reader
  composes native Store reads only; no Engine, recovery, schema creation, sessions,
  execution or approval is started. Unknown configuration/connection/schema refuses
  with sanitized startup stderr/code2 and never falls back to a local SQLite DB.
  Native runtime tool errors use the same fixed protocol error as SQLite.
- Each tool call now validates before opening a readonly snapshot, then reads its
  task/finding, coverage/proofs/retests/events and page counts on that connection.
  Both Store event_page methods accept an existing connection; default HTTP event
  behavior is preserved. Seven native tools compare with SQLite including literal
  filters, compact references and pages; missing legacy coverage remains not_recorded
  without writes.1200 proof/retest rows retain25-row detail and full counts.
  A concurrent foreign-asset edit is excluded from the active finding detail
  snapshot and excluded on the next call.512KiB serialized result refusal remains.
- Actual native SELECT-only login role has schema usage and record/event/hash/state/
  metadata SELECT, reads MCP/audit without users/sessions privileges, and is refused
  on DELETE and users SELECT. MCP denies unknown command/SQL/invalid arguments and
  does not expose authentication settings. Raw manifests before/after protocol
  reads remain unchanged. These are local role tests, not external MCP clients or
  protection against a DB administrator changing grants/raw records.
- Audit CLI accepts explicit --backend/--schema or the same backend environment;
  DSN remains environment-only. PostgreSQL --source is refused. SQLite retains
  explicit --source and now uses configured data directory when source is omitted.
  Actual child process exports a0600 checkpoint, compares its prefix after append,
  refuses overwrite without changing the file, rejects mismatched prefix/tampered
  event before output creation, and omits record/credential/error payloads.
- Initial subset had1 failure/43 passes because generated missing-coverage timestamps
  used a live clock while record clocks were fixed; the parity fixture now fixes
  the coverage observation clock too. Production output/limits were not altered.
  Final native+SQLite MCP/audit subset: **44 passed in6.95s**
  (`artifacts/postgres-readers-targeted-final.txt`). Full backend with PG opt-in:
  **549 passed in163.94s**, one existing Starlette/httpx warning
  (`artifacts/postgres-readers-backend-final.txt`). No UI edits or rebuild.
- Wheel SHA2568618e24e12e48d342b7328e65983e22d19097a5ce6068ab995431d73e4251ff0
  byte-matches all54 service Python files. Outside-checkout installed package
  completes native HTTP lifecycle, then actual MCP stdio initialize/task/command
  refusal and audit checkpoint export/compare before real dump/restore/session
  return and returned SQLite HTTP verification
  (`artifacts/postgres-readers-installed-review.json`,valid=true,target_requests=1,
  owned_lab_requests=1,owned_source_requests=1,external_target_requests=0,
  external_source_requests=0,service_postgres_backend_enabled=true). Same wheel's
  default installed HTTP/auth/UI/records/maintenance/release review
  passes (`artifacts/postgres-readers-runtime-review.json`,valid=true,target_requests=0).
  Successful runners stop/remove disposable clusters/installations. CI includes
  native reader cases; hosted execution remains unverified.
- Complete v1 stays open: live PostgreSQL backup/operational restore/schema upgrade,
  full native HTTP/provider/SSE/scheduler/failure/load combinations and broader
  product gates remain required. Remote MCP client, external checkpoint automation,
  huge record memory limits, remote DB faults and resource SLO remain unverified.
  No remote publication or external target/provider/source request was performed.
- Owned default SQLite preview completed normal shutdown before restarting
  current code on8790 (PID80736/session30994); `/api/health` and root HTTP200.
  Existing workspace retained; no user workspace migration was performed.


## Native PostgreSQL online logical backup and fresh-schema restore

- Added a data-only ZIP_STORED format for the supported schema2. Backup uses one
  read-only REPEATABLE READ native snapshot and server cursors(batch32), preserves
  raw record JSON/credential hashes/audit links/identity allocation gaps, omits
  sessions and leaves source cookies valid. No SQLite staging database or archive
  SQL is executed. A closed, verified0600 stage is fsynced and hard-linked without
  overwrite, then its parent is fsynced. Stages are removed on success/failure.
  A directory fsync failure after publication can leave the verified output;
  this is documented rather than claiming all errors imply no output.
- Restore verifies archive frames/audit and optional independent audit prefix
  before opening target DB. Only a new quoted schema is accepted, under the
  exclusive native runtime gate. Reviewed DDL/bound COPY, storage metadata and
  sequence restoration, native audit/typed-row hash verification share one
  transaction; precommit failures roll back every new object. Existing schemas
  are never overwritten. A lost commit acknowledgment remains ambiguous and
  requires checking the target schema; commands do not switch running services.
- Actual owned DB cases cover a write after snapshot while a live owner holds
  admission, source-cookie preservation/copy invalidation, exact raw-row manifests,
  sequence gaps, existing schema/live-owner refusal, post-COPY rollback, concurrent
  output creators, and read transaction exit failure before publication. Damaged
  frames/audit/missing/extra/duplicate/compressed members, wrong sequence/scalar/
  record JSON/canonical encoding, oversized line/metadata, non-ZIP and mismatched
  external checkpoint are refused. Checkpoints authenticate only an audit prefix,
  not all archive content; frame hashes are not signatures.
- Real PostgreSQL HTTP backup while source runs, restore to another schema, then
  recovered HTTP login: old cookie401, original password accepted, unfinished task
  and started call interrupted, pending plan remains pending, owned target handler
  receives zero requests. Source live cookie/task state remain unchanged by copy
  restoration. Backend CLI defaults follow configured environment; DSN is only
  environment-based. Actual subprocesses check archive without DB configuration,
  restore, refuse incompatible SQLite path flags/occupied schema, sanitize failed
  DSN/user/password errors, and never create a local SQLite fallback directory.
- Initial subset:1 failed/22 passed because verification reused a closed owner-bound
  Store. Fixture now creates a fresh independent reader after owner shutdown;
  production fencing was retained. Final new+SQLite backup+transfer subset:
  **43 passed in7.12s** (`artifacts/postgres-backups-targeted-final.txt`). Complete
  backend with native PG opt-in: **570 passed in170.29s**, one existing
  Starlette/httpx warning (`artifacts/postgres-backups-backend-final.txt`). UI
  remains unchanged and was not rebuilt.
- Wheel SHA256d5ccc97eab3d5bca61c2dec3da3773b07cf16734ed37d2dcca288728c4f7ef66
  byte-matches all55 service Python files. Outside-checkout installed review passes
  (`artifacts/postgres-backups-installed-review.json`,valid=true): installed live
  native HTTP backup, no-DB archive/checkpoint verification, fresh-schema restore,
  source manual cookie preserved/copy cookies invalid, actual restored native
  HTTP password login/pending plan/reports/graph, then existing MCP/audit CLI,
  real pg_dump/pg_restore/session-preserving source and SQLite return checks.
  Owned target requests1 and owned source POST1, external target/source0. Default
  installed SQLite/runtime/auth/UI/maintenance/release review of the same wheel
  also passes (`artifacts/postgres-backups-runtime-review.json`,valid=true,
  target_requests=0). Both disposable installed clusters/environments are stopped
  and removed. CI includes new native cases; hosted execution remains unverified.
- Scope is supported Open Aegis logical data, not roles/extensions/functions/
  triggers/full instance/WAL/PITR/HA. Row4MiB and metadata64KiB bounds are enforced;
  arbitrary hostile ZIP central-directory resources, remote faults/commit loss,
  power failure, huge archives/server snapshot effects, native version upgrade
  and full operating SLO remain unverified. Native release/update/config switching
  and broader v1 UI/tool/resource gates remain open. No remote publication or
  external target/provider/source request occurred.
- Default SQLite preview completed normal shutdown, retained its workspace, and
  restarted current code on8790 (PID11016/session32193). Health/root HTTP200.


## Fresh native PostgreSQL initialization and first service setup

- Added installed `aegis-init-postgres` and native bootstrap, without creating or
  transferring a temporary SQLite workspace. Reviewed DDL, new random audit chain
  ID/genesis, schema2 metadata and empty-row/audit verification share one transaction.
  Same exclusive runtime admission key is checked before DDL; existing schemas
  (including empty ones), active owners and competing initialization are refused.
  Precommit DDL/verification errors roll back new schema/tables/identities together;
  ambiguous lost commit acknowledgment still requires checking actual target state.
- Extracted exactly the existing reviewed schema DDL into a common creator used by
  initialization, SQLite→PG transfer and native archive restore. Each caller keeps
  its own transaction/admission contract. No arbitrary supplied DDL, administrator
  auto-creation, service start, execution or database/role/TLS provisioning occurs.
  CLI DSN is environment-only, schema can be explicit or configured, and expected
  failures exit2 without connection/user/password/SQL traceback payloads.
- Actual owned PG cases check empty genesis and first record/event IDs1, native
  backup/restore after initialization, concurrent creators/one winner, preservation
  of existing note/audit data, live-owner refusal, DDL/audit/manifest failure rollback
  and successful retry. New HTTP first setup requires configured token, rejects
  missing token403 and repeated setup409, protects anonymous API401, authenticates,
  creates a pending owned-lab plan with zero target requests and retains cookie/
  pending state on restart. Local SQLite directory is never created.
- Ordinary login role is NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOINHERIT; database
  CONNECT/CREATE allows initialization and role owns the schema. CREATE is revoked
  before real HTTP setup/note/audit validation, which still succeeds. A role lacking
  database CREATE is refused before leaving any objects. These are owned local
  PostgreSQL16.15 tests, not arbitrary production grant/role/TLS configurations.
- Final initializer+native backup+transfer subset **50 passed in9.17s**
  (`artifacts/postgres-bootstrap-targeted-final.txt`). Complete backend with native
  opt-in **579 passed in172.70s**, one existing Starlette/httpx warning
  (`artifacts/postgres-bootstrap-backend-final.txt`). UI unchanged, no UI rebuild.
- Wheel SHA2564dacc52066f35919ad2fb7b786ae7ec98c578a563e6bde9b281e6cc9e9531142
  byte-matches all57 service Python files and contains the new console entry point.
  Outside-checkout installed native review passes
  (`artifacts/postgres-bootstrap-installed-review.json`,valid=true): actual initializer
  under ordinary DB role, database CREATE revocation, fresh native HTTP setup token,
  authenticated note/audit with no SQLite, plus previous approved owned execution,
  graph/report/import/owner fencing, live backup/native restore, MCP/checkpoint,
  real dump/restore and SQLite return. Owned target requests1, owned source POST1,
  external target/source0. Same wheel's default runtime/install/HTTP/auth/UI/
  maintenance/release review passes with **seven CLI help entry points**, including
  native init help without the optional PostgreSQL dependency
  (`artifacts/postgres-bootstrap-runtime-review.json`,valid=true,target_requests=0).
  Installed runners stop/remove temporary clusters and environments. New native
  tests included in CI; hosted execution remains unverified.
- Local editable package was reinstalled without dependency changes; new CLI help
  and pip check pass. Operators still provision DB/TLS/roles and optional dependency;
  installed CLI does not automatically load .env. Existing native workspace upgrade,
  signed PostgreSQL update preflight/version/config transition, full native operating
  failures/long load and broader v1 UI/tool/resource gates remain open. No external
  publication, target/provider/source request or existing user DB mutation occurred.
- Default SQLite preview completed normal shutdown and restarted latest code on8790
  (PID33701/session55447); health and root HTTP200. Existing workspace retained.


## Signed PostgreSQL compatibility and stopped update preflight — initial pass

- Release create accepts optional PostgreSQL dependency lock. With it, format2
  signs native storage format/read schema2–2/write2/fixed lock path plus complete
  payload hashes; without it, format1 SQLite bundles remain unchanged. Verifier
  accepts both formats, checks exact native field/range/int contracts and requires
  the signed optional lock payload. Old format1 verifiers do not accept format2;
  producer declarations do not prove wheel/source identity or operational safety.
- Native prepare validates trusted-key signature/full payload/explicit native
  compatibility before DB use. A read-only READ COMMITTED connection holds the
  exclusive runtime transaction gate throughout checks and backup. This avoids
  pinning a historical snapshot before admission; separate native backup owns its
  consistent read-only REPEATABLE READ snapshot. Checks refuse owners/protected
  operations/cooperative writers, unsupported schema/objects/audit, queued/running/
  stopping tasks; captured backup task shapes/states are checked again before receipt.
  Raw SQL/admin edits are outside the cooperative exclusion contract.
- Private0700 stage holds a verified0600 before-update.zip and0600 preflight.json.
  Only after successful DB transaction exit are files linked into a new0700 output;
  files/output/parent are fsynced. Existing/concurrently created output is preserved.
  Handled publication failure removes the command's created output and stage;
  process/power loss can leave partial output and remains unverified. Shared digest
  limits preflight archive to2GiB. Receipt records backend/schema, release/revision,
  signer/manifest digest, backup digest/metadata and target write schema, installed=false;
  no temporary output paths or DSN are included. Receipt itself is not signed.
- Actual owned PG cases preserve source raw manifests/cookie, restore exact records/
  credentials/audit into a fresh schema with invalid copied cookie; reject live
  owner, unfinished tasks, legacy bundle, incompatible declared range and damaged
  audit without published files. Native dependency mutation and malformed signed
  declarations fail. Injected backup/read transaction exit/receipt publication
  failures clean up; a competing output marker survives. A new owner is refused
  during backup then succeeds after gate release. Actual native prepare child CLI
  follows configured backend/schema, refuses SQLite database flag and sanitizes
  user/password/connection failures without SQLite fallback or traceback.
- Native release+SQLite release+native backup subset **55 passed in8.81s**
  (`artifacts/postgres-release-targeted-final.txt`). Complete backend with PG opt-in
  **598 passed in174.51s**, one existing Starlette/httpx warning
  (`artifacts/postgres-release-backend-final.txt`). UI unchanged, no UI rebuild.
- Wheel SHA2567b0487b1bea40dbe74d1c7dd7df2daa531b8db1d3445c26ba1b3068a8db96262
  byte-matches all57 service Python files. Outside-checkout installed native review
  passes (`artifacts/postgres-release-installed-review-final.json`,valid=true):
  installed create/verify format2 with ephemeral Ed25519 keys and real locked
  dependency files, stopped native prepare, archive restore and exact native
  source/copy manifest/audit comparison with source cookie maintained/copy cookie
  invalidated. The ordinary bootstrap role also performs prepare after database
  CREATE revocation. Signed UI and revision inputs here are explicitly synthetic
  contract fixtures, not a new product UI/official source identity or publication.
  Existing installed initializer/native HTTP/approval/import/graph/report/ownership/
  MCP/audit/live backup/restore/dump/SQLite return checks remain passing. Owned
  target requests1, owned source POST1, external validation target/source0.
- Same wheel's default installed runtime/UI/auth/seven CLI/SQLite backup/restore/
  format1 release review passes (`artifacts/postgres-release-runtime-review.json`,
  valid=true,target_requests=0). Initial installed native review also passed before
  adding the unresolved ordinary-role permission check; final review reran native
  installed workflow for that added case. Successful runners stop/remove temporary
  clusters/environments. CI includes native release cases; hosted runs unverified.
- No bundle is installed by prepare, no source schema/data/session is mutated and
  no operational config/service switch occurs. Real different-version/schema/
  settings/UI upgrade and failed native startup rollback, official signing key
  distribution/rotation, containers/power/remote faults/load remain open v1 gates.
  Broader UI/tool/resource/AI gates remain open. No remote publication or external
  validation target/provider/source request occurred.
- Default SQLite preview completed normal shutdown, retained its workspace and
  restarted current code on8790 (PID63100/session82952); health/root HTTP200.


## Schema downgrade refusal and final native preflight regression

- Review found that a read-compatible declaration could still name a lower target
  write schema. Both SQLite and PostgreSQL prepare now refuse that declaration
  before creating/publishing a backup. Signature/shape validity does not authorize
  a schema downgrade. Genuine migration/version/config/operational transition
  remains a separate unfinished release gate.
- Reproduced previous committed SQLite behavior using the actual releases.py from
  debe3b3 in an isolated Python module, with the same new signed fixture test:
  source schema2/read0–2/write1 was accepted, yielding **1 failed / DID NOT RAISE
  ReleaseError** (`artifacts/postgres-release-downgrade-before.txt`). Current SQLite
  and real PostgreSQL cases refuse the lower write schema. No production DB or
  workspace was used for reproduction.
- Final release/native-backup subset **57 passed in9.26s**
  (`artifacts/postgres-release-downgrade-targeted-final.txt`). Full backend rerun
  after the guard **600 passed in174.97s**, one existing Starlette/httpx warning
  (`artifacts/postgres-release-downgrade-backend-final.txt`). Rerun was required by
  the newly found compatibility gap; initial598-pass run is not final evidence.
- Rebuilt wheel SHA256dea00a28c6131db44b607988e39c4c4a87771c195003130158b68476f515dee8
  matches all57 service Python files. Native installed workflow, including signed
  native declaration/preflight/backup restore and ordinary role after CREATE
  revocation, passes (`artifacts/postgres-release-downgrade-installed-review.json`,
  valid=true,owned_lab_requests=1,owned_source_requests=1,external_target_requests=0,
  external_source_requests=0). Same final wheel's installed default SQLite/runtime/
  UI/maintenance/format1 release checks pass
  (`artifacts/postgres-release-downgrade-runtime-review.json`,valid=true,
  target_requests=0). Successful runners remove owned disposable clusters/envs.
- No UI edits/rebuild or remote publication. All broader v1 and actual native
  different-version/schema/config/startup-failure transition gates remain open.
  Default SQLite preview completed normal shutdown and restarted final code on8790
  (PID79857/session80496), retained its workspace; health/root HTTP200.


## Different installed version/UI/config transition and startup rollback

- Prepared local prerelease **0.2.0a1** (private UI package0.2.0-alpha.1), without
  declaring v1/official publication. Python package/runtime/MCP now report the same
  installed version; MCP's literal0.1.0 was replaced with package version. UI uses
  actual settings version and an unknown-version label before it is available,
  rather than inventing0.1.0. Release metadata fixtures use actual package version.
- Captured prior built UI before rebuilding: old JS index-cPS8RbeC.js, candidate
  index-DJrtcSWq.js; CSS remains index-DniDnrrf.css. Final frontend **67 passed in
  474.29ms** (`artifacts/version-candidate-frontend-tests-final.txt`), final TypeScript/
  Vite build passes (`artifacts/version-candidate-frontend-build-final.txt`). Source
  release/MCP subset **28 passed in1.67s** (`artifacts/version-candidate-targeted.txt`),
  full backend with owned PG opt-in **600 passed in174.86s**, one existing Starlette/
  httpx warning (`artifacts/version-candidate-backend-final.txt`).
- Old wheel SHA256dea00a28c6131db44b607988e39c4c4a87771c195003130158b68476f515dee8
  matches all57 Python files from authoritative git archive10ded2b5e78b338aaad5def57a196693dd691783
  (`artifacts/version-transition-old-source-proof.json`). Candidate wheel
  SHA256700406723d95f30a799e07647efc87d93c78b4fd9504f4324ef2aa3b8d07db63 matches all57
  current Python files at candidate source revision8bc19f2dde54f409de272264507f0e1aa65ac324
  (`artifacts/version-candidate-source-proof.json`). This is independent source-byte
  evidence; create CLI itself still does not prove a supplied revision's identity.
- Enhanced installed transition rehearsal for SQLite/PG, distinct old/new UI input,
  each artifact's own signing CLI, actual HTTP/MCP version assertions and exact
  served index/JS/CSS comparisons. PG uses an owned disposable Unix-socket cluster
  and installed old initializer; all server sockets are inherited bound descriptors.
  Fault injection writes through app.state.store, so PG failure is an actual native
  write under its owner rather than an unrelated SQLite file.
- **Both actual transitions pass** (`artifacts/version-transition-postgres.json`,
  `artifacts/version-transition-sqlite.json`):0.1.0→0.2.0a1→policy restart→failed
  startup→recovered0.1.0. Both valid=true,same_version=false,shared_ui_input=false,
  changed_execution_budget=true,target_requests=0,private_key_removed=true.
  Initial/candidate/policy-restart/recovered processes exit-15 with cleanup and
  owner/lease release; injected pre-readiness startup exits3, serves no HTTP, leaves
  its committed fault note and releases ownership.
- Execution budget24→candidate12, old package contract approval409 without execution;
  a newly created candidate plan is refused after same candidate restart at6 with
  explicit changed-policy reason. Candidate notes/plan/fault note are removed from
  the restored workspace, original asset/plan/note retained, old cookie401 and
  original password login accepted, prior version/UI/budget24 selected. PG restores
  into fresh owned_recovered while original owned_transition retains later notes/
  fault/source cookie; SQLite preserves its pre-restore DB. Audit and zero target
  request checks pass; plans remain pending throughout. No production workspace,
  target/provider or remote source is involved.
- Candidate's existing installed native initializer/HTTP/owned approval/import/
  graph/report/ownership/live backup/native restore/MCP/audit/signature/preflight/
  dump/SQLite-return review passes
  (`artifacts/version-candidate-installed-postgres-review.json`,valid=true,
  owned_lab_requests=1,owned_source_requests=1,external_target_requests=0,
  external_source_requests=0). Default installed runtime/UI/auth/seven CLI/maintenance/
  release checks pass (`artifacts/version-candidate-installed-runtime-review.json`,
  valid=true,target_requests=0). Successful runners stop/remove temporary clusters,
  environments, data and signing keys.
- Both database schemas remain2 and runtime/PG dependency locks are shared. This
  proves these different package versions, small UI change and selected runtime
  budget changes, not arbitrary breaking UI/config/dependency/schema migrations.
  Different-schema migration, auto service switching, official keys/publication,
  containers/power/remote fault/load, full browser/mobile/accessibility and other
  v1 tool/AI/resource gates remain open. No remote publish/push was performed.
- Local editable distribution now matches runtime0.2.0a1. Preview's0.1.0 process
  completed normal shutdown and current candidate restarted on8790 (PID28802/
  session84430). Health/root HTTP200; existing workspace/session/schema retained.
  Old pending contracts were not rewritten and require current reviewed replan.

## Concurrent HTTP body admission (2026-10-04)

- Added a process-local limit of 16 concurrent body readers before application/JSON
  entry. Full slots reject immediately with503/Retry-After1 without reading the
  rejected body. Existing2MiB/30s caps remain. Success, streamed oversize,
  disconnect, timeout and cancellation release reader admission.
- Body limit tests:7passed0.50s, including recovery after cancellation/disconnect/
  timeout and413. Full default-backend run completed447passed155skipped115.62s
  (`artifacts/body-reader-backend.txt`); that run collected before the final
  standalone oversize-recovery test was added. All7 body tests then passed.
  Native PostgreSQL HTTP suite explicitly enabled:11passed9.21s
  (`artifacts/body-reader-postgres-http.txt`). Existing Starlette/httpx deprecation
  warning remains. Skipped native suites were not counted as passing.
- Actual owned loopback Uvicorn with16partial-body sockets and2s shortened receive
  timeout: excessrequest503/Retry-After1, all16readers408, subsequentrequest200,
  serverthreadterminated; targetrequests0 (`artifacts/body-reader-http-review.json`).
  This tests receive admission only, not total memory/connections/downstream work
  limits or a default30s/long soak. No Docker/Colima/Podman executable was found;
  actual container verification and other v1 gates remain open.

## Append-only audit checkpoint archive (2026-10-04)

- Added `aegis-checkpoint` (eighth CLI) for scheduler-driven captures to an
  operator-specified independent directory. Each capture validates the whole
  read-only SQLite/native PostgreSQL snapshot against the latest archived head
  before publication. Same head is a successful no-op; new0600 files use canonical
  chain/seq/hash names, fsynced stage and non-overwriting hardlink publication.
  A process-level flock rejects concurrent captures; dirfd/no-follow operations,
  bounded checkpoint reads, one-chain/seq conflict checks and10000file limit
  protect the local archive contract. No existing checkpoint is pruned or repaired.
- Final archive/audit/native targeted suite:41passed1.85s
  (`artifacts/checkpoint-archive-tests-final.txt`). Tests cover actual CLI repeated
  captures, payload non-disclosure, valid complete rewrite/truncation detection
  against the prior external head, corruption/symlink/branch refusal, concurrent
  capture and retry, file-sync/link/verification failures, stage collision preservation,
  capacity without pruning, and the complete-file outcome of post-link dirsync failure.
- Candidate wheel SHA2563d959b998a158e4935e5f044a339215ff0c72dd268e8e2e2ce9b4e32dd3ad7
  contains all59 service Python files matching current source
  (`artifacts/checkpoint-archive-source-proof.json`). Outside-checkout installed
  runtime/UI/auth/eight CLI/backup/restore/audit/release checks pass, including actual
  installed SQLite capture/idempotent repeat/tampered DB refusal
  (`artifacts/checkpoint-archive-installed-review.json`,valid=true,target_requests=0).
- Installed native reviewer also verifies actual PostgreSQL checkpoint creation,
  repeat no-op0600 and unchanged audit snapshot along with existing native workflows
  (`artifacts/checkpoint-archive-installed-postgres.json`,valid=true,
  owned_lab_requests=1,owned_source_requests=1,external_target_requests=0,
  external_source_requests=0). Temporary environments/owned clusters stop and clean;
  both review stderr files are empty. Neither reviewer contacts external targets.
- First concurrent full run had620passed/1failed: the package contract cached the
  source fingerprint while this implementation was still being edited; its direct
  recomputation correctly saw changed source. Stable-source single failing test
  passed immediately. Final complete native-enabled suite is rerun after source freeze;
  that first failed run is not treated as passing evidence.
- This command enables repetition by an operator's scheduler, not an installed
  automatic job or proof of independent immutable custody. Documentation includes
  a cron example; no user's OS job or remote mount/account was created. Actual
  independent storage/scheduling, signing/WORM, alerts/continuous UI status,
  network filesystem and power-loss durability, whole v1 gates remain open.
- Stable final source: complete SQLite+native PostgreSQL backend suite622passed
  175.78s (`artifacts/checkpoint-archive-backend-final.txt`), no skips; one existing
  Starlette/httpx warning. Final editable package reinstall completed and the new
  `aegis-checkpoint --help` entry point succeeds. Preview's prior PID44273 completed
  normal lifespan shutdown before restarting with the existing data directory.

## Container preparation and actual loopback probe (2026-10-04)

- Replaced fixed-port urllib Docker health check with installed `aegis.healthcheck`:
  direct127.0.0.1/configured port and Host, no proxy/redirect, bounded4096byte JSON,
  required HTTP200/ok/current runtime version, socket3s/image health5s. Twelve actual
  loopback fixture tests cover configured port/Host, ignored proxy, redirect/status/
  body/version failures and invalid port refusal. New probe + existing HTTP/body
  suite50passed13.69s (`artifacts/container-probe-tests.txt`); code-fingerprint/
  execution contract suite17passed5.35s (`artifacts/container-contract-tests.txt`).
- Image optional `AEGIS_INSTALL_POSTGRES=1` uses the existing exact PostgreSQL lock;
  default remains SQLite. Compose now passes storage DSN/schema and optional chat/
  price/source/export settings. No DB service or automatic schema creation added.
  Added owned Docker reviewer for build/nonroot/read-only/health/UI/auth, synthetic
  pending plan, cookie/data restart, checkpoint repeat, stopped-volume restore,
  old-session refusal/password/data retention and target requests0, with owned
  cleanup. Added a CI job for default/PG-driver images. The PG image rehearsal still
  uses SQLite HTTP/restore; it does not verify native PostgreSQL in containers.
- Docker/Colima/Podman executables remain absent. Actual reviewer exits2 before any
  resource creation (`artifacts/container-review-unavailable.err`). Script compile,
  Compose/CI YAML parsing and correctly joined Docker RUN shell syntax pass.
  An initial validation helper mistakenly removed the RUN continuation while keeping
  newlines and reported a shell syntax error; joining the actual continued command
  correctly passes. This is not image-build evidence. Actual Docker/hosted CI,
  volume permissions, port/internal network behavior, restore/cleanup, PG-container
  and multi-architecture gates remain open. Docker official network-create and
  port-publishing docs were read; their described behavior is not local execution proof.
- All60 Python files in the candidate wheel match source
  (`artifacts/container-candidate-source-proof.json`). Installed outside-checkout
  runtime/UI/auth/eight CLI/maintenance/release review passes, now explicitly invokes
  the installed probe against the actual owned server's assigned port
  (`artifacts/container-candidate-installed-review.json`,valid=true,target_requests=0).
  Actual current local preview probe on8790 also exits0. No external target review,
  deployment or remote publish/push performed. No whole-backend rerun is claimed
  for these deployment/probe-only changes; affected suites and installed workflow
  are the recorded validation scope.

## Worker link history and provenance pages (2026-10-04)

- Reproduced the overwrite against the unchanged prior implementation using two
  actually approved owned loopback tasks on the same asset: the first task lost
  its observation, second retained it (`artifacts/worker-observation-before.txt`,
  one meaningful failing test). After fixing ID identity to task/asset/check/URL,
  both retain distinct records for the same link, two base requests only; passed
  (`artifacts/worker-observation-after.txt`). Existing legacy records are not
  rewritten and previously overwritten history cannot be recovered automatically.
- Persisted Worker/task/asset/check/version/scope URL/revision/package metadata;
  added authenticated task-local HTTP and eighth read-only MCP tool with bounded
  SQL pages/search and one source/records read snapshot. `matched` checks stored
  approval metadata consistency, not signed provenance, Worker identity, endpoint
  access or validation success. Historical approval scope survives current asset
  changes; legacy/altered metadata remains visible as unconfirmed, other task
  records excluded. Observation reading grants no execution/approval or target
  request. UI wording now reflects each record's task instead of “latest task”.
- Final targeted HTTP/history/native execution/MCP/readers46passed13.52s
  (`artifacts/worker-observation-mcp-tests.txt`); full native-enabled backend suite
  644passed183.93s, no skips (`artifacts/worker-observation-backend-final.txt`). One
  existing Starlette/httpx warning. Frontend67passed420.79ms; production build1.58s
  (`artifacts/worker-observation-frontend-tests.txt`/`...frontend-build.txt`), final
  JSindex-D-WjoRbB/CSSindex-DniDnrrf. Wording-only UI change is not full visual/
  mobile/accessibility journey verification.
- Wheel SHA25631aa688ee98848270ecff5c6cabe97ebe69017d0e63893ba685506563eb11cde
  has all61 service Python files matching final source
  (`artifacts/worker-observation-source-proof.json`). Installed native reviewer now
  serves owned HTML with a link, runs approved security_headers+endpoint_inventory,
  and verifies source-matched Worker record through native Store, actual HTTP and
  MCP stdio. Exactly one owned base GET and one owned source POST, no observed-link
  visit or external target/source request. Full existing native/backup/restore/
  audit/signature/preflight/return workflows also pass
  (`artifacts/worker-observation-installed-postgres.json`,valid=true,external0).
- Default installed runtime/UI/auth/eight CLI/maintenance/release/probe workflows
  also pass (`artifacts/worker-observation-installed-runtime.json`,valid=true,
  target_requests=0). Both runners terminated and cleaned temporary environments/
  owned PostgreSQL cluster; stderr files empty. CI native test list includes new
  Worker tests; hosted execution remains unverified. Repeated planning/dependency
  steps, automatic Worker consumption, dedicated detail UI and whole v1 remain open.

## Worker observation detail UI — 2026-10-04

- Observation list source-task buttons open detail while retaining list search/page;
  missing source task disables the button. Task detail has independent observation
  search/25-item pagination/bookmark state, matched/unconfirmed metadata, timestamps
  and native keyboard-expandable provenance. Observed URLs remain text values.
- Frontend68passed480.47ms; production build1.44s, JSindex-CcUhf-wd and
  CSSindex-DniDnrrf (`artifacts/observation-ui-tests.txt`, `...ui-build.txt`). Added
  URL isolation/close/task-change test. Service Python files unchanged; historical
  backend644 result above was not rerun or relabeled for this frontend-only change.
- Owned synthetic fixture60 current links plus legacy/missing-source records:
  keyboard Enter source open; page2/search preserved; new-tab bookmark restored;
  Escape closed and returned focus to source button. Actual iframe documents390px
  (scroll390/dialog366) and320px (scroll320/dialog296), including native keyboard
  metadata expansion with no document overflow. Viewport emulation returned success
  but document remained1810px, so these are same-origin fixture iframe checks,
  not actual-device/touch/zoom/screen-reader verification. Production frame policy
  unchanged. Final rebuilt390 screenshot retaken after fresh fixture/login.
- Synthetic503 shows error and distinguishes retained stale data. New-search failure
  presents retry; manual retry after flag removal restored10 matching records. A
  first retry attempt found no button after automatic polling recovered, and another
  stale-data state correctly used the existing latest-list control. Only the final
  explicit new-search retry counts as manual-success evidence.
- Artifacts: `observation-ui-review.json`, `observation-ui-http-smoke.json`,
  `observation-ui-desktop.jpg`, `observation-ui-320.jpg`, `observation-ui-390.jpg`.
  Initial fixture startup used an invalid Store method, corrected before QA. Two
  earlier SIGTERM runs exposed temporary cleanup outside Uvicorn's lifespan; their
  synthetic DB/task/zero-traffic identity was checked before removal. Final fixture
  shutdown now checks zero target requests and cleans data inside lifespan. Default
  no-failure-flag mode also serves the frame with correct same-origin child headers.
  Real preview8790 remains healthy and serves final bundle with DENY framing.
- This completes the dedicated observation panel subset, not repeated Planner,
  Worker dependency/consumption, full accessibility/mobile QA or the full v1 gate.

## Worker process sharing reads — 2026-10-04

- Added task/asset Worker process list/detail and bounded event/observation pages in
  authenticated HTTP; three read-only MCP tools now expose the same process. One
  read transaction covers approval scope, expected coverage cells and latest25
  events/observations each. SQL task/asset filtering excludes other Workers/tasks
  and Planner events. New execution events retain Worker ID. Historical metadata
  remains unconfirmed; missing/mismatched coverage never becomes completed.
- Actual owned SQLite and native PostgreSQL execution verifies per-check completed
  coverage, Worker events and source-matched observed link, with one base GET only
  and no observed-link visit. Native parity checks pages/search, concurrent source/
  observation changes, and string-only asset identity (boolean JSON does not match).
  Viewer GET, anonymous401, unknown Worker404, page bounds, read-only MCP refusals,
  unbounded-history prohibition and audit preservation also verified.
- Related final tests34passed6.10s (`artifacts/worker-process-identity-after.txt`).
  Initial full run had653passes and one old fixed8-tool catalog expectation;
  changed it to an exact11-tool name set. Next full run654passed186.90s before
  additional identity hardening (`...backend-before-identity.txt`). Inspection then
  found a stored-key/payload-ID mismatch could redirect process history; actual
  tampered SQLite API test failed200 vs404 before the fix (`...identity-before.txt`).
  Added source identity guard and actual SQLite/PostgreSQL mismatch refusals.
- Final native-enabled full backend657passed187.53s, no skips
  (`artifacts/worker-process-backend-final.txt`). One existing Starlette/httpx
  deprecation warning. Source remained frozen during this final run.
- Final wheel SHA256a010cde05a2edc2e34c197b0489778c6aaaa789da8baeafc4310c3abc831b6c8
  contains all62 service Python files matching source
  (`artifacts/worker-process-source-proof.json`). Initial no-build-isolation wheel
  attempt lacked bdist_wheel; normal isolated build succeeded. Final installed
  native reviewer verifies process via Store, actual HTTP and real MCP stdio,
  existing native backup/restore/audit/source/owner/release/return workflows too
  (`...installed-postgres.json`,valid=true,external target/source0). Default installed
  runtime also valid with target_requests0 (`...installed-runtime.json`). Both runners
  terminal0 with empty stderr and removed temporary installations/clusters.
- UI source/build unchanged this turn; previous68 frontend tests are historical,
  not a newly rerun visual suite. Preview restarted gracefully on final code and
  port8790 health200 (`...preview-health.json`). CI native list includes process
  tests; hosted CI and real container execution remain unverified.
- Dedicated whole-workspace process search UI, automatic repeated planning,
  dependent Worker consumption, shared to-do and the whole v1 remain open. The
  process read contract is [WORKER-PROCESS.md](WORKER-PROCESS.md).

## Approved Worker dependency execution — 2026-10-04

- Added bounded task-local acyclic dependency declarations (20 assets/40 edges),
  creation/approval/run validation and persisted approval contract. Ready Workers
  use the declared pool size; joins wait for all predecessors, independent Workers
  progress in parallel. Persisted expected coverage/approval scope/contracts are
  read in one snapshot before admitting a dependent. Handoffs retain completed
  checks and up to10 matched observation IDs from latest25, totals/omission state;
  reading references adds no observed-link requests or execution scope.
- Actual owned SQLite/PostgreSQL HTTP verifies no execution before approval, reversed
  input-order dependency scheduling, two-parent join and independent parallelism,
  failed parent/descendant blocking, cyclic/self/foreign/duplicate/type refusals,
  changed approval contract refusal before requests, corrupted completed coverage
  refusal, stop and replan preserving relationships with new pending approval.
  Initial failed-parent test expected one request but existing GET retry policy
  legitimately made two; assertion corrected to exact two parent-only requests.
- Controlled real held-HTTP stop ordering exposed stopped task done0 after its
  running Worker exited (`artifacts/worker-dependencies-stop-before.txt`,failed).
  Scheduler now stops scheduling, drains running outcomes and records done1 while
  cancelling unstarted dependent without a child request. Related final SQLite/
  native/runtime/tool tests65passed37.77s (`...targeted-final.txt`).
- Initial full run679passes/2failures was started while Vite rebuilt dist; backup
  app startup observed the temporary missing assets directory (`...backend-first.txt`).
  Fixed verification order, froze service source and built assets for final run:
  native-enabled full backend681passed208.61s, no skips (`...backend-final.txt`), one
  existing Starlette/httpx warning. Frontend68passed354.65ms and build1.57s;
  JSindex-CWZgcYd4/CSSindex-DniDnrrf (`...frontend-tests.txt`, `...frontend-build.txt`).
- Final wheel SHA256c9c3978b1400f82a99c7d38ccd0c9b5c07398488bdfe064de4ba4df79167d171
  matches all63 service Python files (`...source-proof.json`). Final installed
  native reviewer executes original owned task plus an explicitly declared two-
  Worker dependency task, verifies persisted handoff/completion through Store/HTTP,
  and retained Worker records through actual MCP stdio. Exactly requests /, /,
  /dependency-only; /observed-only never visited. One owned source POST, external
  targets/sources0. Existing backup/restore/audit/ownership/release/return workflows
  also pass (`...installed-postgres.json`,valid=true). Final default installed
  runtime valid with target_requests0 (`...installed-runtime.json`). Both runners
  terminal0, stderr empty, temporary installations/clusters removed.
- Built approval card and task detail show predecessor/dependent names and approved
  URLs with failure/skip behavior. Synthetic pending fixture, no approval: 390px
  iframe has actual document375px with15px vertical scrollbar and scroll375;
  320px modal document320/scroll320/dialog296. Both displays wrap without horizontal
  document overflow. Escape closes modal; underlying document305/scroll305. Actual
  screenshots `worker-dependencies-approval-390.jpg`, `...detail-320.jpg`; compact
  evidence `...ui-review.json`. Not actual-device/touch/zoom/screen-reader QA.
  Fixture shutdown asserts pending state unchanged, zero target traffic and removes
  temporary data. Preview restarted gracefully on final source, port8790 health/UI
  200 with final bundle (`...preview-health.json`).
- New declarations currently use API; dependency creation editor, adaptive repeated
  Planner, observed-URL consumption by tools, shared to-do and full v1 remain open.
  Contract [WORKER-DEPENDENCIES.md](WORKER-DEPENDENCIES.md). CI native list includes
  these cases; actual hosted CI/container execution still unverified.

## Worker dependency creation editor — 2026-10-05

- Task and recurring schedule forms now edit predecessor relationships for selected
  assets. Selection metadata and edges survive search/pagination. Deselection
  atomically removes related edges; reselect does not restore them. Client validation
  covers shape, selected scope, self/duplicate edges, cycles,20 assets and40 edges.
  Invalid submissions focus the relevant checkbox and show one inline alert.
- Frontend73passed372.648375ms, no skips/failures; production build1.40s. Final
  JSindex-Jx91yrBi/CSSindex-CHE-GKf8 (`artifacts/worker-dependency-editor-tests.txt`,
  `...build.txt`). Service Python unchanged; previous681 full backend result is
  historical, not rerun for this frontend change.
- Owned synthetic built UI verifies cross-page/search selection, keyboard Space,
  cycle refusal/focus, deselection/reselection, clear-all and keyboard restoration.
  A controlled503 retains task title, selections and dependency; successful retry
  stores one pending plan. Actual24h recurring reservation stores the same editor
  contract without execution (`...saved.json`, `...schedule-saved.json`).
- Root scroll width alone initially missed clipped modal content:320px dialog
  client277/scroll428. Removed nested fieldset sizing and scoped the inherited
  address minimum width. Final320px document320/scroll320, dialog277/277, form237/237,
  editor233/233;390px document390/390, dialog347/347, form307/307, editor303/303.
  Visually inspected final `...320.jpg` and `...390.jpg`; evidence `...ui-review.json`.
  This is same-origin CSS-width iframe QA, not device/touch/zoom/screen-reader QA;
  held saving-state interactions were not exercised.
- Fixture shutdown: target requests0, task creation POSTs2 (one503 and one successful
  retry; cyclic submissions sent none), original pending task unchanged, owned tabs
  closed and temporary data removed. Preview remains healthy with final UI bundle
  (`...preview-health.json`); initial check used nonexistent /health (404), corrected
  to /api/health (200). Backend process restart was unnecessary.
- Adaptive repeated Planner, observed URL consumption, shared to-do, full process
  search UI and remaining v1 gates stay open. Historical API-only editor limitation
  in the preceding validation entry is superseded by this entry.

## Evidence-based next-plan HTTP contract — 2026-10-05

- Added readonly follow-up proposals from approved terminal task coverage, and
  operator/admin acceptance creating a fresh pending plan. Original assets and
  Worker dependencies remain declared; current scope/policy/tool contracts are
  exposed for review. Completed compatible cells are omitted, failed/missing/stale
  cells and never-selected built-in checks are proposed. Skips remain disclosed.
  Whole-task tool selection can repeat other assets' completed cells; IDs are
  explicitly listed. No observed URL or external tool is added.
- Read snapshot follows at most8 predecessor rounds, verifies reciprocal lineage
  and takes latest asset/check evidence across rounds. This prevents alternating
  missing-check proposals. Changed asset revisions or tool contracts make old
  completion stale. At most8 follow-ups; no candidate after all attempted cells
  are completed/skipped and no retry candidates. This does not prove security.
- Acceptance compares source/effective coverage/current assets/contracts/policy
  fingerprint under engine/store locks. Source pointer, pending task and coverage
  commit together. Concurrent clicks and later retries return one same task, even
  after it finishes. Changed proposals refuse409; pending/unapproved/missing/
  archived/corrupt lineage and insufficient roles refuse without target execution.
- Owned real HTTP tests run on SQLite and native PostgreSQL: actual approved
  initial task, pending follow-up with no new requests, approved next round, then
  no remaining candidate; dependency retention/repeated-cell disclosure, revision/
  source-contract/policy changes, viewer/operator/administrator boundaries and
  bounded synthetic eight-round failure loop. Forced SQL trigger failures on both
  databases preserve source and create no child/coverage. Initial native rollback
  assertion expected an exception; the app intentionally translates native DB
  errors to503. Corrected assertion confirms503 and rollback. Preliminary targeted
  run25passed/1failed is preserved (`artifacts/next-plan-targeted-first.txt`).
- Initial full native-enabled backend701passed224.72s (`...backend-first.txt`),
  then added source-tool-contract compatibility and two tests. Final frozen source
  full backend703passed226.37s, no skips, one existing Starlette/httpx warning
  (`...backend-final.txt`). Frontend source/assets unchanged this turn: previous
  73 tests/build/visual review are historical, not rerun UI QA.
- Final wheel SHA256cbd1b6c235ecfecb88b7198edb5b50c5696021346da42f0a7a4383635f92de9d
  matches all64 service Python files (`...final-source-proof.json`). Installed
  native reviewer initially refused the synthetic legacy asset lacking explicit
  authorized=true; fixed owned fixture rather than weakening the contract.
  Failure preserved in `...installed-postgres-first.stderr`. Final installed
  native HTTP verifies proposal, idempotent pending creation, not_started coverage,
  already_accepted state and backup/restore retaining exact linked pending task.
  Existing installed maintenance/MCP/audit/source/release/return checks also pass.
  Total owned target requests remain3 (/, /, /dependency-only), source POST1,
  external targets/sources0 (`...installed-postgres.json`, valid=true). No added
  target request for follow-up proposal/acceptance. Default installed runtime also
  valid with target_requests0 (`...installed-runtime.json`). Both runners terminal0,
  stderr empty and owned temporary installations/clusters removed.
- Preview gracefully restarted on final service source; health/UI200 with existing
  JSindex-Jx91yrBi (`...preview-health.json`). CI native matrix includes new tests;
  hosted CI/container execution remains unverified. Contract [NEXT-PLAN.md](NEXT-PLAN.md).
  Dedicated proposal UI, replacement/retry interactions across planning rounds,
  event-driven automatic Planner, semantic goal/observation consumption, shared
  to-do and full v1 remain open.

## Next-plan review and acceptance UI — 2026-10-05

- Added terminal approved task detail panel for explicit proposal lookup/relookup:
  missing/retry checks, current names/URLs/revisions, pool/planner, Worker edges,
  policy/contract disclosures, repeated completed cells, skipped cells and latest
  per-cell source-task links. Acceptance uses the existing view/session action
  guard and opens the real pending task. Pending detail links to previous round;
  accepted source offers its existing child. Viewer acceptance is disabled.
- Query abort/controller identity and unmount guards prevent old read updates.
  Saving ref and disabled buttons reject repeated actions. Failed acceptance clears
  the stale proposal and requires reread; query or save failure returns keyboard
  focus to the enabled lookup button once pending state settles.
- Final frontend73passed473.157208ms, no failures/skips; build1.43s,
  JSindex-kxf37mbn/CSSindex-sstsBYgv (`artifacts/next-plan-ui-tests.txt`, `...build.txt`).
  Existing unit tests are regression checks; the new panel's behavioral evidence
  comes from real built-app browser interactions below. Service Python unchanged:
  all64 files still match previous cbd1b6c235ecfecb88b7198edb5b50c5696021346da42f0a7a4383635f92de9d
  wheel (`...service-unchanged.json`). Previous703 backend tests are historical,
  not rerun for this frontend change.
- Owned synthetic terminal evidence verifies503 query/retry, failed acceptance
  requiring relookup, one alert and focused query button. Held POST disables the
  submit control; attempted keyboard press is refused as disabled. Escape closes
  pending detail; same task reopens while logout is still disabled, then releasing
  the held error does not apply the old error to the new panel. Synthetic completed
  sources are not claims of real target execution.
- Keyboard acceptance creates exactly one real pending task with five checks,
  original two asset IDs and dependency, approved_at=null, planning_round1 and
  reciprocal source link (`...saved.json`). Source remains completed. Previous-
  round and existing-child links work; no_remaining_checks explanation displays
  without security claim; actual viewer login can read and has disabled acceptance.
  Additional synthetic preview/no-remaining sources and a viewer were seeded solely
  for readonly UI review. No actual execution approval was clicked.
- Narrow QA found existing observation cards'240px minimum address width causing
  article client233/scroll256 and modal277/278. Scoped record address sizing fixes
  this alongside the new panel. Final320 document320/scroll320, dialog277/277,
  panel237/237;390 document390/390, dialog347/347, panel307/307. Tables retain their
  intended internal scroll. Actual widths are measured by a QA-only same-origin
  page button/external script, not by iframe evaluation's unsupported contentDocument
  in the browser facade. Root-only measurements were insufficient.
  Final screenshots visually inspected: `...desktop.jpg`, `...320.jpg`, `...390.jpg`;
  measured evidence `...widths.json`, compact review `...review.json`. These are
  CSS-width iframe checks, not physical-device/touch/zoom/screen-reader verification.
  Round-limit presentation was not separately exercised in UI.
- Initial fixture shutdown next-plan POSTs1 (failed), final fixture POSTs4 (three
  failures and one pending creation), task creation /api/tasks POSTs0; both target
  requests0, original terminal state unchanged, owned tabs/flags cleaned and both
  temporary directories removed. Preview health/UI200 with final JS/CSS
  (`...preview-health.json`), service restart unnecessary.
- Replacement/retry interactions across rounds, automatic event-driven Planner,
  semantic goal/observation consumption, shared to-do and the full v1 gates remain
  open. The preceding API-only UI limitation is superseded by this entry.


### 2026-10-05 — Follow-up lineage across replacement and retry

- Reproduced loss of follow-up round metadata before the fix: two failing tests
  (`artifacts/planning-lineage-before.txt`). Replacement/retry now preserve the
  round, canonical parent/fingerprint and approved historical results. Current
  attempt resolution keeps the original forward pointer; combined history is
  bounded to32 records and follow-up rounds to8. Retry/next-plan races create
  one continuation. Duplicate retry still resolves the same attempt after finish.
- Added SQLite/native PostgreSQL lineage, actual owned HTTP failure/recovery,
  bounded-history, missing/conflicting links and atomic rollback coverage.
  Initial full run723 passed246.62s. A further corrupted stored key/payload ID
  case reproduced200 instead of409 in both stores; the first PostgreSQL fixture
  needed a TEXT-to-jsonb cast before reproducing the same bug. Added the identity
  guard and final full run: **725 passed249.24s**, no skips, one existing
  Starlette/httpx deprecation warning (`...backend-final.txt`).
- Corrected native rollback triggers to cast TEXT data to jsonb. A
  nontransactional sequence probe confirms the intended source-pointer write
  branch was reached before failure, rather than an earlier invalid SQL operator.
  CI native test selection includes the new file; hosted CI was not executed.
- Frontend **73 passed462.854125ms**, build1.45s; final JS
  `index-s-TgUUBz.js`, CSS `index-sstsBYgv.css`. Retry/replan opens returned current
  detail, and retry-origin/accepted-retry navigation is available.
- Final installed wheel SHA256
  `ab5bfb494fc70f33aabeb02956b00d97ebdcfabcb8b6236e6f18a0a5de07f119`;
  all65 service files match (`...final-source-proof.json`). Installed default
  runtime review valid with0 target requests. Installed native review valid:
  replacement retains round/parent/fingerprint and current attempt survives
  real backup/restore;3 owned target requests,1 owned source request,0 external
  requests. The first reviewer attempt mistakenly used GET for replan; corrected
  to POST and retained its failure stderr. Final JSON artifacts are
  `...installed-runtime.json` and `...installed-postgres.json`.
- Actual built UI created one pending follow-up, replaced it, navigated from
  original to current replacement, then created a pending retry and navigated
  through retry origin and accepted-retry buttons. Source completion and failure
  metadata were explicitly synthetic in a disposable fixture, with no execution
  approval clicked. Persisted four-task graph preserves round1, original
  fingerprint, dependencies and immutable first follow-up pointer; retry remains
  pending/unapproved, traffic0 (`...ui-proof.json`). Desktop screenshot
  `...ui-desktop.jpg` was visually inspected. This increment did not repeat narrow
  width/touch/screen-reader QA; prior width evidence is not a physical-device test.
- Owned tab closed; fixture shutdown confirmed target requests0, task creation
  POSTs0, next-plan POSTs1 and temporary data removal. Main preview gracefully
  restarted asPID37464 with preserved preview data on127.0.0.1:8790; health and
  final JS/CSS verified (`...preview-health.json`). No remote publishing occurred.
- Basic replacement/retry lineage supersedes the preceding integration limitation.
  Automatic event-driven planning, semantic observation consumption/shared to-do,
  full accessibility/mobile journeys and all other V1-READINESS gates remain open.


### 2026-10-05 — Worker process UI

- Added task-detail Worker selection, explicit process read, coverage and independent
  event/observation search/pages using existing bounded readonly endpoints.
  Stored approval scope/revision is displayed; event metadata matched/unconfirmed
  and observation provenance are distinguished. Selection changes unmount/abort
  prior requests and clear old records. GET uses existing session completion guard.
  Full-workspace process search, selection/search URL restoration, automated Planner
  consumption and full assistive-technology/mobile journeys remain open.
- Frontend73 passed328.180125ms; production build1.41s, final JS
  `index-jUmwrGRR.js`, CSS `index-A1Pg18P4.css` (`artifacts/worker-process-ui-tests.txt`,
  `...build.txt`). These existing unit tests do not exercise the new React interaction.
  Appropriate Worker API tests on SQLite and actual PostgreSQL16:13 passed3.75s,
  one existing Starlette/httpx warning (`...api-tests.txt`). No backend service changed;
  the preceding full725-test result is historical, not rerun for this UI increment.
- Actual built-service UI with disposable synthetic completion/coverage/events/
  observations: child32 events, next page26–32, single observation search result;
  parent switch removes child records before query and then returns one isolated
  parent event, two completed cells and empty observations. Legacy Worker event
  shown unconfirmed. Owned failure flag produces503 and alert, focus returns to
  query button; after removal query succeeds. No execution approval was clicked.
- Visual screenshots `...ui-desktop.jpg`, `...ui-320.jpg`, `...ui-390.jpg` inspected.
  QA-only page button measures320 document320/320 and dialog277/277;390
  document390/390 and dialog347/347. Overflow report contains intended table
  scrolling, hidden skip link and collapsed sidebar brand; no Worker content overflow.
  Existing metric named panel refers to next-plan, not the Worker panel; document/
  dialog dimensions and overflow entries support the narrower claim here.
  CSS-width frames do not prove physical mobile/touch/zoom/screen-reader behavior.
- Owned tabs closed, flag removed, fixture shutdown: target requests0, task creation
  POSTs0, next-plan POSTs0 and temporary data removed. Main preview backend remains
  unchanged; final separate static assets and health verified on127.0.0.1:8790.
  No hosted CI, container run, remote publishing or full v1 completion is claimed.


### 2026-10-05 — Worker navigation bookmarks

- Added bounded task Worker URL state for selected asset, expansion and independent
  event/observation search, offset and snapshot. Asset switch resets both collections
  and expansion; search resets only its own positions. Closing/switching detail or
  workspace page clears Worker URL fields. Invalid IDs/integers normalize before
  API use; syntactically valid assets outside the historical scope show an error
  and no process panel. Existing task list/collection positions remain independent.
- Old collection callbacks verify current task/Worker state before changing the
  URL. Saved open URLs automatically query the readonly process; existing abort,
  unmount and session-completion guards apply. Restore failure focuses query, and
  retry retains the bookmarked searches/pages.
- Frontend77 passed429.736833ms (`artifacts/worker-navigation-tests.txt`), four new
  navigation cases cover restoration, independent snapshot domains, resets,
  removal and malformed bounds. First run76/77: the new fixture incorrectly set
  a snapshot in the same interaction as changing search, which correctly resets
  it. Fixed fixture to model separate search/page actions, retained first output
  (`...tests-first.txt`). Build1.41s, JSindex-5ZXIJQ2h.js, CSSindex-A1Pg18P4.css.
- Actual built UI, disposable synthetic two-Worker fixture: child event second page
 26–32/32 and observation owned-link-59 restore in a newly opened document; parent
  switch clears fields and child content; parent read returns isolated evidence;
  dialog Previous twice restores child's page/search. Missing-scope URL refused;
  saved open URL503 focuses query and retry restores event page. Closing detail
  removes all Worker fields. Screenshot `...desktop.jpg` visually inspected and
  compact evidence `...ui-proof.json` saved. An unsupported inputValue facade call
  was replaced by readonly visible DOM value inspection. A duplicate query argument
  initially retained the first asset; verified missing-scope case with a replaced
  URL parameter. These were review-tool issues, not claimed product regressions.
- Fixture shutdown confirmed target requests0, task creation POSTs0, next-plan
  POSTs0 and temporary removal; owned tab/flag cleaned. Preview health and final
  static assets verified at127.0.0.1:8790. Backend unchanged; previous725 full
  backend and13 Worker API tests are historical, not rerun here. No physical-device,
  screen-reader, hosted CI or container evidence is added by this increment.
- Whole-workspace process search, automatic/event-driven planning, shared to-do and
  all remaining V1-READINESS gates remain open. No remote publication occurred.


### 2026-10-05 — Workspace Worker event search

- Added authenticated GET /api/worker-events and readonly MCP search_worker_events.
  SQL pages newest Worker-associated events, supports literal message/level/task-ID/
  asset-ID search and task/asset filters. Valid string asset IDs and bounded task IDs
  select events; Planner events without asset are excluded. Legacy/orphan events
  remain unconfirmed. Historical task scope is read through bounded point queries
  in the same DB snapshot; missing scope/corrupt stored key/payload identity cannot
  redirect source. SQL count/search workload and record retention still need SLO QA.
- Added SQLite/native PostgreSQL paging, snapshot insertion exclusion, historical
  scope, filtering/literal SQL-like search, malformed asset identity, orphan/legacy,
  concurrent source change and corrupt payload tests. MCP parity/bounds/readonly
  and HTTP anonymous/viewer/operator checks cover the new route. Extended the actual
  native ordinary SELECT-role test to call workspace search while writes/users
  remain denied. Native CI selection includes new history test file; hosted CI not run.
- Initial targeted25 passed5.66s. First full:736 passed,1 failed252.32s because the
  MCP stdio catalog assertion still expected11 tools; new catalog has12. Updated
  explicit expected tool set without removing catalog/no-mutation assertions.
  Preserved first failure (`artifacts/worker-history-backend-first.txt`). Final full
  **737 passed251.31s**, no skips, one existing Starlette/httpx deprecation warning
  (`...backend-full.txt`). Frontend **78 passed1291.162ms** includes source-list
  position preservation and reset case; final build1.44s, JSindex-cH43G0Gr.js,
  CSSindex-D51Z87fH.css (`...ui-tests.txt`, `...ui-build.txt`).
- Installed wheel SHA256
  2a58587e55fe63ab78fe4a1811720ab583c5514308148d5cfd2263546115ec09;
  all65 service source files match (`...wheel-source-proof.json`). Installed native
  review valid: actual owned execution history searched over HTTP and MCP stdio,
  source available/matched and execution_authorized=false. Existing owned target
  request count remains3, owned source1, external requests0. Default installed
  runtime review rerun against final static assets valid with0 target requests
  (`...installed-postgres.json`, `...installed-runtime-final.json`). Earlier default
  result before final padding styles is retained separately, not final UI evidence.
- Built UI now has 실행 과정 page,25-row search/page URL state and source Worker
  navigation with atomic selected/open detail URL state. Orphan source button is
  disabled. Actual disposable synthetic fixture:34 total, last page26–34, reopened
  page URL restores position; message search returns one child event; open source
  selects child scope/process, closing preserves search. Read503 shows failed-read
  notice and last received record; Latest after flag removal recovers. Synthetic
  records are not claimed as actual execution; no approval/target requests occurred.
- Final desktop/320/390 screenshots (`...ui-desktop.jpg`, `...ui-320.jpg`,
  `...ui-390.jpg`) visually inspected. Added panel/input padding for readability.
  QA-only visible measurement button:320 frame document client305/scroll305;
 390 frame375/375 (15px vertical scrollbar). No content horizontal overflow;
  only hidden skip link and collapsed sidebar brand reported. No dialog/next-plan
  panel in this page. Compact evidence `...ui-proof.json`, `...ui-widths.json`.
  These are CSS-width frame tests, not physical-device/touch/zoom/SR verification.
- Owned tabs/flag cleaned; fixture shutdown target requests0, task creation POSTs0,
  next-plan POSTs0 and temporary removal. Main preview gracefully restartedPID84481
  on127.0.0.1:8790 preserving data; health/final JS/CSS/authenticated route verified
  (`...preview-health.json`). No remote publication or container execution occurred.
- Worker event search supersedes the earlier whole-workspace event-search gap;
  semantic goal/observation consumption, automatic/event-driven Planner, shared
  to-do and all remaining V1-READINESS gates stay open. This is not full v1 completion.


### 2026-10-05 — Shared planning-family todo persistence/API

- Added todos/todo_history records, verified planning-family root resolution and
  authenticated HTTP create/update/list/history. Follow-up/retry/replacement reads
  share the original family; unrelated families cannot mutate/read a todo history.
  Actor/root/request-ID-derived creation deduplicates retries even after edits or
  completion, with content mismatch409. Strict expected_revision CAS rejects stale
  updates, terminal decisions require a reason, active admin/operator assignment
  snapshots public names and no-op writes do not increment revision.
- Todo/history and event/hash/head commit in one write transaction. Store.event now
  accepts an owned connection to participate in that existing transaction. SQLite
  BEGIN IMMEDIATE/native schema advisory locking serialize distinct Store instances.
  No change creates task approval or marks findings/coverage successful. Reopening
  clears current completion reason while historical decisions remain.
- Readonly MCP list_task_todos/list_todo_history bring catalog to14 tools. Existing
  page bounds/output cap apply. Actual native ordinary SELECT role reads both without
  users/sessions access and remains unable to write/read users. CI native selection
  includes todo parity and native HTTP tests; hosted CI not executed.
- First targeted20/21: duplicate HTTP creation returned identical row and unchanged
  decision history, but the assertion incorrectly expected no generic API request
  audit. Changed it to assert decision deduplication; HTTP requests remain audited.
  A later39-case run failed in the native rollback fixture before creating its
  probe because unqualified DDL resolved to pg_catalog. Qualified owned schema DDL.
  Both failure outputs retained (`artifacts/shared-todos-targeted-first.txt`,
  `...targeted-second.txt`). Initial complete run751 passed254.75s was before the
  later terminal-note guard and assignment/identity cases (`...backend-first.txt`).
- Additional regression reproduced clearing a completed decision's reason in both
  stores: two failing tests (`...terminal-note-before.txt`). Added guard requiring
  nonempty reason throughout terminal state, including explicit new reason on a
  terminal state change. Final related50 passed12.22s (`...targeted.txt`).
  Final full **755 passed255.92s**, no skips, one existing Starlette/httpx warning
  (`...backend-full.txt`). Tests cover real retry/replan HTTP sharing, role/input
  bounds, foreign family, active/disabled/viewer assignment, corrupt todo key/payload
  identity, independent-writer concurrent create/CAS and readonly snapshot pages.
- Actual late audit-head database triggers fail after todo/history and event/hash
  inserts: all records/hash/head rollback in SQLite/native PostgreSQL. Native
  nontransactional sequence proves the intended failing head-update branch ran.
  Earlier Python event-failure probes separately verify rollback after record writes.
- Final wheel SHA256
  0beb241dcb26841a99e8ff1b647757ab1e5f5b9785d93d969db613bcecaa5e4f;
  all66 service files match (`...final-wheel-source-proof.json`). Installed native
  review valid: creates/deduplicates todo, reads through actual pending follow-up and
  replacement, updates manually, restores done decision and two history entries
  through real backup/restore, and queries both via MCP stdio. Existing owned target
  requests3, owned source1, external0; no new target execution caused by todos.
  Default installed review valid with0 target requests (`...installed-postgres.json`,
  `...installed-runtime.json`). First wheel0521995b... and its successful reviews
  precede terminal-note guard and are retained as historical evidence only.
- Frontend unchanged: prior78 tests/build are historical, not rerun or claimed to
  exercise a todo editor. Shared todo editing/UI/URL/mobile/SR and automatic Planner
  consumption are explicitly open in SHARED-TODOS and V1-READINESS. No browser todo
  QA claimed, no remote publication/container run. Main preview gracefully restarted
  fromPID84481 to53876 preserving data; health/static assets and authenticated todo
  route verified (`...preview-health.json`). Full v1 remains unachieved.

### 2026-10-05 — Shared todo editing and response recovery UI

- Task detail now provides create, description, paged assignee lookup, status/reason
  editing, paged/searchable decision history and readonly viewing. Added authenticated
  point GET with the same verified family/record identity guards as updates, allowing
  an explicit latest-state comparison after409. Both native HTTP and SQLite tests
  verify current row through follow-up/retry/replacement, viewer read, anonymous
  rejection and unrelated-family404.
- Creation persists the frozen payload/nonce before dispatch; storage failure blocks
  dispatch. Unknown response remains retryable with exactly the same content after
  same-tab reload. Successful matching response clears only that nonce;422 unlocks
  rejected input. Explicit API error status distinguishes validation from503/network
  uncertainty. Session/view guards suppress stale UI completion. Unsaved pre-dispatch
  drafts and other-device/tab recovery are not provided.
- Editing keeps an independent baseline/draft through list refresh and409. Latest
  record is shown before choosing local changed-field rebase or intentional discard.
  Rebase preserves unrelated concurrent fields and still requires explicit CAS save.
  New terminal decisions send their reason even if its text matches the old reason.
- First browser concurrency run exposed duplicate sibling React keys for editor and
  history: periodic updates accumulated editor forms. Recorded the actual duplicate
  DOM (`artifacts/shared-todos-ui-duplicate-before.json`), separated their keys, then
  reran with one editor remaining through refresh and successful writes. This was
  found and fixed before the final UI build; backend tests do not assert React DOM.
- Actual disposable built-app desktop: create committed before a deliberately
  substituted503 response, input froze, same-tab reload restored it, retry returned
  the existing item with one creation history. Two tabs edited the same record;
  stale title save409 retained input. Latest comparison/rebase saved only local title
  while retaining the colleague's description/done reason. Assignment and reopening
  produced revision5, cleared current reason and retained all five history entries
  (`...ui-conflict-after.json`).31 total items paged26–31; title search returned1.
  Final desktop screenshot visually inspected (`...ui-desktop-final.jpg`).
- Built task-detail documents measured320/320 and390/390 client/scroll widths with
  the new section rendered (`...ui-widths.json`). Existing intentional table scroll
  regions and hidden skip link/icon label remain internally wider; no shared-todo
  overflow was reported.390 frame screenshot inspected (`...ui-390.jpg`) shows the
  task detail upper section, not a mobile editor interaction. Actual mobile touch,
  zoom, keyboard journey/SR, viewer UI and todo-specific URL restoration remain open.
- **84 frontend tests passed471.49ms**; final TypeScript/Vite build1.46s succeeds
  (`...ui-node.txt`, `...ui-build.txt`). New tests cover persistence isolation,
  matching-response cleanup, blocked/malformed storage, changed-field rebase,
  explicit terminal reason and HTTP error statuses. Related native/SQLite tests
  **18 passed4.25s**. Full suite **755 passed258.02s**, no skips, one existing
  Starlette/httpx warning (`...ui-api-native.txt`, `...ui-full.txt`).
- Final wheel SHA256 d09d8b9b9ea7bb24d3344d654f97a6c73aa52d9f96ccfa2a3731d74e9dfe1551;
  all66 recursive service files exactly match (`...ui-wheel-source-proof.json`).
  Actual installed native backup/restore/todo/MCP review valid:3 owned target and1
  owned source requests, external0. Default installed runtime review repeated after
  final CSS build and valid with0 target requests (`...ui-installed-postgres.json`,
  `...ui-installed-runtime.json`). New point GET is exercised by HTTP tests; the
  installed native review continues to exercise the existing todo/history APIs.
- Preview restarted fromPID53876 to98945 preserving data, final health/static HTML
  recorded (`...ui-preview-health.json`). Final assets JSindex-CedO0ifR.js and
  CSSindex-CEJAE7Xo.css. No GitHub publication, container/hosted CI, commercial LLM
  call, automatic todo-driven Planner or complete v1 claim.

### 2026-10-05 — Shared todo URL restoration and collection callback scope

- Added task-scoped todo list search/offset/snapshot, selected todo ID and independent
  history search/offset/snapshot URL state. Task closure/change clears these fields;
  item change/closure clears only its history; one search resets only its own page.
  Bounded ID/search/integer normalization applies before API paths/positions. Current
  selected row uses authenticated point GET with abort/error/manual retry; malformed
  IDs do not dispatch it. Edit-open/pre-dispatch drafts remain local, not in the URL.
- Creation/edit UI completion now reconciles owned current state before dispatching
  records-changed; URL snapshot updates can invalidate a view capture synchronously.
  A late confirmed creation unlocks its frozen form and reports completion while
  preserving the new selection/search/editor. Session/unmount guards remain.
- First actual creation retry from a selected item with `updated` history search
  exposed the old history listener writing its conditions into the new item's URL:
  the new item showed0 history. Preserved before evidence (`artifacts/shared-todos-navigation-retry-before.json`). Added task/item and expected collection condition
  guards to position callbacks, including the gap before React rerenders after a URL
  change. Rerun shows empty history search, one creation entry, unlocked form and
  preserved todo list position (`...navigation-retry-after.json`).
- Expanded owned fixture:30 todos,31 history entries for one item,26 operators plus
  admin/viewer, bounded POST/PATCH hold and todo GET failure flags. These fixtures
  only write synthetic metadata; no validation target execution/approval occurs.
- Actual built desktop: independent list/history last pages26–30, selected item and
  both searches/snapshots restored in a new document. Closing selected item retained
  list page; Back restored selection/history. Editing title through history search
  and Back retained one editor/draft. Saving retained search/offset, cleared insertion
  snapshots and advanced baseline32 (`...navigation-save.json`). A final guarded
  description save advanced baseline33 while both offsets remained25
  (`...navigation-current-guard-save.json`).
- Last assignee page selected operator25; directory search changed to admin while
  retaining that selection. A committed creation with substituted503 froze input;
  same-tab reload restored its payload together with existing selected item/history
  bookmark. Matching retry deduplicated and retained assignment. Retry before/after
  artifacts distinguish the separately fixed history-condition leak.
- Held another POST while changing search, selecting item28 and editing its title;
  released response confirmed prior creation without changing new selection/draft,
  and unlocked creation (`...navigation-late-save.json`).503 point/list/history reads
  preserved existing draft and last received list; fresh bookmarked document showed
  errors without a fabricated selected row/editor/empty result. Manual recovery
  cleared alerts and retained draft (`...navigation-read-failure.json`,
  `...navigation-read-recovery.json`).
- Viewer login restored selected row/list/history pages without creation/editor/edit
  button (`...navigation-viewer.json`). Missing valid ID showed404 without editor or
  fabricated selection, with list page retained and explicit selection close
  (`...navigation-missing.json`). Server permission guards were unchanged this turn.
- Documents rendered with selected/history bookmark measured320/320 and390/390
  client/scroll widths (`...navigation-widths.json`). Existing intentional table
  scroll regions/hidden skip/icon labels remain wider internally; no todo overflow.
  Actual desktop editor screenshot inspected (`...navigation-desktop.jpg`). Actual
  mobile touch/zoom, full keyboard/SR journeys and role change race are not claimed.
- Final **90 frontend tests passed472.03ms**, TypeScript/Vite build1.42s
  (`...navigation-node.txt`, `...navigation-build.txt`). Six new navigation tests
  verify independent positions, reset/cleanup, hostile bounds and old task/item or
  collection callbacks being rejected. Final installed runtime review valid with0
  target requests and final separately built UI (`...navigation-installed-runtime.json`).
  Backend source/wheel unchanged, SHA256d09d8b9b9ea7bb24d3344d654f97a6c73aa52d9f96ccfa2a3731d74e9dfe1551.
  The prior755 full/native suite and native installed review are historical evidence,
  not rerun for this frontend change. No new backend/native coverage claimed.
- Main preview keepsPID98945 and existing data; updated static assets are
  JSindex-ii273h2V.js / CSSindex-CEJAE7Xo.css. No remote publication/container/hosted
  CI or automatic todo-driven Planner. Full v1 remains unachieved.
- Final current creation selected the new item, reset history search and showed one
  creation entry while retaining list search/offset25 (`...navigation-final-create.json`).
  All owned browser tabs/flags were removed. Fixture lifespan ended with target
  requests0, task/next-plan creation POSTs0 and temporary data removed
  (`...navigation-fixture-cleanup.txt`). Final preview health/static HTML recorded
  (`...navigation-preview-health.json`).


## Shared todo requests and frozen planning context — 2026-10-05

- Current service: explicit check_ids for shared todos, canonical known catalog IDs,
  old omitted-field creation digest replay and empty update compatibility. Active
  requests join next-plan candidates without changing existing assets or approval.
  Closed requests never suppress actual failure retry or mark coverage successful.
- Family-wide context includes current ID/revision/status/title/description/check
  requests/decision reason, validates every row and checksum, and refuses over100
  items or64KiB UTF-8 without truncation. Follow-up creation recomputes its proposal
  inside the final write transaction; changed or corrupted context refuses409 and
  leaves no child/coverage partial commit. Previously accepted requests replay the
  existing immutable pending plan. Replan/retry also capture current family context.
- Rule/AI order uses stored context and intersects approved tools. Actual approved
  owned loopback execution with mocked completion verifies frozen human text after
  a live edit, exact six-field active item projection, call provenance and refusal
  of injected tools/corrupt context before provider dispatch. No commercial provider
  or operational target tested. Arbitrary prose goal decomposition and automatic
  event-driven planning remain open.
- Related SQLite/native PostgreSQL contracts: **68 passed35.75s**
  (`artifacts/todo-planner-targeted.txt`). Full native-enabled suite:
  **771 passed269.89s**, one existing Starlette test-client deprecation warning
  (`artifacts/todo-planner-full.txt`). New native cases are included in CI configuration;
  hosted CI was not executed. Frontend: **92 passed435.48ms**; final TypeScript/Vite
  build1.58s (`...node.txt`, `...build.txt`). No backend edits after the full run.
- Wheel SHA256 **ad9e635d82a1ec7cdd4c25cb6d888b7f3a9e70694040417d30993ed4065a6f89**,
  all66 recursive service Python files byte-for-byte match checkout
  (`artifacts/todo-planner-wheel-proof.json`). Installed default runtime and native
  PostgreSQL16.15 reviews valid (`...installed-runtime.json`, `...installed-postgres.json`).
  Native review now verifies check requests/proposal snapshot/frozen child and exact
  context preservation after pg_dump/restore. Native owned lab requests3, owned source1,
  external targets/sources0; default target requests0. Final UI review uses the last
  separate build. Docker/hosted CI and production PostgreSQL are not claimed.
- Actual built desktop: endpoint request joins skipped-but-not-successful check to
  proposal; changing association to cookie after GET refuses stale POST; fresh GET
  creates pending child. Child snapshot stays at version2 while live item changes
  title/version3 (`...ui-stale.json`, `...ui-frozen.json`). No execution approval.
  Committed create with substituted503 freezes CORS selection; same-tab reload restores
  checked/disabled control and same-payload retry confirms one item
  (`...ui-lost-restored.txt`, `...ui-lost-confirmed.txt`). Final AI export disclosure
  visible at creation, stored context and proposal; final desktop screenshot inspected.
- Final320/390px synthetic documents measure client/scroll320/320 and390/390
  (`...ui-widths.json`). Intentional table scrolling/hidden labels and existing320px
  report action internal overflow remain; no document/todo width overflow. Actual
  mobile touch/zoom, screen reader and full role-race journeys are unverified.
- Main preview restarted preserving artifacts/preview-data; health ok, final
  JSindex-BQ8INzWl.js / CSSindex-Chq8UNaO.css (`...preview-health.json`).
  Current increment is partial v1 progress, not full ARTEX parity or v1 completion.
- Owned fixture/tabs/flags cleaned up; lifespan reported target requests0, ordinary
  task creation POSTs0, next-plan POSTs2 (one stale refusal, one accepted pending
  plan), temporary data removed (`artifacts/todo-planner-ui-fixture.txt`).


## Durable automatic event-driven proposal preparation — 2026-10-05

- New EventPlanner consumes committed task/family and asset-ID events to prepare
  rule-based follow-up proposals before explicit next-plan GET. It never calls
  a provider, sends a target request, creates a task or grants approval. Source
  coverage, tool contracts, bounded history and frozen human request context are
  reused; current descendant terminal plans receive root todo changes.
- SQLite/native PostgreSQL persist proposal and event cursor in one write
  transaction. Cursor-save failure rolls both back; next step replays the event.
  Asset fanout is25 tasks per step with saved insertion snapshot/offset; a new
  processor resumes the unfinished page. Policy changes replay committed events.
  Corrupt lineage becomes a blocked result without starving the next valid event.
  Real HTTP server restart consumes an unprocessed human change without new execution.
- **18 related cases passed14.62s** (`artifacts/event-planner-targeted.txt`). First
  full run had789 passes but a report-only global Store.get prohibition also killed
  the independent background reader. The report test now stops that consumer before
  installing the unchanged prohibition. Final full native-enabled suite:
  **789 passed281.78s**, only existing Starlette deprecation warning
  (`artifacts/event-planner-full.txt`); no unhandled worker warning. No service source
  change after these runs. Native event tests added to hosted CI configuration;
  hosted CI itself unrun.
- Final frontend **92 passed503.40ms**, TypeScript/Vite build1.71s
  (`...node.txt`, `...build.txt`). New component polls status4s, aborts on unmount,
  distinguishes stale displayed proposal, blocked preparation and failed reads,
  and offers explicit read retry. No claim that existing unit tests alone prove
  new interaction behavior; owned built-app evidence below provides that coverage.
- Wheel **826e827e7b4171f660429850e89dd5e5388f62c50ed71b2f2088427b91b91ed7**,
  all67 service Python files byte-match checkout (`...wheel-proof.json`). Installed
  default/runtime and native PostgreSQL16.15 reviews both valid. Native installed
  HTTP waits for an automatic ready proposal before manual proposal GET and verifies
  exact equality; restored server automatically resumes to the existing connected
  plan/no-proposal state. Runtime consumer alive/errors0 verified. Native target
  requests3 and owned source1, external targets/sources0; default target requests0
  (`...installed-postgres.json`, `...installed-runtime.json`). Final separately built
  UI was included in default review.
- Owned UI fixture shows automatic ready status before proposal lookup, then a
  human endpoint request reflected by later event62 (`...ui-ready.txt`,
  `...ui-proposal.txt`). Final built UI: while prior proposal remains displayed,
  committed cookie request advances to event64.503 status GET shows failure and
  explicit retry while preserving prior proposal. Retry restores stale-display
  notice; proposal reload shows both requests (`...ui-read-error.txt`,
  `...ui-display-stale.txt`, `...ui-fresh.txt`).
- A second owned tab archives the synthetic source asset; final UI reports blocked
  preparation while retaining old displayed proposal, rather than claiming a new
  available proposal. Restoring asset prepares current revision and requires
  proposal reload (`...ui-blocked.txt`, `...ui-restored.txt`). Explicit acceptance
  creates a pending two-asset/six-tool plan with0/2 processed, all cells unexecuted
  and32-item stored context (`...ui-pending.txt`). No execution approval.
- Automatic-status default documents measure320/320 and390/390 client/scroll widths
  (`...ui-widths.json`). Intentional table scroll/hidden label widths remain. Desktop
  status panel and folded context screenshot inspected; final text-only guard change
  subsequently verified with blocked/archive/restore interaction. Actual mobile
  touch/zoom, screen reader and full event-load/latency SLO are not verified.
- Existing preview data retained, new PID57068, health ok; anonymous planner401,
  processed event88/head88 and3 stored reviews. Final static JSindex-PvAXzy1C.js /
  CSSindex-ZAbl2hHS.css (`...preview-health.json`). Owned tabs/flag removed. Both UI
  fixtures shut down with target requests0 and temporary data removed; final fixture
  task creation POSTs0, explicit next-plan POST1 (`...ui-final-fixture.txt`).
- [EVENT-PLANNER.md](EVENT-PLANNER.md) states boundaries: semantic goal decomposition,
  Worker observation reasoning, live AI intervention, commercial provider, long
  event/resource load, retention and complete mobile/SR remain open. Whole v1 is
  still unachieved; no remote publication or container execution.

## Frozen Worker observation planning context — 2026-10-05

- Follow-up, replacement and retry plans store bounded observation context. Only
  matching recorded provenance, completed endpoint inventory and current active,
  authorized scope/revision contribute. Counts disclose exclusions and observations
  outside the100-row sample; context above64KiB is refused. Path-name categories
  affect relevance ordering within approved checks and do not establish a vulnerability.
  Human requested checks retain their original group order before other relevant checks.
- SQLite/native PostgreSQL tests cover changed-observation stale proposal refusal,
  accepted nonce replay and frozen child context, invalid provenance/coverage/revision,
  query-bearing URLs, mismatched keys and malformed list-valued IDs, bounded sampling,
  oversize refusal and context tampering. Mock-provider approved loopback execution
  verifies the exact five-field projection, recorded references and no observation
  URL visits; later live observations do not change the stored provider input.
- Final related cases: **38 passed27.53s** (`artifacts/observation-context-targeted-final.txt`).
  Final native-enabled full suite: **811 passed295.28s**, only the existing Starlette
  test-client deprecation warning (`...full-final.txt`). The earlier809-case full run
  preceded the final malformed-ID regression pair. No service edits after final tests.
  Frontend: **92 passed481.01ms**, TypeScript/Vite build1.42s (`...node.txt`, `...build.txt`).
  Native cases are configured in CI; hosted CI was not run.
- Wheel SHA256 **63a6dd5c5b0e3b0d96e2653347552fea225506160adc86ccdcf2d9207a2256e5**;
  all68 recursive service Python files byte-match checkout (`...wheel-proof.json`).
  Installed default runtime and native PostgreSQL16.15 reviews are valid
  (`...installed-runtime.json`, `...installed-postgres.json`). Native review asserts
  one source observation in the proposal, exact child snapshot and exact preservation
  after real pg_dump/restore. Native owned lab requests3, owned source1, external
  targets/sources0; default target requests0. Docker and production PostgreSQL untested.
- Built-app proposal and accepted pending task show2 included observations out of63,
  with61 exclusions and0 omitted. Reloaded final built UI displays session/API paths,
  scope revision/source and provider projection disclosure; desktop screenshot inspected
  (`...ui-proposal.txt`, `...ui-pending.txt`, `...ui-final.txt`, `...ui-final.jpg`).
  No execution approval. This increment does not establish new mobile/SR coverage.
  Owned tab closed and fixture stopped: target requests0, ordinary task POSTs0,
  next-plan POSTs1, temporary data removed (`...ui-fixture.txt`).
- Main preview restarted preserving existing data; health status ok and anonymous
  planner access401. Final JSindex-DS-FF9lF.js / CSSindex-ZAbl2hHS.css
  (`...preview-health.json`). [OBSERVATION-PLANNING.md](OBSERVATION-PLANNING.md)
  documents boundaries. Semantic goal decomposition, explicit observed-URL execution,
  commercial-provider validation and other v1 readiness gates remain open.

## Explicit observed-response execution — 2026-10-05

- New readonly observation-plan preview and explicit operator selection create a
  separate pending task for up to10 verified observed URLs and the four existing
  response configuration checks. The final write transaction rechecks observation
  context and current assets. The same request ID/input returns the same committed
  task, including after source changes; a different input with that ID is refused.
  Approval seals selected input/checks/scope and execution checks that contract.
- Owned SQLite/native PostgreSQL cases demonstrate no requests before approval,
  simultaneous duplicate creation, exact selected GETs/response reuse, frozen input,
  invalid/stale selections and roles, approval tampering refusal, URL-specific proof,
  failed/partial/denied responses, scoped redirect refusal, same-URL failing-before/
  passing-after retest with original evidence retained, denied retest inconclusive,
  replacement/retry selection and final-write mutation rollback. Observed response
  coverage is excluded from base-asset latest completion in both native queries.
- Related suite **24 passed30.89s** (`artifacts/observation-execution-targeted-final.txt`)
  preceded the final retry replay ordering correction and its additional assertion.
  Final native-enabled full suite **835 passed327.22s**, only existing Starlette
  test-client deprecation warning (`...full.txt`), includes that correction. No service
  source edits after the full run. Native cases added to CI configuration; hosted CI unrun.
  Frontend **92 passed452.26ms** (`...node.txt`); these existing unit tests do not by
  themselves prove the new selection interaction. Final TypeScript/Vite build1.48s
  (`...build-final.txt`) includes subsequent spacing/wrapping classes and styles.
- Wheel SHA256 **f1955f4ddf8d51bf75ed3947af831a5ec68ae513912d2863608e175f5af48860**,
  all69 recursive service Python files byte-match checkout (`...wheel-proof.json`).
  Final-UI installed default runtime and native PostgreSQL16.15 reviews both valid
  (`...installed-runtime-final.json`, `...installed-postgres.json`). Native installed
  HTTP additionally creates a selected pending plan, replays its request ID and
  verifies exact execution context and replay after actual native backup/restore.
  No approval of that selected installed plan; actual selected execution is exercised
  by owned source-checkout HTTP tests above. Native owned lab requests3/source1,
  external targets/sources0; default target requests0. Container/production DB unverified.
- Built-app selection shows2 available out of63 observations. A committed POST with
  substituted503 preserves selection, freezes controls, reloads saved request in a
  new document and confirms the single existing pending task by same-request retry
  (`...ui-lost.txt`, `...ui-restored.txt`, `...ui-pending.txt`). Final built desktop
  screenshot inspected (`...ui-final.jpg`); no execution approval. Backend role/refusal
  tests do not establish full browser role or navigation race journeys.
- Final selected pending document measures320/320 and390/390 client/scroll widths;
  dialog277/277 and347/347 (`...ui-widths.json`). Existing intentional table overflow,
  hidden labels and320px internal report-action overflow remain. Actual mobile touch,
  zoom, screen reader and selection controls on mobile are not verified.
- Owned tabs and flag removed, fixture shut down: target requests0, ordinary task
  POSTs0, next-plan POSTs0, observation-plan POSTs2, temporary data removed
  (`...ui-fixture.txt`). Preview restarted with existing data; health ok, anonymous
  observation-plan401, JSindex-C1BFzZvh.js / CSSindex-f-LhXaKA.css (`...preview-health.json`).
- [OBSERVATION-EXECUTION.md](OBSERVATION-EXECUTION.md) defines limits. Semantic
  goal/observation reasoning, automatic observed-target selection, selected-plan
  follow-up/shared-todo integration and the broader v1 readiness gates remain open.

## Natural-language goal drafts and approved execution — 2026-10-05

- New [goal planning contract](GOAL-PLANNING.md): optional provider decomposes an
  operator goal into bounded review objectives, catalog checks, registered asset IDs,
  proposed criteria/missing inputs and an acyclic Worker dependency graph. Accepting
  a reviewed draft creates a separate pending task; the original remains. No target
  request before administrator approval. Runtime uses the approved asset/check union
  matrix and dependencies; precise per-objective scheduling and semantic goal
  verification remain open. Progress always reports `goal_verified:false`.
- SQLite/native PostgreSQL HTTP tests exercise mock semantic decomposition, same
  request replay without another provider call, conflicting nonce refusal, six invalid
  provider forms and explicit rules fallback, stale asset/policy/source/draft refusal,
  role boundaries, current-scope/approved-contract tamper refusal, atomic final-write
  recheck, provider-result save failure/recovery, actual approved owned target execution,
  dependency order/replan preservation, token custody and declared progress denominator.
  These are provider contract tests, not commercial-model quality evaluations.
- Historical intermediate full run:867 passed before the final scope/denominator guard.
  A subsequent full run had868 passed/1 failed because a concurrent Vite build briefly
  removed its output directory during a backup test's server initialization. No test
  or service workaround was added. After completing and freezing the final build,
  final full SQLite/native run **869 passed352.30s**, one upstream deprecation warning
  (`artifacts/goal-planner-full-fixed-build.txt`). No service edits after that run.
  Native goal tests added to CI configuration; hosted CI remains unrun.
- Final existing frontend unit suite **92 passed442.513959ms**
  (`artifacts/goal-planner-node-final.txt`); this suite alone does not establish new
  goal interaction behavior. Final TypeScript/Vite build1.42s uses
  JSindex-DKEUHmDY.js / CSSindex-BDvYxa4w.css (`...build-final.txt`).
- Final wheel SHA256 **7da83162d05eb8a2d528314aa6a14fb939a34e739929029be82a1c7ed992fb4b**,
  all70 recursive service Python files byte-match checkout
  (`artifacts/goal-planner-final-wheel-proof.json`). Installed default runtime and
  native PostgreSQL16.15 reviews both valid (`...installed-runtime-final.json`,
  `...installed-postgres.json`). Native review creates a rules goal draft and pending
  task, verifies exact frozen decomposition and same-request draft/accept replay after
  actual native backup/restore. That installed goal task stays unapproved; actual goal
  execution is covered by source HTTP tests above. Native owned target requests3 and
  owned source requests1; external targets/sources0; default target requests0.
- Built-app fixture uses a local mock provider. A committed draft POST with substituted
  503 preserves the frozen request; reload restores goal/mode and same-request retry
  retrieves the ready draft. Review acceptance creates one new pending task. Manual
  progress displays0/2 for each of two objectives and explicitly distinguishes check
  completion from goal achievement (`...ui-lost.txt`, `...ui-restored.txt`,
  `...ui-ready.txt`, `...ui-pending.txt`, inspected `...ui-final.jpg`). Final cosmetic
  asset-name/dependency/button spacing changes were included before screenshot;
  subsequent title wrapping was built before final width measurement. Full role,
  navigation race, keyboard and screen-reader journeys remain unverified.
- Final pending document measures320/320 and390/390 client/scroll widths, dialog277/277
  and347/347 (`artifacts/goal-planner-ui-widths.json`). Intentional table overflow,
  hidden labels and320px internal report-action overflow remain. No actual mobile
  touch/zoom or screen-reader claim.
- Owned fixture tabs closed and process stopped: target requests0, ordinary task
  POSTs0, next-plan POSTs0, observation-plan POSTs0, goal draft POSTs2 and mock provider
  calls1; temporary data removed (`artifacts/goal-planner-ui-fixture.txt`). Existing
  preview data preserved on restart; health ok, anonymous goal-draft endpoint401 and
  final asset names confirmed (`...preview-health.json`).
- Commercial-provider semantic quality, goal predicate verification, precise objective
  scheduling, observation-selected URL integration, draft search/retention, complete
  mobile/accessibility journeys, container deployment and production operations remain
  open under [v1 readiness](V1-READINESS.md). No remote publication performed.

## Exact objective-pair execution — 2026-10-05

- New ready drafts freeze `execution:objective_pairs` into their reviewed fingerprint.
  Approval and runtime require that contract. Each asset executes only the checks
  requested for it by at least one objective, preserving planner order and deduplicating
  shared pairs. Legacy drafts/tasks without this field retain their original full union
  matrix; removing the field from a new task fails approval. Replan/retry preserve the
  stored execution contract.
- Planned/terminal task coverage, Worker process, dependency completion/handoff,
  report coverage and SQLite/native latest-evidence queries use declared pairs.
  A newer goal cannot replace earlier proof for a pair it does not select. The catalog
  denominator remains6 checks per active asset; goal execution counts still do not
  assert semantic goal verification.
- Targeted goal cases **40 passed32.38s** (`artifacts/goal-pairs-targeted-final.txt`):
  sparse two-asset cookie/CORS execution records exactly two `run_check` invocations
  and two owned GETs; an overlapping third objective shares one invocation/result.
  Actual dependency handoff carries only the parent's selected check, progress is1/1
  per objective, task/report cells are exactly selected, and overview preserves older
  unselected-pair evidence. SQLite/native cases also exercise legacy full-matrix
  approval/execution and execution-mode tamper refusal. Initial dependency/goal
  regression **58 passed45.06s** (`...targeted.txt`).
- Frontend **92 passed455.040791ms** (`...node.txt`); final TypeScript/Vite build1.46s
  (`...build.txt`), JSindex-C4hIYkEK.js / CSSindex-BDvYxa4w.css. Built-app mock-provider
  draft shows separate asset/check scopes and the new execution explanation. Accepted
  pending result table has two cells rather than four; manual progress is0/1 per
  objective (`...ui-ready.txt`, `...ui-pending.txt`). No approval in this browser fixture.
- Widths measured320/320 and390/390 document client/scroll, dialog277/277 and347/347
  (`...ui-widths.json`). Existing intentional table overflow/hidden labels and320px
  internal report controls remain. Actual mobile touch/zoom, screen reader, full roles
  and navigation race journeys are unverified. No new visual screenshot claim.
- Owned fixture tabs closed and process stopped: targets0, ordinary task/next-plan/
  observation-plan POSTs0, goal draft POSTs1 and mock provider calls1; temporary data
  removed (`...ui-fixture.txt`).
- Wheel SHA256 **43d87e21d85bd605f9ce350e18ae5f6ccca3afc52b842b28fcd2ebc8f1b06f2f**,
  all70 service Python files byte-match checkout (`...wheel-proof.json`). Installed
  default runtime and native PostgreSQL16.15 reviews valid (`...installed-runtime.json`,
  `...installed-postgres.json`). Native pending goal's execution contract and frozen
  decomposition survive actual backup/restore and cached draft/accept replay. Installed
  pending goal remains unapproved; actual sparse execution is covered by source HTTP
  tests above. Default target requests0; native owned target3/source1; external0.
- Commercial-provider quality, semantic criterion verification, observation-selected
  goal integration, follow-up/retest objective linkage and the remaining v1 gates stay
  open. No container/production/hosted-CI verification or remote publication claimed.
- Final full SQLite/native regression **875 passed361.44s**, one upstream deprecation
  warning (`artifacts/goal-pairs-full.txt`). Final build completed before the run;
  service source stayed unchanged during/after it. Existing preview data preserved
  on restart, health ok and anonymous goal-progress401, final JS/CSS confirmed
  (`...preview-health.json`).

## Objective source proof and retest history — 2026-10-05

- New [goal evidence contract](GOAL-PLANNING.md) and authenticated bounded findings
  endpoint link objectives through actual source-task evidence. Finding task references
  alone are insufficient: proof reference, task, asset, check and fingerprint must match.
  Responses project compact finding fields and counts; no raw proof or full reference
  arrays. Pagination insertion watermark does not freeze later triage/history updates.
- Same-finding retest summaries require a matching approved retest task, single
  asset/check, matching stored scope asset and recognized conclusion. Missing or
  malformed scope/primitive elements, wrong task/finding/asset/check and unapproved
  conclusions are excluded. Retests remain separately approved finding-level history;
  no claim they share original goal revision or verify its natural-language criterion.
- Final targeted SQLite/native HTTP tests **32 passed33.22s**
  (`artifacts/goal-evidence-targeted-final-source.txt`): actual owned goal header
  execution, original proof preserved, hardened lab followed by separately approved
  resolved retest, paging/search/literal wildcard handling, viewer read-only/bounds,
  six mismatched source-proof forms and eight unmatched retest forms. Original goal
  progress remains independent and `goal_verified:false`. Earlier development runs
  exposed a SQLite reserved alias and compact-test-fixture/role-helper mistakes; these
  were corrected before final proof. Intermediate30-pass run predates the primitive
  scope-element case; final32-pass source includes it.
- Frontend existing suite **92 passed554.071083ms** (`...node.txt`), not standalone
  proof of the new interactions. Final TypeScript/Vite build1.43s (`...build-verified.txt`)
  uses JSindex-CB-uAFh5.js / CSSindex-Bi_eIbTY.css. No build overlapped final full tests.
- Installed default and native PostgreSQL16.15 reviews valid (`...installed-runtime.json`,
  `...installed-postgres.json`). Wheel SHA256
  **112f7c9779dc2ecf7f964f60340f8f29e93770cb8d07f431d6dcaf3b424219c8**;
  all71 service Python files byte-match checkout (`...wheel-proof.json`). Native installed
  pending rules goal exposes empty objective evidence before/after actual backup/restore;
  it stays unapproved. Actual goal proof/retest execution is covered by source HTTP tests.
  Default target requests0; native owned target3/source1; external targets/sources0.
- Built-app fixture seeds31 synthetic proofs and one resolved retest without target
  execution. UI displays25 then6 records, searches to one record, and links its recent
  retest task and finding detail (`...ui-first.txt`, `...ui-second.txt`, `...ui-search.txt`,
  `...ui-retest.txt`). Browser evidence is synthetic metadata, not actual runtime
  execution. Search/page state is currently component memory, without URL restoration;
  full late-response/role/mobile/screen-reader journeys remain open.
- Existing preview data retained on restart, health ok and anonymous objective findings401;
  final built JS/CSS confirmed (`...preview-health.json`). Goal predicate verification,
  goal-specific follow-up/retest-task references and broader v1 readiness remain open.
- Final full SQLite/native regression **907 passed394.00s**, one upstream deprecation
  warning (`artifacts/goal-evidence-full.txt`). No service edits during/after that run.
  CI configuration includes the new native cases; hosted CI unrun.
- Initial synthetic retest fixture copied two-asset done count into a one-asset task.
  Corrected the fixture count and reran goal→recent retest navigation; final detail
  shows1/1 (`...ui-retest-final.txt`). This was fixture metadata, without runtime target
  execution. Both owned fixture processes stopped and all owned tabs closed: target
  requests0, task/next-plan/observation-plan/goal-draft POSTs0, provider calls0, temporary
  data removed (`...ui-fixture.txt`, `...ui-fixture-final.txt`).

## Goal-origin retest plans — 2026-10-05

- Operators can create a pending single-finding retest from an objective's verified
  source evidence. The immutable goal_retest reference records source task/objective
  names and IDs, plan/finding fingerprints, asset/check and request ID. Approval/run
  require local reference/execution consistency. Final transaction rechecks source proof
  and current asset, atomically storing task, coverage and audit. Competing active retests
  are refused; same deterministic request returns its original task even after replacement.
- Replacement/retry retain the origin, and retest results copy it. New task detail links
  to the original goal and finding. Origin is historical provenance; it does not claim
  unchanged source semantics/revision, external authenticity or semantic goal achievement.
- Final targeted goal-origin and evidence suites **40 passed41.38s**
  (`artifacts/goal-retest-targeted-final-source.txt`): actual owned goal/retet execution,
  pending creation/no new target before approval, nonce replay/conflicting active plan,
  preserved origin on replan/resolved result, wrong proof/operator/tamper refusal and
  final-write source-change rollback. Both SQLite/native variants covered.
- The previous evidence viewer-read test incorrectly called a context-manager helper
  without entering it and therefore exercised the existing administrator session.
  Corrected it to enter an actual viewer session; viewer authenticated read/no writes
  and viewer retest POST403 now execute in both backends. Earlier viewer-read claims
  were weaker than stated. Initial new role test caught the same helper misuse before
  final verification; backend role enforcement was unchanged.
- Final full SQLite/native regression **915 passed404.98s**, one upstream deprecation
  warning (`...full.txt`), with final build completed before tests and no service edits
  during/after them. Two subsequently added actual application close/reopen tests
  **2 passed3.07s** (`...restart.txt`): stored pending origin and same-request identity,
  no target during restart/replay, then newly approved execution with origin in result.
  These two tests were not part of the915-test collection. No OS reboot/process-kill claim.
- Frontend **92 passed616.134833ms** (`...node.txt`); final TypeScript/Vite build1.57s
  (`...build-final.txt`), JSindex-qb9xqnII.js / CSSindex-Bi_eIbTY.css. Existing unit tests
  alone do not prove new request recovery interactions.
- Wheel SHA256 **d136e5c4d3e90a7a99066f86099755dd52607d017619e59579319e80b9a92ba4**;
  all72 service Python files byte-match checkout (`...wheel-proof.json`). Installed default
  runtime and native PostgreSQL16.15 reviews valid (`...installed-runtime.json`,
  `...installed-postgres.json`). These existing installed scenarios exercise goal drafts
  and recovery, not goal-origin retest backup/restore specifically. Native owned target3/
  source1, external0; default targets0. Source application restart tests cover new origin
  persistence and execution in both backends.
- Built-app synthetic proof fixture commits an objective retest then substitutes503.
  Input row preserves its request; a new document reloads goal progress/proofs and
  retrieves the original pending task via the same request (`...ui-lost.txt`,
  `...ui-restored.txt`). No approval/target request in this browser fixture. Request ID
  is saved per actor/task/objective/finding before POST; storage failure refuses POST.
  Full role/navigation race/keyboard/mobile/screen-reader journeys remain open.
- Existing preview data retained on restart, health ok and anonymous objective retest
  POST401; final asset names confirmed (`...preview-health.json`). Hosted CI/container/
  production verification and semantic-goal/full v1 gates remain open.
- Recovered built-app detail is the single original pending goal retest, with one
  asset/check and the frozen original task/objective names and navigation links
  (`...ui-pending.txt`). Owned tab closed, flag removed and fixture shut down:
  target requests0, ordinary task/next-plan/observation-plan/goal-draft POSTs0,
  objective retest POSTs2, provider calls0; temporary data removed (`...ui-fixture.txt`).

## Goal-preserving follow-up rounds — 2026-10-05

- Goal follow-ups retain the original objective definitions, selected asset/check
  combinations and Worker dependencies. They do not add unselected catalog checks.
  Retry or active in-scope requests propose the entire original selected matrix,
  including completed cells, for a new approval. Failed-cell-only execution is not
  implemented. Out-of-goal todo requests require a new reviewed goal draft.
- Proposal fingerprints and final-write checks include the goal definition; mixed
  legacy histories without matching goals are refused. Replacement/retry preserve
  the reference. Single-finding goal retests use their original separate flow.
- Targeted SQLite/native goal-round and ordinary follow-up suites **32 passed31.83s**
  (`artifacts/goal-rounds-targeted-final.txt`). Owned sparse cookie/CORS execution
  checks exact pairs and dependencies, repeated completed evidence, no preapproval
  requests and only one initial mocked provider call. Scope changes and mutated
  source goals refuse creation without partial children.
- Final full SQLite/native regression **927 passed416.36s**, one upstream Starlette
  deprecation warning (`...full.txt`). Includes the two preceding goal-origin
  application restart cases. No service Python edits during/after this full run.
- Final frontend **92 passed415.361791ms** (`...node-final-ui.txt`); TypeScript/Vite
  build **1.41s** (`...build-final-ui.txt`), JSindex-BwgeXwod.js / CSSindex-Bi_eIbTY.css.
  Corrected the generic all-assets execution paragraph for sparse goal plans after
  the first browser inspection; final built screen shows per-objective combinations.
- Wheel SHA256 **dbfdd035ffe1ab35aff498ba3a20d9df93b535025f494a03c2871fbe5d6054d9**,
  all72 service Python files byte-match checkout (`...wheel-proof.json`). Installed
  default runtime with final UI and native PostgreSQL16.15 reviews valid
  (`...installed-runtime-final-ui.json`, `...installed-postgres.json`). Default target
  requests0; native owned lab3/source1, external0. Existing installed recovery and
  backup scenarios do not specifically prove new goal-round backup/restore.
- Owned built-app synthetic goal fixture shows preserved objectives, repeated
  completed count1 and two source cells, then creates a pending round1 with both
  cells unexecuted (`...ui-ready-final.txt`, `...ui-pending.txt`). Browser fixture
  approval was not granted. Owned tab/process closed: target requests0, next-plan
  POSTs1, task/observation-plan/goal-retest/goal-draft POSTs0, provider calls0;
  temporary data removed (`...ui-fixture.txt`). This is DOM interaction evidence,
  not real execution or screenshot/mobile/screen-reader validation.
- Preview retains existing data, health ok, anonymous next-plan401 and final
  built assets confirmed (`...preview-health.json`). Hosted CI, containers,
  production operation, commercial provider quality, semantic goal verification,
  failed-cell-only optimization and remaining full v1 gates stay open.
