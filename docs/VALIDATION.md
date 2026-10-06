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
  runtime review valid with 0 target requests. Installed native review valid:
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
- Initial targeted25 passed5.66s. First full:736 passed, 1 failed252.32s because the
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
  runtime review rerun against final static assets valid with 0 target requests
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
  Default installed review valid with 0 target requests (`...installed-postgres.json`,
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
  final CSS build and valid with 0 target requests (`...ui-installed-postgres.json`,
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

## Goal evidence navigation recovery — 2026-10-05

- Task detail now stores goal progress expansion and independently applied objective
  searches, page positions and pagination snapshots in its URL. Reload and Back from
  findings restore the selected collection. Draft search input is not bookmarked.
  Only g1..g12 are parsed; only objectives returned for the actual task are rendered
  and queried. Normalization bounds search/offset/snapshot and removes unsupported
  fields. Leaving/closing/changing task removes the goal bookmark from the new route.
- Late position updates require matching task/objective/search/offset/snapshot.
  Progress requests abort on unmount and require current session/task expansion.
  Objective collections reuse the existing cancellable pager, with explicit refresh
  rather than periodic polling. Error retry preserves position; Latest resets to
  the first page/new snapshot with the same applied search. Refresh failures remain
  visible instead of displaying an old successful list as the current result.
- Frontend **97 passed431.995041ms** (`artifacts/goal-navigation-node-verified.txt`),
  including five new independent-bookmark, normalization, route-exit and stale-position
  cases. Final TypeScript/Vite build **1.43s** (`...build-verified.txt`),
  JSindex-KKOOlw2R.js / CSSindex-Bi_eIbTY.css.
- Existing source SQLite/native objective proof suites **32 passed33.67s**, one
  upstream deprecation warning (`...api-native.txt`). Initial run without PostgreSQL
  opt-in was **16 passed/16 skipped** (`...api.txt`); the explicit native run corrected
  that verification gap. No service Python changed; the previous927-test full run
  remains source-service evidence, not a new full run for this frontend change.
- Owned built-app synthetic31-proof fixture: second-page26–31, URL reload, finding
  detail and app Back, search for 검수30 and filtered reload were inspected
  (`...ui-page-two.txt`, `...ui-restored.txt`, `...ui-back.txt`, `...ui-search-restored.txt`).
  Final build also restored page26–31, handled explicit evidence503/retry at unchanged
  URL and progress503 during document restore, then restored its stored evidence page
  (`...ui-final-restored.txt`, `...ui-query-failure-final.txt`, `...ui-query-retry.txt`,
  `...ui-progress-failure.txt`, `...ui-progress-retry.txt`, `...ui-back-final.txt`).
  Final filtered document restore is also recorded (`...ui-search-restored-final.txt`).
  An earlier automatic poll recovered between flag removal and a retry click; that
  timed-out click is not claimed as retry evidence. Explicit collection refresh now
  preserves the original manual-query behavior and the final retry was executed.
- Installed wheel with final separately built UI review valid, target requests0
  (`...installed-runtime-verified.json`). Service bytes unchanged from wheel SHA256
  **dbfdd035ffe1ab35aff498ba3a20d9df93b535025f494a03c2871fbe5d6054d9**.
  All72 service files were byte-compared again (`...wheel-proof.json`).
  Installed smoke does not prove browser navigation; owned browser checks above do.
- Preview retains existing data, health ok, anonymous goal-progress401 and final
  assets confirmed (`...preview-health.json`). Browser evidence is synthetic DOM
  interaction, not target execution, production data or full mobile/screen-reader,
  multi-objective browser race, role journey or semantic-goal verification.
- Both owned fixture processes and tabs closed; each fixture logged target requests0,
  task/next-plan/observation-plan/goal-retest/goal-draft POSTs0, provider calls0 and
  temporary data removed (`...ui-fixture.txt`, `...ui-failure-fixture.txt`).
  Owned failure flag removed. Full v1 readiness gates remain open.

## Installed goal round/retest backup recovery — 2026-10-05

- Added `scripts/review_goal_recovery.py`: actual wheel installed outside checkout
  with locked runtime dependencies, owned loopback HTTP target and real server
  processes. Each SQLite/native PostgreSQL scenario generates a rules goal, approves
  source execution, reads actual objective proof, creates/replaces pending goal-round
  and goal-origin retest plans, stops the source and uses installed backup/check/restore
  and audit CLIs. No model mocking or external AI provider is involved.
- Final both-backend run **valid:true** (`artifacts/goal-recovery-installed-final.txt`),
  native PostgreSQL16.15. Restored old sessions refused; original goal draft acceptance,
  follow-up fingerprint and retest request ID preserve their documented identities.
  Round replay resolves its current replacement; objective retest nonce retains its
  original task, whose replacement replan returns the current task. Each restored
  replacement keeps its goal/reference and unexecuted pending coverage.
- **Zero target requests during restore, startup and pending-request replay**. Per
  backend exactly three owned GETs: approved source, newly approved restored retest,
  newly approved restored goal round. Retest proves missing-nosniff resolved with the
  original objective reference in the result and latest objective evidence. Completed
  round/result and same-request identities survive another real service restart.
  External target requests0. Package dependency installation accesses the package index.
- Rules goals contain all six registered checks: five completed and API authorization
  skipped because this fixture supplies no API policy. The initial rehearsal helper
  incorrectly required all six to complete and failed (`...installed-initial.txt`).
  Corrected the expectation to permit only that declared skipped check, while retaining
  exact check membership and rejecting other failed/incomplete statuses. The service
  was unchanged. Intermediate run valid (`...installed.txt`); final run additionally
  verifies audit continuation and native operation without SQLite files.
- Original audit checkpoint remains40 events; recovered chain extends it to74 events
  in each backend. Restore/session/result checks pass before cleanup; installed origins
  were inside the temporary environment, now removed (`...cleanup.json`). Native
  cluster is stopped by the helper's finally block; owned target/server contexts close.
- Reused wheel SHA256 **dbfdd035ffe1ab35aff498ba3a20d9df93b535025f494a03c2871fbe5d6054d9**;
  all72 service Python files freshly byte-match checkout (`...wheel-proof.json`). No
  service or frontend edits, so this turn did not repeat the earlier full/unit/UI runs.
- CI now runs SQLite/native installed goal recovery in their respective jobs. Hosted
  CI is unrun. This evidence covers single-asset rules goals and normal stopped backup;
  sparse/dependent goal backup scenarios, power-loss recovery, PITR, remote storage,
  commercial-provider quality and semantic-goal/full v1 gates remain unproven.

## Installed goal process-crash recovery — 2026-10-05

- `review_goal_recovery.py --crash` now SIGKILLs only its live owned service Popen
  handles, waiting for actual exit -9: pending goal plans, in-flight objective retest,
  in-flight goal follow-up. In-flight GET is held by an owned target Event; its entry
  and task running status are checked before killing. No production PID is selected.
- Final installed SQLite/native PostgreSQL rehearsal **valid:true** for both
  (`artifacts/goal-crash-recovery-installed-final.txt`): three owned service SIGKILLs
  and five owned GETs per backend. First pending restart preserves plan references,
  same-request IDs and exact task count with no new target request. Active restarts
  mark all unfinished selected coverage interrupted and preserve goal/retest origin.
- Each interrupted task's retry is pending/unapproved, retains its origin and round,
  and repeated retry POST returns the same task with exact count +1. No automatic
  target request before a new explicit approval. Approved retries finish; final reopen
  preserves current follow-up identity, resolved retest origin/latest proof and false
  semantic goal verification. Counts distinguish approved-but-interrupted GETs from
  completed retries: source1, interrupted retest1, approved retest retry1, interrupted
  follow-up1, approved follow-up retry1. External target requests0.
- Same final helper without crash also **valid:true** in both backends, three owned
  GETs and zero SIGKILLs (`...normal-regression.txt`). Earlier intermediate crash run
  covered pending/follow-up only and four GETs (`...installed.txt`); final run extends
  coverage to in-flight retest and exact retry counts rather than reusing that claim.
- Crash-mode backup checkpoint43 events extends to99 after restored execution; source
  checkpoint remains unchanged. Normal mode retains its40→74 continuation. API policy
  absent: five rules checks complete, API authorization skipped, not successful.
- Temporary installations removed and all72 service files still byte-match wheel
  SHA256 **dbfdd035ffe1ab35aff498ba3a20d9df93b535025f494a03c2871fbe5d6054d9**
  (`...proof.json`). Owned server/target contexts close; native cluster stops in finally.
  No service/frontend changes, so previous unit/full/UI evidence was not rerun here.
- CI storage jobs now use crash mode; hosted CI unrun. Database and host remain alive
  during these process kills. This does not prove hardware power-loss durability,
  PostgreSQL crash/PITR, remote backups, interrupted provider calls, sparse/dependent
  goal recovery, complete production readiness or semantic-goal/full v1 completion.

## Goal evidence execution-approval consistency — 2026-10-05

- Found that goal proof/progress/creation accepted source records without a valid
  execution approval, and objective retest summaries accepted any non-null approval
  value. New source regressions exercise evidence, progress, retest creation and
  follow-up read with None/bool/zero/negative/string timestamps; history regressions
  cover malformed retest timestamps. Source proof is generated by an actual approved
  owned HTTP run before damaging metadata, rather than fabricating proof links.
- Before fix **26 failed/8 passed** (`artifacts/goal-approval-before.txt`):21 source
  evidence/progress/retest cases plus five malformed retest-history cases failed.
  Follow-up before-correction run had three extra helper failures: the test wrongly
  read evidence_ids from compact HTTP finding summaries. Corrected it to read the
  stored finding. Corrected follow-up reproduction **4 failed/3 passed**
  (`...followup-before-corrected.txt`); existing None/false/zero refusal was intact.
- Goal proof/progress now require positive finite numeric source approval; booleans
  and strings are excluded. Unapproved recorded outcomes are not_recorded in objective
  progress; ordinary unexecuted not_started cells remain. New objective retests and
  follow-up proposals are refused; existing evidence is retained. Related retest
  histories/counts/latest result apply the same numeric approval requirement via
  SQLite JSON types and guarded PostgreSQL numeric casts. This is local metadata
  consistency, not external authenticity or semantic goal verification.
- Final targeted SQLite/native evidence, retest and goal-round suites **118 passed
  109.51s**, one upstream deprecation warning (`...targeted.txt`). Covers actual valid
  approvals/results, source mutation refusal, no new child/event/target on rejected
  operations and retained original proof, alongside existing origin/round contracts.
- Final full SQLite/native regression **993 passed469.22s**, one upstream Starlette
  deprecation warning (`...full.txt`). Service Python was unchanged during/after the
  run; frontend was unchanged throughout this increment. CI already includes the
  expanded native evidence module, but hosted execution remains unverified.
- New wheel SHA256 **8e25f7105518290348e594c1f4fd033fbb20cae28540e809a409aed18bd252c2**;
  all72 service files byte-match final checkout (`...wheel-proof.json`). Installed
  default runtime valid, targets0 (`...installed-runtime.txt`). New installed wheel's
  SQLite/native goal crash/backup recovery also valid (`...installed-crash.txt`),
  three SIGKILLs/five owned GETs per backend, restored preapproval requests0,
  audit43→99, API policy check skipped and semantic goal verification false.
  Temporary installations removed (`...installed-cleanup.json`).
- Owned preview had no active tasks; clean restart retains exact record counts and
  task states, health ok and anonymous goal-progress401 (`...preview-before.json`,
  `...preview-health.json`). Frontend unchanged, retains index-KKOOlw2R.js; prior
  97-unit/browser evidence is not a fresh run in this backend change. Hosted CI,
  hardware/DB-server crash, sparse recovery and other full v1 gates remain open.

### Installed pending-goal PostgreSQL immediate shutdown recovery (2026-10-05)

- Extended `scripts/review_goal_recovery.py` with `--database-crash`, requiring
  `--crash` and a native PostgreSQL backend. Only its temporary owned cluster is
  stopped with `pg_ctl -m immediate` after the pending source service is killed.
  Startup-log checks require interruption, automatic WAL recovery and readiness;
  audit verification before/after requires the exact same checkpoint. Existing
  HTTP checks then prove retained pending plans/request identities, no automatic
  target GET and fresh approvals before subsequent execution.
- Current installed wheel SHA256
  `8e25f7105518290348e594c1f4fd033fbb20cae28540e809a409aed18bd252c2`;
  all 72 service Python files still byte-match the checkout
  (`artifacts/goal-database-crash-wheel-proof.json`). Service/frontend unchanged;
  the previous 993-test run remains the last full-suite evidence.
- `--backend both --crash --database-crash` passed against SQLite and native
  PostgreSQL16.15 (`artifacts/goal-database-crash.txt`). Native immediate shutdown
  logged WAL recovery and preserved the committed audit checkpoint. Each backend
  made five owned target GETs, three owned service SIGKILLs, zero external target
  requests and zero preapproval restore requests; audit43→99. SQLite receives no
  database shutdown. API authorization remains skipped without a policy and
  semantic goal verification remains false.
- Normal `--backend both` control passed (`...-control.txt`), three owned GETs
  per backend, no service/database crash, audit40→76. Invalid SQLite+database-crash
  and PostgreSQL+database-crash without `--crash` reject with exit2 before setup.
  Both temporary installations were removed and the retained preview health is
  ok (`...-cleanup.json`). Native CI now requests this mode; hosted CI was not run.
- This covers an immediate database-server shutdown while the host/storage remain
  alive and after committed pending plans. It does not establish hardware power
  loss, lost/unflushed storage writes, a database crash during active work, PITR,
  remote-backup restoration or supported-version upgrades. Those gates remain open.

### Ordinary follow-up approval-record consistency (2026-10-05)

- Ordinary next-plan source/history checks previously accepted truthy boolean,
  negative-number or string approval metadata. The corrected pre-change HTTP
  reproduction produced 16 failures and 12 passes across source/ancestor cases on
  SQLite/native PostgreSQL (`artifacts/followup-approval-before-corrected.txt`).
  The first attempt used a nonexistent event-page helper and is not behavioral
  evidence (`...-before.txt`); replacing it with the existing event count API made
  the reproduction meaningful before service changes.
- Shared `planning_history.has_execution_approval` requires a positive finite
  numeric timestamp and remains available through the goal-planner import. Next
  proposals, approved history evidence and earlier-round links use this guard.
  Corrupt source approval also refuses already-accepted request replay through
  history validation. Rejections retain stored completion proof and create no
  task/coverage/evidence/event or target request.
- Seven invalid approval representations × direct source/ancestor/already-accepted
  source × two backends cover 42 new cases. Related next-plan/goal-round/goal-evidence
  tests: **172 passed**,155.94s (`...-targeted.txt`). Final full backend suite with
  owned PostgreSQL enabled: **1035 passed**,506.30s (`...-full.txt`), one upstream
  Starlette deprecation warning. No service/test edits during or after the full run.
- Standard isolated wheel build succeeded (`...-wheel-build-isolated.txt`); the
  no-build-isolation attempt lacked local bdist_wheel and failed (`...-wheel-build.txt`).
  Final wheel SHA256
  `26aef0a38a9a39ad4e75cef9eafe1ed7ab26bcb7cc3ee0d3b3f8d6baa173ba40`;
  all72 service Python files byte-match the checkout (`...-wheel-proof.json`).
  Installed default runtime with the retained frontend passed, target requests0
  (`...-installed-runtime.txt`). Installed SQLite/native goal crash recovery passed
  (`...-installed-recovery.txt`), three owned service SIGKILLs and five owned GETs
  per backend, audit43→99, zero preapproval/external target requests. PostgreSQL
  immediate shutdown confirmed WAL recovery and preserved its audit checkpoint.
  API authorization is skipped without policy; semantic goal verification is false.
- Temporary installations removed (`...-installed-cleanup.json`). Owned preview
  had zero active tasks and was cleanly restarted; exact record counts/task states
  persist, health ok, anonymous next-plan401 (`...-preview-before.json`,
  `...-preview-health.json`). Frontend retains index-KKOOlw2R.js; no frontend
  rebuild or fresh browser/unit run was needed for this backend-only change.
- This is stored-metadata consistency, not approval authenticity. Workspace legacy
  coverage display retains its existing compatibility contract. Sparse retry
  execution, full mobile/screen-reader journeys, actual container/hosted CI runs,
  semantic goal evaluation and other full v1 gates remain open.

### Installed database loss during approved goal GETs (2026-10-05)

- Added optional `--database-crash-in-flight` to the installed recovery rehearsal,
  requiring `--database-crash` (which already requires `--crash` and PostgreSQL).
  Each restored goal retest/follow-up first recovers from its existing service
  SIGKILL, receives a fresh explicit approval and reaches an owned held GET. The
  temporary database is then stopped immediately and restarted while the service
  remains alive. WAL recovery and the pre-crash audit prefix must verify.
- Runtime ownership deliberately does not reconnect after database loss. The old
  service must refuse task reads, approvals and health with503. The harness kills
  only that owned stale service and starts a fresh one; the persisted task must
  recover as interrupted with its original goal reference/round and no new target
  request. Repeated retry requests create one pending plan, a fresh approval
  completes it, and the final restart preserves resolution/results/continuation.
- Initial exploratory run expected a running-task read after database restart and
  correctly received503 (`artifacts/goal-active-database-crash.txt`); this is the
  existing ownership-fencing contract, not a service defect. The next harness
  attempt assumed a health `status` body, but ownership middleware returns a503
  detail before that handler (`...-verified.txt`). Both failed attempts are not
  passing evidence. The final harness checks the actual fenced HTTP contract.
- Final `--backend both --crash --database-crash --database-crash-in-flight` passed
  (`...-final.txt`). Native PostgreSQL16.15: seven owned GETs, five owned service
  SIGKILLs, three immediate database shutdowns (one pending, two active GETs),
  audit43→119. Active audit checkpoints retained event66 and event96 respectively;
  each records WAL recovery, stale-service read/approval/health refusal and fresh
  approval completion after service restart. SQLite: five GETs, three SIGKILLs,
  no database crash, audit43→99. Both have zero preapproval restore requests and
  zero external target requests; semantic goal verification remains false.
- Normal `--backend both` control passed, three GETs/no crashes per backend,
  audit40→76 (`...-normal-control.txt`). Existing pending database-crash control
  also passed, five GETs/three service SIGKILLs per backend, audit43→99 and no
  in-flight database shutdowns (`...-pending-control.txt`). Invalid optional-flag
  combinations reject with exit2 before setup (`...-proof.json`). Three successful
  temporary installations removed (`...-cleanup.json`); retained preview health ok.
- Service/frontend unchanged. Reused verified wheel SHA256
  `26aef0a38a9a39ad4e75cef9eafe1ed7ab26bcb7cc3ee0d3b3f8d6baa173ba40`, all72 service
  Python files freshly byte-match the checkout (`...-proof.json`). Prior1035 tests
  remain the last full-suite evidence; no broad unit/frontend rerun for this
  harness-only increment. Native CI now requests the extra mode; hosted CI unrun.
- This proves database-server loss during a held, already-authorized HTTP request
  and recovery through new service ownership and new approval. It does not prove
  a crash during database writes/commit, hardware power loss, storage failure,
  PITR or remote-backup recovery. Those and other full v1 gates remain open.

### Installed follow-up write interrupted before parent linkage (2026-10-05)

- Added `--database-crash-write` to the installed recovery helper, requiring the
  existing native `--database-crash` contract. It creates a separate owned
  `goal_write` schema and real loopback goal execution/todo/next-plan HTTP flow.
  A temporary BEFORE INSERT trigger at the parent upsert requires the already
  staged child with correct followup_of and exactly six coverage records in that
  transaction. Only then does it increment a nontransactional probe sequence and
  sleep. The harness observes that signal before immediate database shutdown.
  This is the actual installed application transaction, not a separately simulated
  write or a caught SQL exception used as a proxy for server failure.
- WAL startup recovery must be observed. The interrupted HTTP mutation and stale
  health return503. After stopping that owned service, task/coverage/goal-plan rows
  must exactly match their pre-write snapshot and the audit checkpoint must match
  its pre-write value. The fixture trigger/function/sequence are removed. Fresh
  service startup retains no parent next_plan_id; the same reviewed fingerprint
  creates one pending plan with six not_started cells, repeated POST returns that
  plan, and no target request occurs until a new explicit approval.
- Native PostgreSQL16.15 combined mode passed
  (`artifacts/goal-write-database-crash.txt`). `--backend both` with all crash flags
  also passed (`...-both.txt`); the separate write scenario is native only. Each
  write scenario made two owned GETs, one immediate DB shutdown and one owned
  service SIGKILL, audit28→48. The exact pre-write audit28 checkpoint survived
  the crash; preapproval recovery and external target requests were0. Existing
  recovery scenarios remain valid: SQLite five GETs/audit43→99; PostgreSQL seven
  GETs/audit43→119 with two in-flight DB ownership-loss checks.
- Normal `--backend both` control passed with the optional write result null,
  three GETs per backend/audit40→76 (`...-control.txt`). Invalid write-flag
  combinations reject with exit2 before setup (`...-proof.json`). All three
  successful temporary installations were removed (`...-cleanup.json`). Retained
  preview health is ok; no preview restart or data mutation was needed.
- Service/frontend unchanged; verified wheel SHA256
  `26aef0a38a9a39ad4e75cef9eafe1ed7ab26bcb7cc3ee0d3b3f8d6baa173ba40` still matches
  all72 service Python files (`...-proof.json`). The prior1035-test run remains
  the last full-suite evidence. Native CI now requests the write mode; hosted CI
  was not run. No broad unit/frontend rerun for this harness-only addition.
- This covers one uncommitted follow-up transaction after child/coverage staging
  and before parent linkage/audit append/commit. It does not establish every write
  boundary, an already-staged audit append, commit acknowledgement loss, hardware
  power loss, failed storage, PITR or remote recovery. Full v1 gates remain open.

### Installed staged audit append rollback on database shutdown (2026-10-05)

- Added `--database-crash-audit`, requiring `--database-crash-write`, to the
  installed goal recovery helper. A separate owned `goal_write_audit` schema
  repeats the real HTTP follow-up creation. A BEFORE UPDATE audit-state trigger
  checks the staged child, all six coverage cells, the parent's next_plan_id,
  inserted audit event and event_hashes entry matching the proposed new head and
  old previous head. Only that confirmed stage signals the nontransactional probe
  sequence; the database is immediately stopped before audit-state update/commit.
- Snapshots now include task/coverage/goal-plan records, events, event_hashes,
  audit_state and storage_metadata. All must exactly match before/after shutdown;
  independent before/after digests are emitted. WAL recovery and the exact prior
  audit checkpoint must verify. The stale service refuses the mutation/health;
  after fixture removal and service restart, the same fingerprint creates one
  unapproved pending plan, duplicate submission returns it and fresh approval
  completes it without any preapproval target request.
- Native combined mode passed (`artifacts/goal-audit-database-crash.txt`). Final
  script's `--backend both` with all crash flags passed (`...-both.txt`). Both
  record-stage and audit-stage scenarios each made two owned GETs, one immediate
  database shutdown and one owned service SIGKILL; audit event count28→48, exact
  retained crash checkpoint seq28. Final sequence53 differs from event count48;
  the resulting chain and checkpoint extension verify despite identity gaps.
  Each before/after snapshot digest pair is equal; audit-stage proof includes the
  staged parent/event/hash and rollback of audit rows/state/storage watermark.
- Existing scenarios in the same final run passed: SQLite five GETs/audit43→99;
  PostgreSQL seven GETs/audit43→119 and both in-flight ownership-loss recovery
  checks. No external target/preapproval recovery requests. Normal both-backend
  control passed with both optional write reports null, three GETs per backend,
  audit40→76 (`...-control.txt`). Invalid audit-flag combinations reject exit2
  before setup (`...-proof.json`). Three successful temporary installations were
  removed (`...-cleanup.json`); retained preview health ok, no data change/restart.
- Service/frontend unchanged; reused wheel SHA256
  `26aef0a38a9a39ad4e75cef9eafe1ed7ab26bcb7cc3ee0d3b3f8d6baa173ba40`, all72 service
  Python files freshly byte-match (`...-proof.json`). Prior1035 tests remain the
  last full-suite evidence. Native CI now requests the audit mode; hosted CI unrun.
- This covers an uncommitted audit append after parent linkage/event/hash staging
  but before audit-state update/commit. It does not establish commit acknowledgement
  loss, every write/commit boundary, hardware power loss, failed storage, PITR or
  remote recovery. Full v1 completion remains unproven and its gates stay open.

### Goal draft keyboard focus and delayed-response recovery (2026-10-05)

- Actual built-app keyboard flow reproduced a ready draft with focus left on BODY
  after its focused generation button became disabled (`artifacts/goal-focus-before.json`).
  `GoalDraftPanel` now queues focus owned by that action and its captured view/
  session, applies it after saving, and preserves any new user focus. Ready drafts
  focus a keyboard review heading; error/status notices are focusable, reset
  returns to the goal input. Goal/mode controls describe their help/provider text
  and current error via unique IDs. No target approval or request is added.
- Actual rules generation and same-request restoration focus H4 review, then Tab
  reaches acceptance; reset focuses enabled TEXTAREA with the goal preserved
  (`...-keyboard-checks.json`). Real missing-provider409 focuses the alert and
  keeps both controls enabled with valid descriptive references; Tab returns to
  generation, changing to rules then generates normally (`...-error-check.json`).
  Desktop screenshots inspected (`...-error-desktop.png`, `...-review-desktop.png`);
  review focus has a visible blue3px outline and stays inside the task dialog.
- Added `scripts/review_goal_ui.py`: disposable valid pending task, synthetic
  local provider and terminal-controlled delayed response. During held requests,
  keyboard movement to Worker asset preserves that select after completion
  (`...-other-control.json`); closing the detail preserves the list status filter
  and keeps the dialog closed (`...-closed-view.json`). Reopening restores the
  same request without another provider call; accepting the reviewed draft creates
  a pending child and settles on its dialog close control. Configured fixture made
  two provider calls, retained two unapproved pending tasks and zero target traffic;
  unconfigured fixture made0 calls/one pending task/zero target traffic
  (`...-provider-fixture.txt`, `...-error-fixture.txt`, `...-cleanup.json`).
- Fresh frontend **97 tests passed** (`...-frontend-tests.txt`) and TypeScript/Vite
  build passed (`...-build.txt`). Final JS index-CZXysOmK.js, CSS index-Bi_eIbTY.css.
  Installed existing wheel with this final UI passed, targets0
  (`...-installed-runtime.json`). All72 backend Python files still byte-match wheel
  SHA256 `26aef0a38a9a39ad4e75cef9eafe1ed7ab26bcb7cc3ee0d3b3f8d6baa173ba40`
  (`...-wheel-proof.json`); prior1035 tests remain the last backend full-suite run.
  Existing selected-palette contrast verifier also passed; this is not a full
  rendered accessibility/contrast audit.
- Owned fixture processes exited and workspaces were removed. SIGTERM left the
  earlier conversation fixture directory; its exact synthetic task/goal and no
  open file handles were verified before removing only that owned directory.
  Goal fixtures shut down with Ctrl+C. Browser tabs closed; installed temp removed.
  Main preview health ok, exact record counts/task states unchanged, serves final
  JS without a backend restart (`...-cleanup.json`, `...-wheel-proof.json`).
- Scope is desktop keyboard/DOM semantics and two real API/provider fixture flows.
  No claim of actual screen-reader, mobile touch/zoom, full UI journeys, or async
  session-switch focus verification; model-quality/security execution and full
  v1 completion remain unproven. Their explicit readiness gates remain open.


### Actual arm64 container build/restart/offline restore (2026-10-05)

- Installed Docker CLI29.7.2, buildx0.36.1 and Colima0.10.3; started a private
  Linux arm64 VM/Docker29.5.2 with two CPUs/2GiB RAM and no host mounts. All daemon,
  cache, Lima and Docker config paths belonged to one fresh temporary workspace;
  default Docker context remained desktop-linux. Host tools remain installed;
  no background service/autostart was configured.
- Actual default Dockerfile build passed (`artifacts/container-default-build.txt`).
  Initial full QA failed at published-port lookup after health/read-only/UID checks
  (`.../container-review-default.txt`): internal-only network accepted loopback
  publication but NetworkSettings.Ports returned null. An owned minimal container
  reproduced it. The harness now matches Compose's ordinary owned bridge network,
  asserts its driver/ownership and requires exactly one127.0.0.1 publication.
  This is not an egress firewall; offline maintenance still uses network none.
  Similar behavior is reported in the upstream
  [Moby discussion](https://github.com/moby/moby/discussions/53256).
- Both actual harness runs exited0/valid:true (`.../container-review-default-fixed.txt`,
  `.../container-review-postgres-extra-fixed.txt`): image build; UID10001; read-only
  root and writable volume; cap-drop/no-new-privileges; actual health and bundled
  UI; HTTP setup/auth; pending unapproved task; live backup/checkpoint capture and
  duplicate rejection; restart retains data/cookie; offline restore/chain verification;
  restored cookie rejected, password retained, post-backup note absent; clean stop.
  Both report target_requests0. Extra mode imports locked psycopg3.3.6; both HTTP
  and restore scenarios use SQLite, not native PostgreSQL.
- Owned review/debug containers, volumes and networks removed; warm image removed;
  dedicated VM and its data deleted; private temporary root removed. Cleanup proof
  lists no containers/volumes and only built-in bridge/host/none networks
  (`.../container-cleanup-proof.json`, `.../container-vm-cleanup.txt`). Retained preview
  health ok, exact record counts/task states unchanged (`.../container-preview-proof.json`).
- No service/frontend change; prior1035 backend/97 frontend passes remain the latest
  suite evidence. These are actual local arm64 Dockerfile/harness results. Hosted CI,
  amd64/multi-architecture, actual Compose startup, PostgreSQL container storage,
  production deployment/egress controls and full v1 readiness remain unverified.


### Actual Compose and PostgreSQL-container recovery (2026-10-05)

- Added `scripts/review_compose.py`: stdlib orchestration of the repository's actual
  compose.yml plus a temporary override. Requires Compose2.24.4+ for !override;
  ephemeral loopback port replaces the original8787 mapping. Unique project/image/
  named volumes; inherited application/Compose variables removed, explicit0600
  synthetic env file, no user .env. QA overrides image tag/port/health interval/
  restart policy. Actual model and running container check read-only/UID10001/
  cap-drop/no-new-privileges and named data mount. Ordinary app bridge is not an
  egress firewall; optional database-only network is internal with no published DB
  ports. Base Compose deployment behavior beyond these QA changes is not assumed.
- Final unchanged script ran both modes exit0/valid:true on Linux arm64,
  Docker29.5.2/Compose5.5.0 (`artifacts/compose-final-sqlite.txt`,
  `.../compose-final-postgres.txt`, `.../compose-final-proof.json`). Each builds the
  real app, starts healthy, serves real UI bundles, rejects anonymous data access,
  performs setup/auth and confirms /api/settings.storage equals the requested
  backend. One synthetic asset/task remains pending and unapproved, target_requests0.
- Actual online installed backup/audit CLI exports backup/checkpoint; later HTTP
  note is added. App container is stopped/deleted/recreated; native mode also
  stops/deletes/recreates the DB container. Named volumes retain all records,
  login cookie/password and the later note. App then stops for restore: SQLite
  restores its DB; PostgreSQL initializes/restores fresh owned_restored schema,
  verifies original owned_source still has the later note, switches actual Compose
  schema setting and recreates the app. Audit chain verifies against pre-note
  checkpoint; old cookie rejected401, password login succeeds, original asset/
  pending task retained, later note absent. Native data mount contains no SQLite DB.
  Both normal stops finish exit0/143; each fixture cleans its own project resources.
- Native DB is PostgreSQL16.15 from postgres:16-alpine, resolved digest
  `postgres@sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea`.
  Digest/version are reported; --postgres-image accepts a PostgreSQL16-compatible
  pinned image. This ephemeral DB uses a synthetic owner account, not production
  privilege/credential validation. Checkpoint is in the fixture data volume, not
  independently trusted remote storage. No DB-crash/WAL/PITR claim for this run.
- First VM attempt hit macOS UNIX socket path length in the default temporary
  directory (`.../compose-vm-start.txt`); moved only that owned setup/cache to short
  /tmp path before successful startup (`.../compose-vm-start-short-path.txt`).
  Final cleanup found no containers/volumes and only built-in bridge/host/none;
  owned app images absent, dedicated VM/data/private root removed, default context
  remains desktop-linux (`.../compose-cleanup-proof.json`, `.../compose-vm-cleanup.txt`).
  Compose host plugin remains installed with no daemon autostart. Retained preview
  health ok, exact records/task states unchanged. Both-mode reports bind results
  to the final script SHA256, freshly checked after cleanup.
- CI now includes both actual Compose modes. Hosted CI/amd64/multi-architecture
  remain unrun; production rollout, retention/resource SLO, independent checkpoints,
  official releases and full v1 readiness remain open. Service/frontend unchanged;
  prior1035 backend/97 frontend tests remain latest suite evidence. Existing selected
  design-pair verifier and diff whitespace check pass; no full accessibility claim.


### Goal follow-up selected pairs and retained prior proof (2026-10-05)

- Added goal_selection contract for new objective_pairs follow-ups: immutable source,
  canonical nonempty asset/check subset and fingerprint. Select failed/missing/stale
  cells and explicit active-todo check requests; recursively include each selected
  child's complete declared parent checks for task-local dependency handoffs. Original
  goal/decomposition/assets/checks/dependencies stay unchanged. Approval pins a copy;
  execution rejects changed/removed contracts. Replan/retry and continuation replay
  preserve the subset. Legacy plans retain their full approved matrix.
- Engine skips even the base GET for assets without selected checks. Planned slots
  and SQLite/native PostgreSQL latest-coverage ranking filter by the selected pairs,
  preserving untouched source coverage. Goal progress aggregates same-goal approved
  history in one read snapshot, rejects incompatible scope/tool proof, keeps original
  cell IDs/source_task_id and treats current pending selection as unexecuted. Findings
  remain task-local; no semantic goal_verified claim is added.
- New actual-transport regression: two assets/two declared tools, one owned failure;
  follow-up selects only second-asset CORS. After fresh approval exactly one /other/
  GET and one completed cell; first asset unrequested, source coverage unchanged,
  aggregate completed4 and both objectives2/2. SQLite/native repeat tests cover
  attempts/replay, todo-request repeats and invalid selection/approval metadata.
  Baseline892c8cc fails missing goal_selection in a temporary owned checkout
  (`artifacts/goal-selection-before.txt`), which was removed. Expanded147 tests pass
  (`.../goal-selection-expanded-tests.txt`); final null-plan guard/selection tests20
  pass across both stores (`.../goal-selection-final-guard-tests.txt`). Final scope-change/
  accepted-replay damage cases also pass,24 total (`.../goal-selection-final-scope-replay-tests.txt`):
  stale review rejected without partial child; only stale/failed pairs reapproved;
  damaged approved selection rejects replay while original completed result remains.
- Real built UI on a disposable synthetic seeded fixture shows one CORS pair, zero
  repeated completed pairs, acceptance to a pending detail with one unexecuted row
  and prior-progress1/2. Corrected a stale whole-matrix explanation found during
  actual review. Screenshot/DOM recorded (`.../goal-selection-ui-review.png/json`).
  Fixture provider_calls0/target_traffic0, one pending unapproved child; cleaned
  fixture/tabs (`.../goal-selection-ui-fixture.txt`, `.../goal-selection-cleanup-proof.json`).
  This is desktop UI of explicitly seeded proof, not an actual scan or mobile/SR test.
- Node20 in the web working directory refused the required strip-types option;
  reran explicitly with Node22.18.0:97 frontend tests pass and final TypeScript/Vite
  build passes (`.../goal-selection-final-frontend-tests.txt`,
  `.../goal-selection-node22-build.txt`), JS index-6LBcfAe8.js/CSS index-Bi_eIbTY.css.
  Selected design-pair verifier/diff whitespace checks pass, not full accessibility.
- Final installed wheel SHA256
  `429a02164a47206fd66bcd95e1808bdaa6aa06d7c766e62af91944c6836bb80d`, all73 service
  files byte-match (`.../goal-selection-final-wheel-proof.json`). Real installed
  runtime/maintenance with final UI passes target_requests0 (`.../goal-selection-final-installed-runtime.txt`).
  Recovery harness initially assumed all task checks produce rows and failed on the
  valid subset; now checks exact declared selected pairs. Its write/audit fixture
  explicitly requests all goal tools, preserving its six-cell precommit crash gate.
  Final installed both-backend process/database/write/audit crash modes pass
  (`.../goal-selection-final-installed-recovery.txt`): SQLite5owned GETs/audit43→92;
  native7GETs/audit43→112 plus two write/audit stages2GETs each/audit28→48. No external
  or preapproval restore traffic; no hardware/PITR/commit-acknowledgement-loss claim.
  Temporary installations removed; retained preview restarted only after exact idle
  counts/states and owned PID/CWD verification, serves final UI and remains healthy
  with identical counts/task states (`.../goal-selection-preview-before.json`,
  `.../goal-selection-preview.txt`, `.../goal-selection-cleanup-proof.json`).
- First full suite:1052pass/1failure after532.59s. The final null-plan guard was edited
  after test-process startup; deterministic package-contract test correctly detected
  cached startup digest versus changed files. No test was weakened. Fresh frozen
  contract tests17pass (`.../goal-selection-frozen-contract-tests.txt`); final service
  code stayed frozen: full rerun1055pass in535.93s
  (`.../goal-selection-frozen-full-tests.txt`). Four later-added scope/replay cases
  pass in the final24-case suite; full1055 plus those four covers all1059 current
  collected cases (`.../goal-selection-collected-tests.txt`). Fresh source hash and
  retained preview health/counts/task states reconfirmed in cleanup proof.
  Full v1, whole mobile/SR, mixed-version operation and semantic goal quality remain open.

## Objective-bound observation response plans — 2026-10-05

- Frozen backend regression run with native PostgreSQL enabled: **1,083 passed,
  2 setup errors** in 578.31s. Both errors were `StaticFiles` finding no
  `web/dist/assets` during a concurrent frontend rebuild; application assertions
  did not run for those two cases. After the build completed, the exact two
  cases passed in **1.61s**. Combined evidence covers all **1,085 collected
  tests** on unchanged backend source; this is not a single clean full-suite run.
  Future reviews must finish frontend builds before tests that mount their assets.
- SQLite and native PostgreSQL: **26 passed** for objective asset/check filtering,
  separate approval, actual owned `/api/account` GET, independent URL result and
  unchanged base coverage/goal progress, exact request replay, changed objective/
  scope refusal, retry/replan origin preservation, damaged/removed origin refusal,
  viewer permissions and final-transaction rollback. A rejected HTTP mutation
  retains its single user-request audit event; plan/coverage/source changes roll back.
- Before reproduction from `be94d9a`: the same owned source scenario fails at the
  new objective observation preview with **404**; no import/collection failure.
- Frontend: **97 passed**, TypeScript/Vite build successful. Actual built console
  with explicitly synthetic seeded observations: only the objective's declared
  response check appears, selection creates a pending plan, origin and selected URL
  display, and the original-goal button returns to the source. Fixture shutdown
  confirms **0 target traffic records**, **0 provider calls**; no fixture approval.
  This is desktop evidence, not real mobile or screen-reader coverage.
- Wheel `9581dd0c102fd4743f7393799b2487001bcc1508b962444a6e07edd95f0b3127`: all
  **74 Python files** match current source. Installed runtime outside checkout
  passes locked dependencies, eight CLI entry points, HTTP/UI/auth/persistence,
  maintenance/release rehearsals and clean shutdown with **0 target requests**.
- Owned preview restarted with unchanged 4 tasks, 23 coverage records and 3 traffic
  records; loopback health reports `ok`. Disposable browser fixture and tab removed.
- Automatic interpretation, goal-origin inheritance for generic finding retests,
  automatic observation follow-up/shared todos, full mobile/SR, production and
  public-release gates remain open. This does not establish complete v1 readiness.

Local ignored evidence: `artifacts/goal-observation-*`; source tests are
`tests/test_goal_observations.py` and `tests/test_postgres_goal_observations.py`.

## Observed finding retests retain goal objective origin — 2026-10-05

- Frozen source/assets full regression with native PostgreSQL enabled:
  **1,103 passed** in **612.46s**, no setup errors or failed assertions. The
  sole warning is the existing Starlette/httpx test-client deprecation.
- Before reproduction from `c28e5d7`: an owned goal observation finding's general
  retest becomes pending but has no `goal_observation` reference. The focused
  regression fails on that missing reference, not on imports or collection.
- Targeted SQLite/native PostgreSQL regression: **66 passed** across existing
  observation execution, objective selection and the new retest tests. Tests seed
  a provenance-bearing `/login` observation in the owned fixture, then make real
  loopback GETs; hardened 2xx responses resolve the finding while retaining source
  evidence and independent base goal progress. Original `/api/account` hardened
  responses return403 and existing tests preserve the inconclusive conclusion.
- Latest proof's approved execution contract, task/finding/check/asset identity,
  observation ID and requested URL must match before inheriting the objective.
  Changed objective, proof URL/task, numeric approval, removed origin and damaged
  active replay are rejected without target requests. Final-write proof mutation
  rolls back task/coverage/proof changes on both backends. Replacement keeps
  origin, replay returns the same active retest, and completion stores origin in
  the retest result. A newer ordinary observation proof does not inherit a guessed
  historical objective.
- Wheel `9c92c7326655ead3df90cb16744aadf21ebc2e768c5f3d95c949c934e6ef4896`: all
  **74 Python files** match frozen source. Separate installed runtime rehearsal
  passes with 0 target requests; **9 focused retest tests pass in 16.81s** from an
  isolated installation outside checkout. Fixtures/tests are copied separately;
  `aegis` is imported from the installation's site-packages. The temporary
  environment is removed at completion.
- No frontend source change this round; the existing task detail already displays
  `goal_observation` origin and the original-task navigation. This round does not
  establish a new mobile/SR or complete browser journey result. Automatic
  observation interpretation/follow-up/shared todos and all other open v1 gates
  remain incomplete.

Local evidence: `artifacts/goal-observation-retest-before.txt`,
`goal-observation-retests-expanded.txt`, `goal-observation-retests-installed-*`,
`goal-observation-retests-package-proof.json`. Source/native tests:
`tests/test_goal_observation_retests.py`, `tests/test_postgres_goal_observation_retests.py`.

## Selective observed URL response follow-up rounds — 2026-10-05

- Final frozen-source/asset full regression with native PostgreSQL enabled:
  **1,125 passed** in **664.39s**, no failed assertions or setup errors. Only
  the existing Starlette/httpx test-client deprecation warning remains.
- Before reproduction from `4e9c7da`: the same owned two-URL/two-check partial
  failure returns409 at observed follow-up preview; the focused test fails on
  that API response, not imports/collection.
- Targeted run: **35 passed** for initial selection/compatibility, then **100
  passed** across SQLite/native PostgreSQL follow-up, objective retest and
  existing base planning scenarios. An owned failed `/login` header cell creates
  a pending child with one URL/check pair; explicit approval produces one real
  `/login` GET and one target result. Completed `/api/account` and cookie pairs
  remain reusable in the next proposal; base coverage/goal progress are unchanged.
- New selected-cell contracts are pinned by approval, reject removal/duplication/
  out-of-scope IDs/parent mismatch, and survive replacement/retry. The durable
  event planner prepares the same fresh proposal without target requests or
  creating a task. Shared todos can repeat existing selected checks; new tools
  require a fresh observation selection. Acceptance rechecks coverage/todos/
  scope/context in its final transaction and rolls back source/child/coverage
  together on injected change.
- Actual loopback execution repeats a persistent selected failure for eight
  separately approved rounds, then refuses a ninth. A separate two-real-attempt
  test lowers only the module's history cap to 2 to exercise the history boundary
  and distinct reason; the production history cap remains 32.
- First broad run: **1,122 passed, 1 failed** in 660.93s. The existing retest race
  injector mutated every connected prepare call, including the newly supported
  background observation planner. An instrumented experiment confirms injection
  in `aegis-event-planner` as well as the HTTP worker. It now captures the HTTP
  retest's reviewed request ID and injects exactly once only in that request's
  final write; **both backend retests passed** with proof rollback and no GETs.
  The production event consumer remains running during this test.
- Desktop built-app fixture explicitly seeds a synthetic failed observed result:
  selection and corrected execution wording display in the proposal; acceptance
  opens a pending child with the selected URL/check, original objective and
  original-task navigation. DOM/PNG reviewed; fixture and browser tab removed.
  Shutdown confirms **0 target traffic records**, **0 provider calls**, and an
  unapproved pending child. This is not mobile/SR or real target execution proof.
- Final frontend: **97 passed**, TypeScript/Vite build successful,
  `index-X1SP_7_K.js`. The later eligibility correction preserves the original
  general finding-retest next-plan UI and excludes only observed finding retests.
  UI iteration used a separate output directory while the
  Python suite mounted unchanged `web/dist/assets`. The fresh full-suite run
  used the corrected selection wording; final normal build/97 frontend tests
  completed after it for the general-retest eligibility correction. Python
  source and final wheel remained unchanged.
- Frozen wheel `f17ccb20308bba2216dabdbd8b89f1af6447a1e56dc9ccfb871d6490cd64df1c`: all
  **75 Python files** match current source. Installed runtime outside checkout
  passes HTTP/UI/auth/persistence/maintenance/release rehearsals with 0 target
  requests. **11 focused feature tests pass in 26.19s** from the installed package
  outside checkout, including selected real GETs, eight actual rounds and the
  separate history-boundary reason. Temporary installation removed at completion.
  Remaining v1 criteria retain their unchecked status.

Evidence lives in ignored `artifacts/observation-rounds-*`; source tests are
`tests/test_observation_rounds.py` and `tests/test_postgres_observation_rounds.py`.

## Automatic shared notes for observed response failures — 2026-10-05

- Final frozen-source full regression with native PostgreSQL enabled:
  **1,143 passed in 695.09s**. No failed assertions or setup errors; only the
  existing Starlette/httpx test-client deprecation warning remains.
- Owned baseline reproduction from `073ab55` fails the new automatic-note test
  because the completed failed observation has **0 notes**, rather than failing
  import or collection. The temporary baseline checkout is removed.
- Focused SQLite/native PostgreSQL checks: **18 passed in 32.01s**. Repeat events
  create one note without tool requests or target traffic. Human edits and
  open/done/cancelled decisions remain unchanged. New failed combinations create
  distinct notes; an injected cursor-write crash rolls back notes, history,
  review, cursor and audit together, and replay succeeds once.
- Limits leave existing records intact and expose `limited`; a proposal reviewed
  before note creation becomes stale. Damaged origin blocks preparation without
  overwriting the note. A saved legacy policy fingerprint replays old failure
  events after upgrade without target requests. Native CI includes the new cases;
  this does not establish a hosted CI result.
- Built-app desktop fixture seeds an explicitly synthetic failed observation.
  The real event consumer creates its note, displays the automatic-origin notice
  and **no requested checks**. An unapproved follow-up shares the note and its
  source button returns to the original failed task. DOM/PNG inspected; tab and
  temporary server removed. Shutdown records **0 provider calls, 0 target traffic**
  and the pending child remains unapproved. Mobile/SR remains unverified.
- Frontend **97 passed**; TypeScript/Vite build succeeds with `index-DVOFWd77.js`.
  Frozen wheel SHA256 `1b6b250fd05015199be8730a90fcabd7c61e1bc521a75881de8028c8095f1c7d`
  matches all **76 Python files**. Installed runtime outside checkout passes
  authentication/UI/persistence/maintenance/release rehearsals with 0 target
  requests. **9 installed feature tests pass in 15.65s** from an isolated
  site-packages installation; temporary installation removed.
- Main loopback preview is refreshed after confirming no active tasks. Existing
  record counts and all four task states remain unchanged; health returns200.
  Automatic notes do not imply vulnerability, successful validation or goal
  achievement. Semantic interpretation and the remaining v1 gates remain open.

Local evidence: `artifacts/observation-todos-*`; source tests:
`tests/test_observation_todos.py`, `tests/test_postgres_observation_todos.py`.

## Execution/read churn exposes and repairs event-planner lag — 2026-10-05

- Final frozen-source full regression with native PostgreSQL enabled:
  **1,151 passed in720.32s**. No failed assertions/setup errors; only the existing
  Starlette/httpx test-client deprecation warning remains.
- New owned HTTP rehearsal performs real approved header/cookie/link checks,
  human acceptance, real503 inconclusive retests and hardened-response resolved
  retests while two clients read bounded lists, overview/runtime and full reports.
  It then admits six concurrent jobs, SIGKILLs two running/two queued jobs,
  restarts, verifies four interrupted plus one never-approved pending job and
  no automatic target requests, and explicitly approves a fresh retry.
- Before repair, **both SQLite and native PostgreSQL 300s runs fail** at
  `planner_catchup`: the restarted retry's automatic proposal does not become
  ready within10s. An owned SQLite live snapshot has event8051 vs position3524.
  Each event independently prepared a current-state proposal and incurred the
  watch delay. This is actual workload/recovery evidence, not a reduced timeout.
- The consumer now atomically processes a prefix of at most25 events, prepares
  each task once at its last trigger, and orders those last triggers by sequence.
  It stops before an asset event and completes that event's25-task pages before
  proceeding. Original audit events remain intact; approvals are unchanged.
- **8 focused SQLite/native tests pass in7.21s** for latest triggers, all-review/
  cursor/audit rollback, asset boundaries with restart, and the bounded durable
  prefix. Corrected baseline checkout fails explicitly because its independent
  affected task has no prepared review. The temporary checkout is removed.
  The first new-test fixture copied the pending response returned by an existing
  helper; it now reads that helper's actual completed record before cloning.
- Final300s runs both pass with the corrected consumer and identical Python
  source fingerprint `fd771d3f7a88a88cf3a6d75846decdbd1632bd7bb7a9b008aa0d25bf584042df`.
  SQLite: **474 cycles,1,422 churn tasks,1,430 target GETs,2,129 read responses**;
  PostgreSQL: **232 cycles,696 churn tasks,704 target GETs,2,809 read responses**.
  Each run additionally completes six burst tasks and one fresh recovery retry;
  target totals include burst and the held interrupted request. Expected503
  failed retests remain recorded, rather than being counted as successful checks.
- Both recover **2 running+2 queued→4 interrupted**, preserve the unapproved
  control, issue **0 automatic target requests**, finish the separately approved
  retry and verify the complete audit chain (SQLite18,601 events; PG9,163).
  Queue/event watchdog errors0, clean lifespan markers and real lease reacquisition
  pass; disposable services/targets/PG cluster/data are removed.
- Sample peak server RSS: SQLite87,936KiB (baseline61,888/end73,024), nativePG
  70,688KiB (baseline68,960/end68,864). Last2,000-query p50/p95: SQLite0.0144/1.8572s,
  PG0.0336/1.2125s. These runs overlap each other and the full regression on the
  same Mac arm64 host. They are scenario observations, not comparable production
  throughput/SLO certification. PostgreSQL/parent memory and disk retention are
  not measured; long-duration/production/mobile gates remain open.
- Frozen wheel `b8fc562e9c38d01016780fe1ff036ac7c5a69b763a8e249709ccca1410b88a66`
  matches all **76 Python files**. Installed runtime outside checkout passes
  HTTP/UI/auth/persistence/maintenance/release rehearsals with0 target requests;
  **4 installed feature tests pass in3.83s**; the temporary installation is removed.
  Frontend source/build is unchanged this round. Main loopback preview refresh
  preserves all existing counts/states and health200. CI adds short execution
  rehearsals and native batch tests; hosted execution remains unverified.

Evidence: ignored `artifacts/execution-load-*`, `artifacts/event-batches-*`;
source: `scripts/review_execution_load.py`, `tests/test_event_planner_batches.py`,
`tests/test_postgres_event_planner_batches.py`.

## Durable event progress visible in runtime and settings — 2026-10-05

- Final frozen-source full regression with native PostgreSQL enabled:
  **1,165 passed in721.16s**. No failed assertions/setup errors; only the existing
  Starlette/httpx test-client deprecation warning remains.
- Baseline `d65ffd7` real authenticated HTTP runtime responds200 but contains no
  durable progress fields. The owned reproduction fails that explicit assertion;
  the temporary checkout is removed.
- **14 SQLite/native PostgreSQL cases pass in11.02s**: SQL aggregation counts one
  pending row across a1,000-sequence gap, never loads event payloads or changes
  cursor/audit/target traffic, reports full replay without rewriting the stored
  cursor, and refuses to call corrupt format/boolean/ahead/fanout state zero work.
  A pending asset page stays visible until its final commit. The initial run
  caught an incorrect timestamp column name; both aggregates use actual `ts`.
- Settings displays process survival/errors plus durable position/latest sequence,
  actual pending rows and oldest wall-clock age. Pending0 displays no oldest
  event; corrupt position displays unknown. Policy replay counts from0 and is
  explicitly labeled. Old runtime responses without progress remain displayable.
- Three disposable built-app desktop fixtures show **38 pending events**,
  policy replay0/38 with38 rows, and corrupt position/remaining/age **unknown**.
  DOM/PNG inspected; tabs and services closed. Each fixture reports **0 tasks,
  0 target traffic** at shutdown. Provider configuration is removed. These are
  synthetic stopped-consumer scenarios, not mobile/SR or real backlog generation.
- New metrics with owned20s execution/read/recovery: SQLite**43 cycles/129 churn
  jobs/137 target GETs**, nativePG**18 cycles/54 churn jobs/62 target GETs**. Both
  pass burst approvals,2-running+2-queued process loss,4 interrupted recovery,
  unapproved preservation,0 automatic requests, fresh approved retry, audit and
  clean shutdown/lease reacquisition. Temporary resources removed.
- Frontend**97 passed**; final TypeScript/Vite build `index-DIKJ8B-c.js` succeeds.
  Wheel `5e8facc858a2b7e3868b47c96c07d0a72e7788b93d8cea49903307a08064c825`
  matches all**76 Python files**. Installed runtime outside checkout passes
  HTTP/UI/auth/persistence/maintenance/release rehearsals with0 target requests.
  **7 installed feature tests pass in5.26s**, temporary installation removed.
  Native CI includes the new cases; hosted execution remains unverified.
- Main loopback preview is refreshed after confirming no active jobs. Health200
  and all original record counts/four task states are preserved.
- Age uses recorded wall-clock time, clamps negative age to0, and is not a
  monotonic processing deadline or production SLO. Counts are events, not jobs
  or approvals. Storage consistency/SLO/long production/mobile gates remain open.

Evidence: ignored `artifacts/event-progress-*`; source tests:
`tests/test_event_planner_metrics.py`, `tests/test_postgres_event_planner_metrics.py`.

## Fifteen-minute execution/read churn with backlog and disk observations — 2026-10-05

The current unchanged `3947acd` backend passes two concurrent900s owned rehearsals
on the same Mac arm64 host. Rehearsal instrumentation adds bounded event-progress
samples, whole-run observed peak backlog/age, approximate baseline/end storage
file sizes and atomic30s progress receipts. Progress files are never pass evidence.
No service Python/frontend source changed this round; the previous1,165-test full
result applies to identical service source, not a newly executed broad test run.

| Observation | SQLite | Native PostgreSQL |
|---|---:|---:|
| Repeating execution duration | 901.692s | 901.999s |
| Completed cycles | 787 | 437 |
| Explicitly approved churn jobs | 2,361 | 1,311 |
| Target GETs including burst/recovery | 2,369 | 1,319 |
| Successful read responses | 2,874 | 3,879 |
| Largest observed pending event count | 40 | 18 |
| Largest observed oldest event age | 0.240s | 0.299s |
| Pending events after churn drains | 0 | 0 |
| Sample peak server RSS | 74,064KiB | 70,992KiB |
| Last2,000-read p50 / p95 | 0.0279 / 5.2217s | 0.0652 / 5.0552s |
| Baseline / after-churn file bytes | 77,824 / 36,163,584 | 40,946,045 / 114,852,741 |
| Complete audit chain verified | 30,808 events | 17,158 events |

Each run also completes six burst jobs and a fresh approved retry. Two running
and two queued jobs become four interrupted after SIGKILL; an unapproved control
stays pending. Recovery issues0 automatic requests, preserves session access,
finishes the newly approved retry and passes audit/clean shutdown/real lease
reacquisition. Both report temporary resources removed and exit0.

RSS medians by resource-sample quarters are68,880/71,744/50,128/53,720KiB for
SQLite and62,632/62,680/40,064/42,888KiB for nativePG. The summary helper verifies
completed successful/cleaned receipts, includes every resource sample once and
rejects unfinished/failed receipts. Optional same-run progress logs retain
increasing observation times/cumulative read counts. Observed read counts over
those progress windows are1,942/505/213/210 and2,434/789/304/310 respectively;
the last observed window ends at898.714s/873.536s and excludes the final4/42 reads.
Window endpoints follow30s receipts, not exact equal-duration boundaries.

Read completion frequency decreases with the accumulating scenario, and mixed
read p95 is about5s. No endpoint-specific latency attribution, query-plan
diagnosis or steady-state production throughput conclusion is established.
Responsiveness under retained data needs further measurement/optimization.
RSS observations do not diagnose memory leaks or prove a memory SLO. PostgreSQL
file sizes include its initial cluster, catalog and WAL; both file walks are
approximate and not retention/backup size guarantees. Parent/DB memory remains
outside the service RSS sample. Multi-hour/day production, retention/SLO and all
other unchecked v1 requirements remain open.

Evidence: ignored `artifacts/execution-soak-*-900s.{json,txt}`, progress and
`execution-soak-*-summary.json`; smoke instrumentation receipts are
`artifacts/soak-metrics-*`. Scripts: `review_execution_load.py` and
`summarize_execution_load.py`. Both long receipts match the service source at that
measurement (`3947acd`); later report batching is not included in those receipts.

### Report delivery batching — targeted and installed verification, 2026-10-05

The report async iterator now bounds each worker call by128 source chunks and
64KiB accumulated source bytes, retaining an oversized record intact. Content,
snapshot ownership and per-source-chunk permit checks retain their contracts.
See [execution/load evidence](EXECUTION-LOAD.md#조회-지연의-구간-구분-검수--2026-10-05)
for the diagnostic and actual HTTP measurements; these are not production SLOs.

Report/export-limit/nativePostgreSQL targeted tests:31 passed in14.57s. Added
coverage checks all three formats with large Unicode values, exact exported
bytes and incremental delivery across a subsequent evidence write within the
original read snapshot. Existing SQL/send deadline, disconnect and cleanup
checks also pass. No frontend source or bundle changed.

The rebuilt wheel contains all76 service Python files byte-for-byte. SHA-256:
`fb00e8e5f4dd9549a9a52e190b9b935c9e9e733d6aabeb5c594109537558618f`.
Installed-runtime HTTP/UI/authentication/persistence/maintenance/release checks
pass outside checkout with0 target requests. An independent installation with
locked development dependencies and copied fixtures imports `aegis` from its
own site-packages and runs both SQLite report/export-limit test files:22 passed
in4.63s. The temporary installation was removed.

Evidence: ignored `artifacts/report-batching-targeted-tests.txt`,
`report-batching-frozen-wheel/`, `report-batching-installed-runtime.txt` and
`report-batching-installed-feature-tests.txt`. The latter reproduction is
`artifacts/review_installed_report_batching.py`. The frozen full regression,
including nativePostgreSQL, passed1169 tests in822.86s; its process exited0
(`report-batching-frozen-full-tests.txt`). The only reported warning is the
existing FastAPI/Starlette TestClient httpx deprecation. Service source remained
unchanged during this run and the concurrent long rehearsals.

The owned idle preview was gracefully stopped (143), restarted with the current
service source and existing frontend bundle at127.0.0.1:8790, and returned
HTTP200 health. Read-only snapshots of exactly `preview-data/aegis.db` before
and after matched record counts and all four task statuses:one pending, two
completed, one failed. No task approval or target execution was performed.
Post-change900s execution rehearsals both exited0 with temporary resources
removed and source fingerprints matching the then-frozen service (`7004786`). SQLite
completed723 cycles/2169 approved churn tasks; nativePostgreSQL461/1383. Both
verified process-loss recovery, no automatic target request, fresh approval,
audit chain, clean shutdown and actual lease reacquisition. Detailed timing,
resource observations, counts and limits are in
[execution/load evidence](EXECUTION-LOAD.md#묶음-전달-적용-후15분-누적-실행--2026-10-05).
Evidence: `artifacts/execution-batched-*-900s.{json,txt}` and summary JSONs.
This does not complete production SLO/retention/multi-day operation or v1.

### Coverage task-field projection — targeted and installed checks, 2026-10-05

The dashboard summary and asset pages now project the task fields needed by
coverage before expanding scope/check combinations, rank eligible attempts,
and look up coverage only for the latest attempt. SQLite preserves JSON path
scalar semantics through JSON encoding, with a no-hint branch below3.35.
NativePostgreSQL decodes each task once through `jsonb_to_record`, and casts
timestamps only for eligible cells. No HTTP response shape or frontend changed.

The retained-history diagnostic and controlled measurements are in
[execution/load evidence](EXECUTION-LOAD.md#대시보드-커버리지-조회-구간-진단--2026-10-05).
Source coverage/nativeStore/contract subset:33 passed in8.31s. The new contract
fixtures verify approval ordering and insertion ties, stale revision, wrong
coverage source, unapproved/observation exclusions, goal objective and selected
cell intersection, legacy timestamp fallback and unrelated archived history.
The SQLite scalar-path projection regression was reproduced (3 failed/1 passed)
and corrected before freezing the service source. The omitted-hint branch was
run on the current SQLite engine, not an actual older SQLite installation.

The wheel has all76 Python service files byte-for-byte matching the frozen
source. SHA-256:
`590389468b760c5d0196bb4bdd1483e5b9ded8172b3ea38e3450944aa69ee10e`.
Installed-runtime HTTP/UI/authentication/persistence/maintenance/release checks
pass outside checkout with0 target requests. An independent temporary
installation with locked development and PostgreSQL dependencies imports
`aegis` from its own site-packages and runs the coverage and contract files:
22 passed in10.04s, including actual disposable nativePostgreSQL. Temporary
installation/cluster resources were removed.

Evidence: ignored `artifacts/overview-projection-final-targeted-tests.txt`,
`overview-projection-frozen-wheel/`, `overview-projection-installed-runtime.txt`,
`overview-projection-installed-feature-tests.txt`; the isolated reproduction is
`artifacts/review_installed_overview_projection.py`. The frozen full regression,
including actual nativePostgreSQL, passed1180 tests in767.68s with exit0. Its
only warning is the existing TestClient httpx deprecation
(`overview-projection-frozen-full-tests.txt`). Service source stayed unchanged
during the full run and both long rehearsals; frontend source/bundle stayed
unchanged throughout this change.

Both900s execution rehearsals exited0 with matching frozen/current service
fingerprints and temporary resources removed. SQLite completed772 cycles/2316
approved churn tasks, nativePostgreSQL506/1518. Both verified burst approval,
four interrupted jobs after SIGKILL, retained pending control,0 automatic target
requests, fresh approved retry, audit integrity, clean shutdown and real lease
reacquisition. Actual overview p95 is342/235ms in the last2000 samples per
endpoint. The independent retained synthetic history and actual HTTP runs have
different observation scopes; no production SLO or exact HTTP improvement ratio
is inferred. Detailed measurements and limitations are in
[execution/load evidence](EXECUTION-LOAD.md#커버리지-투영-적용-후15분-실제-실행--2026-10-05).
Receipts: `artifacts/execution-overview-*-900s.{json,txt}` and summary JSONs.

The owned idle preview was gracefully stopped (143), restarted with current
service source at127.0.0.1:8790 and returned HTTP200 health. Read-only snapshots
of exactly `preview-data/aegis.db` matched record counts and all four task states
(one pending, two completed, one failed), with no task approval/target execution.
This does not complete remaining v1 UI, retention/SLO, extension, deployment and
other unchecked gates.

### Remote MCP client foundation — 2026-10-05

Added a separate Streamable HTTP client library, without wiring external calls
into the HTTP app, Planner or Worker. Owned loopback JSON/SSE and HTTPS fixtures
verify initialization/version/session negotiation, pagination, exact-input
one-use grants, fresh metadata review, credential rotation, list-change
revocation, no call replay, safe RPC errors, response/argument budgets, schema
reference restrictions, admission/network deadlines and caller input mutation.
Trusted certificates complete a real tool call; untrusted and wrong-host TLS
fixtures receive no HTTP requests or credentials. The result error flag is
preserved rather than interpreted as successful validation.

The initial remote/runtime/local-MCP subset passed68 tests in31.09s. After
adding schema-expansion and SSE framing cases, the final remote subset passed44
tests in20.30s. A separate installed-wheel environment outside checkout imports
its own site-packages and passes the same44 tests in20.27s; temporary fixtures
and installation resources were removed. The installed runtime HTTP/UI/auth,
persistence, maintenance and release rehearsal also passes with0 target requests.

Frozen wheel `open_aegis-0.2.0a1-py3-none-any.whl` SHA256 is
`f00d9629ed396e4ac28374129befdb047579d956afba4fb542f8d237177e98df`;
all77 service Python files byte-match the working source. Receipts are ignored
`artifacts/remote-mcp-{targeted-tests,installed-feature-tests,installed-runtime}.txt`,
`remote-mcp-frozen-source.json`, and `remote-mcp-frozen-wheel/`. The independent
installation reproduction is `artifacts/review_installed_remote_mcp.py`.
The frozen full regression, including actual disposable nativePostgreSQL,
passed1224 tests in739.22s with exit0. Its only warning is the existing
TestClient httpx deprecation (`remote-mcp-frozen-full-tests.txt`). All77 service
Python files stayed unchanged throughout the full run and byte-match the wheel.
The frontend source and built bundle were unchanged; no new execution-load or
UI-flow claims are inferred from this standalone client change.

The owned idle preview restarted gracefully (old process exit143) and returns
HTTP200 at127.0.0.1:8790. Read-only snapshots of exactly `preview-data/aegis.db`
match all record counts and four task states before/after restart; no plan was
approved or target executed. Receipts are `remote-mcp-preview-{baseline,after}.json`.
Application registration, actor authorization/audit, isolated execution, remote
scope enforcement and interoperability gates remain open; see
[the supported contract and limitations](REMOTE-MCP.md).

### Administrator MCP metadata registration — 2026-10-05

Added configured connections and administrator-only HTTP/UI discovery, reviewed
metadata registration, paged summaries, individual saved definitions and
revision-checked disabling. Registration refreshes the remote catalog and
checks connection/credential/catalog fingerprints and the registration revision
observed at review creation. Actor ownership, response-loss replay and audit
failure rollback are verified on SQLite and actual disposable nativePostgreSQL.
A reused registration receipt does not re-enable a subsequently disabled tool.
No registration is added to Worker checks, tasks, findings or coverage.

Service discovery runs fixed client code in a supervised POSIX child with
minimal environment, bounded file output, CPU/FD limits and parent deadline.
Owned tests prove unrelated environment variables are not forwarded; hanging/stopped children
are killed and reaped, temporary work directories are removed, and trusted TLS
can register while untrusted/wrong-host fixtures receive no HTTP credentials.
Known credential reflection in metadata is rejected. Linux address-space
limits are implemented but their operating verification remains open; the
actual process tests here run on macOS and do not establish a hard RSS limit or
filesystem/egress sandbox. Server-side effects remain outside the client proof.

Final client/registry subset passed85 tests in51.12s. A separate installed wheel
environment outside checkout, with locked development/nativePostgreSQL
dependencies, passed the same85 tests in53.19s, including real supervised child
imports from installed site-packages. Temporary installation/cluster resources
were removed. Installed runtime HTTP/UI/authentication/persistence/maintenance
and release smoke checks also pass with0 target requests.

Frozen wheel SHA256 is
`8d5fd8f57f4bb470ef4e991db534bedef6c1763daae37fae9f3244d73a6e08af`;
all79 service Python files byte-match source. Receipts are ignored
`artifacts/mcp-registry-{final-targeted-tests,installed-feature-tests,installed-runtime}.txt`,
`mcp-registry-frozen-source.json`, and `mcp-registry-frozen-wheel/`. The installed
reproduction is `artifacts/review_installed_mcp_registry.py`.
The full frozen regression, including actual disposable nativePostgreSQL,
passed1265 tests in771.93s with exit0. The only warning is the existing
TestClient httpx deprecation (`mcp-registry-frozen-full-tests.txt`). All79
service Python files stayed unchanged and byte-match the wheel after the run.
No execution-load/SLO claims are inferred from this metadata registration change.

Frontend97 tests pass and the production build succeeds. Final assets are
`index-DZGlg3Xs.js` and `index-BhB7wk0w.css`. Actual Browser desktop checks cover
explicit connection selection, definition expansion and selection/confirmation
gating, registration/saved definition, changed catalog rejection/new review,
disabling, settings navigation/reentry and HTTP failure followed by explicit
recovery retry. Screenshot layout was inspected. Enter submission completed;
the next selector attempt found the removed registration control. This is not
a verified simultaneous browser double-submission race or a full mobile/screen
reader journey. The owned peer saw8 initialize,7 initialized notifications and
7 tools/list requests, with0 tools/call. Evidence is
`mcp-registry-browser-review.json`; the fixture reproduction is
`artifacts/review_mcp_registry_ui.py`. The first owned UI process exited143;
its exactly identified synthetic workspace was explicitly removed. A corrected
fixture cleanup rehearsal returned health200, exited0 after SIGTERM and
removed its owned workspace/servers (`mcp-registry-ui-cleanup-rehearsal.txt`).
After formatting, the final bundle filenames were verified directly and the
installed runtime smoke was repeated with those assets: valid,0 target requests
(`mcp-registry-final-installed-runtime.txt`).

The main idle preview restarted gracefully with the final service source at
127.0.0.1:8790 and returns health200. Read-only snapshots of exactly
`preview-data/aegis.db` match all record counts and four task states before/after;
no plan was approved or target executed (`mcp-registry-preview-{baseline,after}.json`).
Execution registration/authorization/audit, remote scope enforcement and
isolated Worker execution gates remain open.

## Signed scoped MCP execution foundation

The separate execution server implements the reviewed six-check GET adapter.
Owned HTTP fixtures prove actual SDK initialization/list/call, scoped target
GETs, strict whole-result admission, signature/server/package/expiry rejection,
path redirect refusal, private-target dual permission, credential allow-list and
known-secret reflection refusal. Signed rate/budget and deadline limits are
verified. Two actual isolated Python processes sharing a SQLite nonce ledger
produce exactly one target GET; server reconstruction and signing-key rotation
do not revive a consumed approved job. Supervised registry discovery preserves
the execution profile without any target requests. These use trusted fixture
approval snapshots, not the main app approval/Worker execution pipeline.

Final execution/client/registry tests passed117 in67.83s, including actual
native disposable PostgreSQL. The same117 passed in70.46s from a separately
installed wheel outside checkout; owned installation/cluster resources were
removed. The final full regression passed1297 in788.28s, exit0, with only the
existing TestClient httpx deprecation warning. Earlier interrupted/superseded
runs are not the final validation evidence.

Final wheel SHA256 is
`ae8927787890b663d67a5a32bb344c13e8c01bee6a708baa6fa1175388eccdc5`;
all83 service Python files byte-match the frozen source. Installed HTTP/UI,
authentication, pending-plan persistence, maintenance and signed-release smoke
pass with0 target requests. Final receipts are ignored
`artifacts/mcp-execution-final-{targeted-tests,full-tests,installed-feature-tests,installed-runtime}.txt`,
`mcp-execution-final-frozen-source.json`, `mcp-execution-final-wheel-receipt.json`
and `mcp-execution-final-wheel/`. Installed reproduction is
`artifacts/review_installed_mcp_execution_final.py`.

This phase does not establish generic plugin OS isolation, remote attestation,
main task approval/cancellation/audit/result persistence integration, global
limits across server instances, production compatibility or v1 completion.
See [MCP-EXECUTION.md](MCP-EXECUTION.md) for the actual authority and operating
boundaries. No frontend source changed; prior frontend/browser receipts remain
limited to their documented scope.

The existing idle preview restarted gracefully on127.0.0.1:8790 with health200.
Read-only snapshots of exactly `preview-data/aegis.db` preserve all record-kind
counts and four task states; no plan was approved or target executed. Receipts:
`mcp-execution-preview-{baseline,after}.json`. After the final full run and
preview restart, all83 service files still byte-match the final installed wheel.

## Atomic scoped MCP result admission foundation

An internal admission function now validates the complete remote result and
reconstructs the exact task-derived signed grant before any write. It freezes
the caller's task JSON and rechecks current running status, approval/scope/tool/
policy contracts, live asset revision/URL and coverage identity under one write
transaction. Findings, evidence/history, observed links, sanitized traffic,
completed/skipped coverage, one admission receipt and its audit event share that
connection. Known signing-key/grant/additional-secret reflection is refused.
An identical valid replay returns the original receipt; a changed response or
approval contract is refused. Receipts describe local validated admission, not
remote runtime attestation.

Owned real GET results verify success, observation and skipped admission on
SQLite and actual disposable native PostgreSQL. Injected failure after audit
append proves every result record and audit-chain state roll back, with retry
still possible. Concurrent identical admission creates only one receipt and
one evidence/traffic set. Changed current approval, scope, policy, stopping
status, asset revision, terminal coverage or mismatched stored coverage ID
produce no result writes. Caller mutation during validation cannot bind an old
result to a new approval. Existing finding/triage/observation helper paths remain
covered. The remote server's base response now follows the local Worker's 2xx
requirement; 401/404/429/500 cannot complete a check or revive the consumed grant.

The final related execution/client/registry/admission/core subset passed200 in
115.81s. A separately installed wheel outside checkout passed159 related tests
in103.02s, including actual PostgreSQL and supervised child imports. The owned
installation/cluster resources were removed. Installed HTTP/UI/authentication,
persistence, maintenance and signed-release smoke pass with0 target requests.
Final wheel SHA256 is
`e3bb9aa29968ee50eeb8b63405a3bb00c4a015a65e1601bf6d14439dcc2aa922`;
all84 service Python files byte-match frozen source. The only subset warning is
the existing TestClient httpx deprecation.

Receipts are ignored `artifacts/mcp-admission-v3-{targeted-tests,installed-tests,installed-runtime}.txt`,
`mcp-admission-v3-frozen-source.json`, `mcp-admission-v3-wheel-receipt.json` and
`mcp-admission-v3-wheel/`. Installed reproduction is
`artifacts/review_installed_mcp_admission_v3.py`. Superseded/interrupted earlier
runs are not final validation evidence. No frontend source changed.

The idle preview restarted gracefully with health200 at127.0.0.1:8790.
Read-only snapshots of exactly `preview-data/aegis.db` preserve all record-kind
counts and the four task states (`mcp-admission-preview-{baseline,after}.json`).
No plan was approved or existing target executed. This internal function is
not yet wired to API/Worker execution, so main remote execution, administrative
execution-contract review, cancellation/isolation and v1 deployment gates
remain open.

The final frozen full regression, including actual disposable nativePostgreSQL,
passed1339 tests in821.52s, exit0, with only the existing TestClient httpx
deprecation warning (`mcp-admission-v3-full-tests.txt`). All84 service files
remained unchanged and byte-match the installed wheel after the run and preview
restart. CI now includes native MCP registry/admission tests and allows25 minutes
for verification/storage jobs; the workflow YAML parses locally. Hosted CI,
Linux/amd64 production proof and main Worker integration remain unverified.


## Main approved MCP Worker integration — 2026-10-06

Configured fixed GET adapters now connect administrator tool review, explicit task
server selection, pending scope/policy/server snapshots, administrator approval,
supervised RPC and atomic result admission. The server's six current-code tool
definitions must match exactly; arbitrary registered tools remain ineligible.
Approval state and audit are committed together. Worker dispatch rechecks full
approval authority and current asset authorization/revision/URL before RPC.
An asset's request budget is shared between checks. Each dispatch has a persistent
attempt; unknown responses and startup recovery do not automatically replay it.
Replans, finding retests and follow-up plans preserve the server and require new
approval. Observed-response remote jobs are explicitly refused.

Actual disposable desktop browser review registered two definitions, selected the
remote server, preserved manual check choices across local/remote switching, and
showed scope/server/limits in approval. Target requests were zero before approval.
After approval, two GET checks completed with two admitted receipts, three
findings and one scoped link observation; the link was not visited. The source
fixture and temporary directory were removed. This is not full mobile, screen
reader or simultaneous submission QA.

The built console passes97 frontend tests and the selected design contrast check.
An isolated installation outside the checkout passes203 MCP-related tests with
SQLite and actual PostgreSQL16, including task approval, shared budget, stale
keys/tools, approval-audit rollback, dispatch-time authority change, stop without
admission/next check, startup recovery and retest/replan location preservation.
The initially failing recovery test incorrectly reused a closed PostgreSQL lease;
using a fresh Store/Engine reproduces restart and passes both backends.
Installed runtime/UI/authentication/persistence/maintenance/release smoke review
is valid and makes no target requests. The wheel contains exactly85 frozen Python
service files, byte-matching source; SHA256:
`49fa76c9b3459bd8b8c083daa93e681aa7aa6c4d07836ec2669638e05ec8cabc`.
Evidence: `artifacts/mcp-worker-installed-tests.txt`,
`artifacts/mcp-worker-installed-runtime.txt`,
`artifacts/mcp-worker-final-wheel-receipt.json`, and the owned UI state receipt.

Gitleaks8.30.1, downloaded from its official release with matching archive
checksum, scanned145 prior commits/~3.66MB. One generic-key candidate was ordinary
prose in the earlier validation entry; its exact historical fingerprint is
reviewed in `.gitleaksignore`, and current wording is clarified. This scan does
not prove absence of every secret. Preview restart preserved all record counts
and four task states exactly; existing pending work was not approved.

The full frozen-source regression passes **1,383 tests in856.63s**, exit0,
including native PostgreSQL; only the existing TestClient httpx deprecation
warning remains (`artifacts/mcp-worker-final-full-tests.txt`). Source bytes were
rechecked against the wheel after completion. Hosted image/Compose checks pass;
general verify/native storage CI jobs remain pending at this point. Remote stop kills/reaps the local RPC client and prevents
result admission/later dispatch; it does not guarantee immediate cancellation of
already-running remote server requests. General plugin OS/egress isolation,
remote cancellation, observed-response adapters, production interoperability and
the complete v1 gate remain open.


### First hosted Linux image/Compose evidence

Private review repository `SoonGwan/open-aegis` now contains the source at
`0b341c57bf7d8e139fbe3e8914bc0aaa0e84a6f9`. The
[Verify run](https://github.com/SoonGwan/open-aegis/actions/runs/37340628617)
on Ubuntu24.04 passes both image modes and both actual Compose modes.
Authenticated setup/UI, nonroot/read-only deployment, loopback publication,
retained volume/cookie after restart/recreation, checkpoints, stopped-app restore,
old-session refusal and clean shutdown are verified. PostgreSQL Compose uses16.15,
preserves the source schema and removes owned resources. No target execution was
approved. All four receipts are valid; ordinary application bridge egress is not
blocked. Downloaded job logs and extracted receipts are retained under
`artifacts/mcp-worker-hosted-*`. This is private verification, not a public v1
release or a production/PITR/multiarchitecture claim. General verify/native
storage jobs were still running when this subsection was recorded.


The hosted general verify job subsequently passes897 tests with486 PostgreSQL
cases skipped as expected without that job's optional driver/native-test flag
(587.78s). Its owned SQLite churn, installed runtime/maintenance and installed
SIGKILL goal recovery receipts are valid. Churn completes45 approved synthetic
tasks; installed recovery preserves request identities and waits for fresh
approval after interruption. Actual native PostgreSQL runs in the separate job;
these skipped cases are not described as passed by the general job.
Evidence: `artifacts/mcp-worker-hosted-verify-receipt.json`.


### Hosted completion and public source candidate

All six jobs of the referenced Verify run completed successfully for executable
source commit `0b341c57bf7d8e139fbe3e8914bc0aaa0e84a6f9`. Native storage subsets
pass385/12/42/11 cases in their respective steps; the SQLite/native MCP
review/admission/Worker step passes105 cases. These counts overlap other runs and
are not added to the full-suite total. Native installed transfer, execution churn
and process/database/write/audit crash recovery return valid receipts. See
`artifacts/mcp-worker-hosted-postgres-receipt.json`. Documentation-only additions
after this run do not change the85 frozen service files or the built console.

The [source repository](https://github.com/SoonGwan/open-aegis) is now public with
MIT licensing and enabled private vulnerability reporting. The initial validation
ran privately before publication. The published version remains0.2.0a1; no v1
completion, production deployment, independent audit or star count is claimed.
Remote cancellation/observed-response/general plugin isolation and the other
unmet v1 criteria remain tracked rather than silently omitted.


### Signed remote cancellation and timeout reproduction

The fixed GET execution server now accepts the `aegis/cancel` extension, verifies
its existing signed grant, and stores revocation with consumption atomically.
Native source-stop integration passes for SQLite and PostgreSQL. Nine focused
cases cover pre-dispatch/idempotent cancellation, invalid/expired/wrong-server
refusal, separate-runner and actual separate-process interruption, previous
2-column ledger writes, supervised cancellation and capacity limits. A real
13-second owned response failed before the SDK fix because its RequestGuard
still used12 seconds despite trusted operation_timeout20; it succeeds after
applying that timeout to the socket and guard. No real external target was used.

The settled related suite passes **212 tests in155.83s**, exit0; the independent
installed wheel passes the same212 cases in161.16s outside the checkout,
including native PostgreSQL. The full frozen-source native regression passes
**1,392 tests in877.42s**, exit0, with the existing TestClient httpx deprecation
warning. Frontend97 tests and the production build pass. Selected design-token
contrast checks are separate from a full accessibility review.

Wheel `open_aegis-0.2.0a1-py3-none-any.whl` has SHA-256
`399555a017fafe5a859df43ff7ee18b26cb7a9f72a34b892ba60e83bd7a2b196`;
all85 service Python files match the frozen source byte for byte, rechecked after
the full suite. Installed authentication/UI, persistence, maintenance and signed
release rehearsal return a valid receipt with zero target requests.

In the built desktop UI, an owned API asset with20 explicit anonymous GET rules
was selected into a remote plan. The registry was seeded through the actual
review/register service; registration UI was not retested in this review. There
were zero target requests before approval. After approval, the task detail's
explicit Stop sent POST `/api/tasks/<id>/stop`, returned200, changed the task to
stopped and displayed both the stop event and remote cancellation confirmation.
The remote gate was released, eight already-started target GETs remained stable,
and no execution receipt or finding was admitted. Two earlier attempts ended
by their request timeouts before an explicit stop was established; those are
retained as timeout evidence, not successful stop-button evidence. Owned tabs,
servers and temporary data were removed after review.

Evidence is retained locally in `artifacts/mcp-cancellation-*-tests.txt`,
`artifacts/mcp-cancellation-rpc-timeout-before.txt`,
`artifacts/mcp-cancellation-installed-runtime.txt`, the wheel verification receipt
and `artifacts/mcp-cancel-ui-stop-receipt.json`. These files are ignored diagnostic
artifacts and are not published test certificates.

Revocation acknowledgement confirms the server's grant ledger, not the truth of
remote execution or undo of already-transmitted requests. The source records
unconfirmed original execution and never automatically replays it. Cancellation
is a fixed extension, not generic MCP cancellation. Connection loss, key/expiry
changes and main-process hard termination can prevent acknowledgement; a durable
crash-recovery cancellation outbox, observed-response adapter and general plugin
OS/egress isolation remain open v1 work. Hosted checks for this changed source
are pending until its next Verify run completes; previous hosted success applies
to the preceding executable commit.


### Hosted cancellation source and expanded ARTEX inventory

All six jobs of [Verify37347216353](https://github.com/SoonGwan/open-aegis/actions/runs/37347216353)
pass for executable source `bf0326d62f8fce6a3e49b0c0471d563ff19d6411`.
The general Linux suite passes906 tests with486 native PostgreSQL cases skipped
as expected in that job (603.28s); the separate native job passes385/12/42/11
cases in its respective subsets and114 in the MCP review/admission/Worker/
cancellation step (121.56s). These overlapping subsets are not added to the
local1,392-test total. Both actual image variants and both Compose variants pass,
including setup/UI, retained volumes, authenticated restart, backup/restore and
owned resource cleanup. Ordinary bridge egress remains unblocked. All ten
extracted rehearsal receipts across the six jobs are valid, including installed
runtime, execution churn and installed native process/database/write/audit
recovery. Logs and parsed receipts are retained as
`artifacts/mcp-cancellation-hosted-*`. No production/PITR/multiarchitecture or
remote-runtime attestation claim is made.

The local preview was restarted with the changed executable source. Direct
loopback health is200/version0.2.0a1; all existing record counts and four task
states are exactly preserved. No existing pending task was approved. Public
source audit with Gitleaks8.30.1 scanned373 current files and148 history commits;
zero unignored candidates remained. The single reviewed historical prose
fingerprint stays narrowly listed in `.gitleaksignore`; scans are not a guarantee
of secret absence.

The desktop Stop fixture's wrapper did not initially expose `app.state`, so its
SIGTERM handler exited1 even though finally/TemporaryDirectory cleanup removed
its resources. Its retained receipt records this limitation; it proves explicit
Stop and revocation, not graceful fixture shutdown. Clean installed/container/
Compose shutdown is established by the separate successful rehearsals above.

The newest ARTEX source snapshot
`b55ceb1fdd84a813d77de09a06af83d323a81f85` was fetched read-only and not executed.
[Its inventory](ARTEX-INVENTORY.md) includes261 unique HTTP registrations (243
literal main registrations plus18 reviewed helper expansions),27 page entry
points and49 named literal tool-constructor occurrences in agent/server source.
Each recorded literal source location and local documentation reference was
checked. These are static inventory counts, not verified runtime feature counts;
SDK/dynamic/MCP/skill tools are outside the constructor count. Newly identified
templates/categories/archives/notifications/model failover/prompt versioning are
tracked as incomplete. No upstream source, prompts or skills were copied into
the independently implemented service. The source remains0.2.0a1 and the full v1
gate is open.


## 2026-10-06 — selected observed-response remote batches

Adds a seventh fixed MCP tool, `validate_observation_responses`, without adding
a seventh check type. It requires separate administrator metadata review and
registration. Approved source observations, selection fingerprint, current asset
scope and planned check order bind a batch of up to10 URLs and40 explicit cells.
Only four response configuration checks are eligible. Each selected response is
reused; the base URL and unselected links are not fetched. Source remote location
survives partial next plans and original-URL finding retests.

The settled related suite passes218 cases with SQLite and actual PostgreSQL
(`artifacts/mcp-observation-settled-targeted.txt`,269.11s). The new60 cases cover
40-cell reuse, partial proof and failed-cell-only fresh approvals, retests, source
tampering, administrator registration/disable, budget exhaustion, signed scope
rejection, malformed remote results, audit rollback, replay/idempotent admission,
active Stop, planned order and source-restart unknown recovery. These counts
overlap the full suite and must not be added to it. Frontend97 tests and the
TypeScript/Vite build pass; selected design contrast pairs pass separately.

Actual built-UI browser QA selects two observed URLs and two checks, creates a
pending plan, verifies explicit remote batch wording and exact requested URLs,
approves and opens completed results with two targets per actual check. Owned
fixture state records no extra GET before approval, then exactly two child GETs
for four cells, six findings, one batch receipt and valid audit integrity. Registry
registration and the endpoint-inventory source were prepared through trusted
fixture APIs; their setup is not claimed as part of this browser journey. The
fixture exits0 and removes its temporary resources. Artifacts:
`mcp-observation-ui-before-approval.json`, `mcp-observation-ui-after-completion.json`,
`mcp-observation-ui-receipt.json` and `mcp-observation-ui-process.txt`.

An independently installed wheel outside the checkout passes272 related cases
with SQLite and actual PostgreSQL in295.31s. Its package origin is checked to be
inside the temporary installation, and temporary resources are removed
(`mcp-observation-installed-tests.txt`).

The wheel SHA-256 is
`25ade32973d44e0b022c3ec0bc7eb8668df454bff9886e2788651340ff8964c9`.
All86 service Python files match the frozen source byte-for-byte. Installed
locked-runtime review outside the checkout passes startup/health, authentication,
retained pending data, maintenance, backup/restore, release tamper/rollback and
clean shutdown with zero target requests (`mcp-observation-installed-runtime.txt`).
The main loopback preview health is200/0.2.0a1; its existing counts and four task
states match before/after restart exactly. Public source Gitleaks8.30.1 scans377
files with zero unignored candidates; this is not a guarantee of secret absence.

General plugin OS/egress isolation, durable remote cancellation after source
process loss, remote runtime attestation and remaining full operational criteria
are still open. This batch integration does not establish a v1 release.

The full frozen native-backend suite passes **1,452 tests in1,012.25s** with
actual PostgreSQL enabled (`mcp-observation-full-native.txt`). The source/wheel
byte comparison is repeated after completion and still matches all86 files.
Executable public commit: `2b1f10b28b58700651c6a389a767f571f5aa3fa5`. Its
[hosted verification run](https://github.com/SoonGwan/open-aegis/actions/runs/37352687862)
is tracked separately from these local results.

Hosted run **37352687862** completes successfully for that executable commit:
all six jobs pass. General Ubuntu tests pass936 cases and skip516 PostgreSQL
cases in701.43s; the console passes97 tests and builds the same final asset names.
The native PostgreSQL job separately passes385 storage cases,12 selection cases,
42 observation cases,11 event cases and174 MCP integration cases. These sets
overlap the full native suite and are not a combined test total.

All10 nonempty rehearsal receipts have `valid=true`: installed runtime, SQLite
goal recovery, native transfer, SQLite/native execution churn, native goal
recovery, two image profiles and two actual Compose profiles. PostgreSQL uses
16.15 on Ubuntu24.04. Owned recovery resources are removed. Application networks
use ordinary bridges with no application egress firewall; this does not prove
plugin/network isolation. The container profiles with a PostgreSQL driver still
exercise SQLite HTTP storage; native HTTP storage is exercised by the PostgreSQL
Compose and native installed recovery rehearsals. Logs and receipts are retained
under `artifacts/mcp-observation-hosted-*`.


## 2026-10-06 — durable cancellation-only recovery

Adds a transactional `mcp_revocations` outbox containing unsigned claim data,
original grant hash and endpoint/key fingerprints. Signed tokens, signing keys
and Bearer values are not persisted. Dispatch intent is dormant while execution
is live; admission removes it atomically with proof. An unconfirmed dispatch
activates it, and startup additionally recovers dormant intent independently of
the task's terminal status. Cleanup reconstructs only the original grant and
uses the fixed cancellation method; it never replays execution or target GETs.

Two observable defects were reproduced before fixes: a delayed acknowledgement
could overwrite a changed attempt, and a task already marked failed could hide
dormant cleanup intent from unfinished-task recovery. Each fails on SQLite and
actual PostgreSQL before its fix (`mcp-revocation-stale-ack-before.txt`,
`mcp-revocation-terminal-task-before.txt`). Current targeted recovery tests pass
**39 cases in43.65s** (`mcp-revocation-recovery-final.txt`). An earlier related
255-case suite passes before the last startup-helper fix; it is not claimed as
validation of that final helper (`mcp-revocation-settled-related.txt`).

Recovery tests include real source SIGKILL with a remote call already waiting
on its first owned GET, followed by actual HTTP app restart and acknowledged
remote revocation, no repeated GET and no unconfirmed proof admission. Both
SQLite and native PostgreSQL variants verify interrupted task state, valid audit,
released remote gate and graceful second-source lifespan/ownership cleanup. The
initial test incorrectly assumed SIGTERM exit0; Uvicorn restores the signal and
exits-15 after cleanup. The final test checks its completed lifespan marker and
released workspace/database ownership, while allowing0/-15.

Other cases cover confirmation loss with identical-token retry, false
acknowledgement, retry limit, expiry/endpoint/Bearer/key/claim/hash/attempt changes
refused before outbound cancellation, dormant live intent, normal admission
removal, dispatch/admission/audit rollback, bounded due-row SQL without Store.all,
shutdown during cleanup and lost native ownership. Confirmation and queue removal
share the audit transaction; confirmation loss/storage failure remain retryable.
Execution remains `unconfirmed` even when cancellation is acknowledged. Old
queue-free attempts, expiry, configuration changes and persistent failure cannot
be converted into confirmed cancellation. OS/egress isolation and full v1 gates
remain open.

The frozen wheel contains87 service Python files, all byte-identical to current
source. SHA-256:
`b8578f4465b63806b0c5f740f1470e0f017f3952a4cbe30c6191b8591a8bd668`.
Independent installed-wheel tests outside the checkout pass **311 related cases
in337.65s** with actual PostgreSQL enabled (`mcp-revocation-installed-tests.txt`).
This validates the final startup helper as well as the existing signed execution,
observation batch, registry, admission, cancellation and SDK contracts. The
installed locked-runtime/maintenance/release review also passes with zero target
requests (`mcp-revocation-installed-runtime.txt`). Main preview health is200/0.2.0a1
and all existing counts and task states match before/after restart. The public
source scan covers379 files with zero unignored candidates; it is not proof of
secret absence.

The final87-file recovery service also passes the full local suite with actual
PostgreSQL enabled: **1,491 cases in1,057.42s**
(`mcp-revocation-full-native.txt`). Hosted run
[37358449883](https://github.com/SoonGwan/open-aegis/actions/runs/37358449883)
for4e95d52 fails one PostgreSQL observed partial-followup assertion; the other five
jobs succeed. It is not an all-green hosted release receipt.

The failed test assumed that an immediately reviewed proposal could be accepted
while the background planner was still allowed to create an automatic failure
note. A controlled SQLite/PostgreSQL boundary probe against the original test
reproduces409 in both backends: only `fingerprint` and `shared_todo_context` change,
while the task, selected cells and proof remain unchanged
(`mcp-followup-boundary-before.txt`, rerunnable
`artifacts/test_observation_followup_boundary_probe.py`). This demonstrates a
mechanism consistent with the hosted failure; the hosted log did not capture the
field difference and cannot establish its exact timing by itself.

The test now covers both a settled background note and a forced note insertion
after review. It asserts stale acceptance409 with no new task or GET, followed by
fresh acceptance and a new approval that retries only the two failed cells.
All four SQLite/PostgreSQL cases pass in15.64s
(`mcp-followup-boundary-after.txt`). No production freshness guard or service file
changed; the87-file wheel/service evidence above remains applicable. New hosted
validation is required before claiming this test correction passes Ubuntu.

The corrected follow-up test and related registry, remote admission, execution,
cancellation, observed batch, recovery and automatic-note suites pass **224 cases
in313.39s** with native PostgreSQL enabled (`mcp-followup-native-related.txt`).
The correction is published in7d96ecd; hosted run
[37361283266](https://github.com/SoonGwan/open-aegis/actions/runs/37361283266)
was still in progress when this local receipt was recorded.

Hosted correction run
[37361283266](https://github.com/SoonGwan/open-aegis/actions/runs/37361283266)
for7d96ecd is now terminal **success in all six jobs**, including both container
and both Compose variants, verify and native PostgreSQL. The formerly failing
observed partial-followup test passes in the native MCP suite. This closes the
hosted validation of the automatic-note test timing correction and the unchanged
87-file durable revocation service; it does not validate the separate88-file
task-template candidate or close remaining v1 gates.

## Versioned task templates — candidate branch

The isolated task-template candidate adds CRUD, revision history, archive/restore,
bounded SQL search/pagination, list bookmarks, conflict comparison and explicit
current-scope pending-plan application. It keeps template origin through replan,
retry, results follow-up and observed derivation; template edits do not rewrite
existing plans. The service contains88 Python files. Template-specific native
SQLite/PostgreSQL tests pass **58 cases in30.35s**; relevant template, next-plan,
identity, dependency and goal suites pass **197 cases in142.69s**
(`task-template-server-final.txt`, `task-template-related-tests.txt`).

The original candidate loses template origin during replan and lets oversized
application requests escape as server exceptions. Both fail in both backends
before correction (`task-template-replan-before.txt`,
`task-template-oversize-before.txt`) and pass in the final58-case suite. Tests also
exercise atomic audit rollback for create/edit/archive/apply, changed scope,
changed template/current role, stale revision, role boundaries, request replay,
invalid authority-bearing defaults/overrides, fixed-default fresh scope,
archival and disabled remote tool refusal without outbound requests.

Frontend build succeeds and **98 Node checks pass** using Node22.18.0
(`task-template-web-build.txt`, `task-template-web-tests.txt`). The initial system
Node cannot run strip-types; that failed runner is not counted as a product test.
Actual owned browser UI review confirms create/edit/history/archive/restore/apply,
a two-tab409 with preserved draft, explicit latest-version comparison and saving,
original version1 on the existing task after template version6, target requests0
before approval and one GET after approval, and valid audit
(`task-template-ui-review.json`). Its temporary fixture exits143; the exact owned
workspace is then verified against the recorded task and removed. It does not
establish graceful fixture shutdown. Main preview data and runtime remain untouched.
Full mobile, failed-response replay across documents and remaining v1 gates remain
open.

The built wheel matches all88 frozen service files exactly. SHA-256:
`ceb7b7473159d92cc6dda5ceb48f1cf4948b790f6fdb8acebb23a9ab5ba23c50`
(`task-template-frozen-source.json`, `task-template-wheel-receipt.json`). Candidate
public-source scan covers383 files and reports zero unignored candidates; it is
not proof of secret absence. Installed-wheel and full-native runs were still
pending when this candidate receipt was written. No public v1 release is claimed.

Installed task-template wheel verification outside the checkout now passes
**197 cases in147.68s** with actual PostgreSQL enabled and an asserted import from
the temporary venv's site-packages (`task-template-installed-tests.txt`). Its owned
venv/test resources are removed. The full native candidate suite remains running;
this installed related-suite result is not a full v1 release gate.

The rendered template application lost-response review commits the server response
but sends503 to the browser once. The actual UI retains its error and task-name
draft, then reuses the same request ID and restores the existing pending task.
Both server submissions return200; browser statuses are503 then200; exactly one
task/application and zero target requests remain, with valid audit. The corrected
owned response intermediary exits0 and removes its temporary workspace
(`task-template-response-loss-ui-review.json`,
`task-template-response-loss-ui-process.txt`). Its first wrapper omitted the
application shutdown state and failed at cleanup; that fixture error is corrected
and the sequence repeated rather than claiming its first exit as graceful.

A stopped installed-wheel SQLite sequence (88-file write,87-file reader/writer,
88-file recovery) preserves original templates/history/task origin, but the old
writer drops origin on its new replan; the new reader does not automatically
repair that child. New current-template application works after recovery, audit
remains valid, target requests are zero and owned resources are removed
(`task-template-version-pair-review.txt`). Rollback is conditional on suppressing
old-version mutations when template provenance must remain complete; see
[release ordering](RELEASES.md). Native old/new runtime pairing remains untested.

The first candidate full native invocation finishes **1,515 passed and36 setup
errors in1,098.52s**, not a pass (`task-template-full-native.txt`). Its explicit
worktree shell selects macOS LibreSSL3.3.6, and every error occurs while generating
an Ed25519 fixture key in the two release modules. The same36 release cases pass
in4.54s when PATH selects required OpenSSL3.x
(`task-template-release-correct-runner.txt`). Production code is unchanged. A new
full native invocation with explicit OpenSSL3/PostgreSQL16 PATH is running
(`task-template-full-supported-native.txt`); it must finish before claiming a clean
full candidate result. PR1's hosted candidate run37363828003 is also still running.
The duplicate push run37363822445 for the exact same83433f0 source was cancelled to
avoid duplicating hosted work; it is not a failed product validation.

The supported candidate full-native invocation is now terminal **1,551 passed
in1,098.57s**, with actual PostgreSQL and required OpenSSL3 selected explicitly
(`task-template-full-supported-native.txt`). The service remains byte-identical
to the installed88-file wheel and to functional source83433f0.

Hosted candidate run
[37363828003](https://github.com/SoonGwan/open-aegis/actions/runs/37363828003)
for83433f0 is now **success in all six jobs**. Its first attempt passes verify,
container(true) and Compose(true), while three other jobs never acquire a hosted
runner and are cancelled with the annotation “The job was not acquired by Runner
of type hosted even after multiple attempts”. Retrying the unexecuted jobs closes
those checks without a production change. The earlier cancelled duplicate push
run is not substituted for this successful candidate receipt. Subsequent candidate
commits change only release/validation notes, with the88-file service and UI source
unchanged. This validates the task-template candidate scope; whole-service v1 gates
and the documented old-writer provenance limitation remain open.

## Task category candidate — 2026-10-06

The independent category implementation is a development candidate. It adds versioned
CRUD/archive/restore, immutable category and per-task membership history, bounded SQL
membership filtering, and an operator UI for atomic changes to 1–25 tasks. Classification
preserves execution fields; derived plans inherit classification with a fresh membership
revision. This entry does not close the v1 readiness gates.

- Dual SQLite/native PostgreSQL category tests: **48 passed in 23.77 s**. Coverage includes
  whole-batch stale/missing-member rejection, audit-fault rollback, immutable replay,
  revoked role/disabled-user checks, worker updates and real in-flight request completion,
  inherited-origin replacement, and SQL counts/pagination without `Store.all`.
- A test fixture initially sent a Boolean into PostgreSQL's integer `users.disabled`
  column; it now uses the schema's integer representation. SQL filter fixture setup was
  corrected to pass the lab URL and explicit checks to the existing test helpers. Those
  fixture failures were retained in local evidence and are not product regressions.
- Exact wheel/source equality: **89 Python files**, wheel SHA-256
  `8242a9f203c3c9a3e3881f8742c5e921a6bff7e3c63b0c914f0908a51e9db152`.
  An isolated install outside the checkout passed **245 related tests in 171.00 s** with
  native PostgreSQL. The import originated in the temporary virtual environment's
  `site-packages`, and owned temporary resources were removed.
- Frontend production build and **99 Node checks** passed. Build retains Vite's warning
  about the main JavaScript chunk exceeding 500 kB. A missing JSX closing brace in the
  new detail summary was caught by the build and corrected before the successful build.
- Actual owned desktop browser: create, version history, archive/restore, archived
  membership lookup by stable ID, stale edit draft retention and explicit latest-version
  review. Two tasks were classified atomically; the first committed response was replaced
  by controlled HTTP 503. Retrying the real form sent the identical request ID/body and
  returned HTTP 200 with **one operation and two member-history rows**. Original task
  execution fields were unchanged, no target GET occurred, and audit integrity passed.
  All owned tabs, server and temporary data were removed with fixture exit 0. Layout was
  reviewed again after search/card spacing adjustments. No mobile or screen-reader claim.
- Full native regression is running on the frozen service source with OpenSSL 3 and
  PostgreSQL 16 on the runner path. Hosted candidate and cross-version reviews are still
  pending at the time of this entry. The main preview remains on the verified template
  feature and does not contain this candidate's fixture data.

Installed category old/new SQLite pairing is now complete (`task-category-version-pair-review.txt`).
The 89→88→89 sequence preserves original category/version/history/receipt/task records and
valid audit with zero target requests. The old writer's new replan omits classification.
The first review incorrectly expected a new child after recovery; actual duplicate
protection returns the existing old-version child. The controlled follow-up explicitly
checks that identity and absence of automatic repair, then classifies the child with the
current writer and verifies its next new replan inherits current classification and origin.
All owned temporary resources were removed. Release ordering is conditional as described
in [RELEASES.md](RELEASES.md); native version pairing and backup/restore are not inferred.

Candidate pull request [2](https://github.com/SoonGwan/open-aegis/pull/2) remains draft while
full native and hosted checks run. Functional head `480b9d9` matches the frozen 89-file
installed wheel. The duplicate push run `37370339038` was cancelled deliberately; the
pull-request run `37370424605` is the retained candidate hosted validation.

The same installed 89→88→89 pairing also passes against actual owned PostgreSQL
(`task-category-native-version-pair-review.txt`). The old-writer classification omission
and retained-child behavior match the SQLite boundary. Installed `aegis.cli.backup` and
`aegis.cli.restore` then restore to a fresh PostgreSQL schema with an independently
captured trusted audit checkpoint. Category definitions, versions, membership history,
operation receipts and complete task records compare exactly before/after. An actual
source login creates sessions, and the restored session table is empty. The fixture
records zero target GETs and removes its cluster, server and temporary installation
(`task-category-installed-native-restore.txt`). This is a category-scoped native pairing
and backup/restore receipt, not coverage of every earlier release or mixed-version deployment.

The category candidate's full native regression is terminal **1,599 passed in
1,129.23 s**, with actual SQLite/PostgreSQL and the required OpenSSL 3/PostgreSQL 16
runner path (`task-category-full-native.txt`). Frozen service source remains the exact
89-file installed wheel; later commits change documentation only. This result closes
the candidate native regression check, while retained hosted run `37370424605` is still
running. It does not substitute for the remaining hosted checks or whole-service v1 gates.

Category functional head `480b9d9` now passes retained hosted run
[37370424605](https://github.com/SoonGwan/open-aegis/actions/runs/37370424605) in **all six jobs**.
Hosted verify reports **1,009 passed /590 skipped in785.52 s** and **99 frontend checks**.
Native groups pass **385 in372.66 s**, **12 in25.84 s**, **42 in108.28 s**, **11 in16.57 s**,
and **321 MCP/template/category cases in501.09 s**. Both container variants and both
Compose variants pass. Exact job logs are retained locally in `task-category-hosted-full.txt`.
Subsequent candidate commits change release/validation notes only.

Installed SQLite backup/restore also passes the category pairing, exact category/history/
receipt/task comparison, independently captured audit checkpoint and actual restored-session
revocation (`task-category-installed-sqlite-restore.txt`). Together with the native receipt,
this covers the owned category fixtures on both supported backends; it does not imply full
mobile/accessibility or every release/environment combination.

The previous template main source `e74c050` independently passes all six jobs in
[37369068051](https://github.com/SoonGwan/open-aegis/actions/runs/37369068051).
Two retry rounds were needed because unexecuted hosted jobs could not acquire runners;
the annotations name runner allocation, with no failed test step. Successful jobs were
retained and only cancelled/unexecuted jobs retried. Candidate functionality is validated;
release `0.2.0a1` remains alpha and v1 readiness gates remain open.

PR [2](https://github.com/SoonGwan/open-aegis/pull/2) is merged as main `f370d91`.
The main service matches all 89 frozen installed-wheel Python files. Rebuilt preview
assets are `/assets/index-BJd00qKd.js` and `/assets/index-YYjuvzvz.css`; HTTP responses
match their built bytes. Health reports `0.2.0a1`, and both category and template APIs
require authentication. Exact read-only snapshots before/after the owned restart keep
all 11 record-family counts and the four task states unchanged; no fixture category
records enter the main workspace (`task-category-main-preview-receipt.json`). The old
preview exits143 on SIGTERM, not a claimed exit0; the restarted service is healthy.
The merge-triggered main hosted run `37373173305` is pending, while the exact functional
candidate has already passed all six hosted jobs. No v1 tag or production-console
release is implied by this local development-preview update.


## Terminal task archives — local candidate

The local archive service atomically changes1–25 terminal-task organizational flags,
versioned history, operation receipts and audit. Actual completed-task archive/restore
preserves full task execution fields and all selected evidence families without a new
target GET. Invalid member/version/state, audit failure and revoked roles reject the
batch. Initial archive checks had11 failures: duplicate fixture asset registration,
an uncontrolled background planner changing the comparison and reused Annotated ID
constraints accepting short IDs. Corrected owned fixture setup and a dedicated request
ID type yield26 passing SQLite/native PostgreSQL cases in12.21s.

The frontend build and100 Node checks pass. The owned desktop exercise confirms
archive commit→503→same request recovery yields one operation/history, restoration
retains proof, and a selected revision0 remains pinned after another tab archives and
restores to revision2. The stale request gets409; explicit clear/reselection succeeds.
The first owned fixture preserves original task fields, valid audit and zero traffic
with five intentional operations/history rows, then removes tabs/listener/workspace
and exits0. Its screenshot exposed squeezed toolbar buttons; controls were moved to
a separate wrapping row. The final built desktop screenshot is reviewed and the second
fixture repeats response-loss recovery/restoration and actual new-document archived
bookmark restoration, then cleans up and exits0. This is not full mobile or assistive
technology verification. Installation, full regression, hosted and combined notification
integration checks are still pending; no archive release is declared.


Archive-related record/store/native HTTP checks first report101 passing and one old
assertion requiring `tasks?archived=true` to return422. That assertion is updated for
the new task archive contract while the unsupported notes archive filter still returns
422; all6 record-filter tests pass in1.84s. The same Annotated-ID precedence problem
is reproduced in existing category create/assignment (four actual backend cases fail
before correcting the dedicated16–80-character request type). Both complete category
and archive suites plus record queries then pass84 cases in39.99s on SQLite/native
PostgreSQL. Final100 Node checks and the formatted frontend build pass. The owned
90-module source/package freeze is pending installed/maintenance checks and has not
yet been combined with the separate93-module notification candidate.

## Notification channels and receiver receipts — candidate verification

The independent fixed-webhook implementation adds administrator-reviewed channels,
immutable versions, terminal-task source events, an atomic durable cursor/receipt,
persisted per-channel cooldown, bounded POSTs, attempt history, explicit test sending
for inactive channels and manual retry capped at3 attempts. Unknown/failed sends never
automatically retry. HTTP2xx means receiver acceptance, not human receipt.

The owned desktop browser exercised committed create→503→same-request replay with
ONE channel; HTTP500→explicit duplicate review→committed retry→503→same-request replay
with ONE retry operation and exactly TWO receiver POSTs sharing one Idempotency-Key.
The retry modal preserved the reviewed first-attempt snapshot while the parent polling
showed receiver acceptance after attempt2. Two-tab edit409 retained the draft, required
explicit latest-version review and produced exactly three channel versions. Channel
history and both attempt results were visible; the actual desktop screenshot was
reviewed. Audit remained valid. All owned tabs, listener, receiver and workspace were
removed. The first fixture ended with SIGINT/exit130 after cleanup; that exit is not a
successful fixture exit0. No mobile or assistive-technology claim is made.

Focused server checks passed72/73 before the last startup test used a nonexistent
`/health` path; after correcting it to the actual `/api/health`, all13 HTTP cases passed
in11.41s. The earlier actual native related suite passed181 in80.20s; the initial
installed package passed198 in88.69s, and initial installed93→89→93 plus offline
backup/restore preserved all selected notification records and trusted audit checkpoints
on SQLite and native PostgreSQL, with restored sessions0 and only the two intentional
receiver POSTs. These initial installation receipts precede the following source fix.

A controlled native owner-session termination during an owned pending POST exposed
missing execution admission: before the fix a replacement owner could acquire the
workspace during the pending request. After adding the existing store execution permit
around the POST, the same scenario passes: takeover is fenced until the pending POST
finishes, receipt persistence refuses the lost owner and a fresh owner recovers unknown
without a second POST (1 case in1.89s). The prior full run was intentionally stopped at
266 passing cases to include this source correction; it is not a completed full run.

The final frozen package contains93 Python modules exactly matching source hashes,
SHA256 `8734248fd38642c9b244472cfd3023f18dc846e50510be1a77f1599ba06cd12a`.
The frontend build passes and101 Node checks pass. Existing Vite large-chunk warning
remains. The final exact package passes199 installed related checks in88.91s, including
the owner-loss fence, outside the checkout. Final installed93→89→93 and offline
backup/restore pass on both SQLite and native PostgreSQL: notification/channel/version/
attempt/operation/runtime/task rows compare exactly, the independent trusted audit
checkpoint verifies, restored sessions are0 and only the two intentional test POSTs
occur. Owned temporary installation, receiver and cluster are removed. Final full native
and hosted runs remain pending. Version remains0.2.0a1; notifications are partial ARTEX scope.


Strict notification request-budget correction: the reused Annotated record-ID type
overrode an extra Field(min_length=16), so short create/test request IDs reached
operation handling. Actual HTTP tests fail before the correction (4 failed/2 passed);
a dedicated Annotated request-ID type now enforces16–64 characters for create/edit,
test and retry. The complete notification suite passes80 cases in30.95s on both
backends, including the controlled native owner-loss fence. This changes one of the
93 Python modules; the latest exact wheel is SHA256
`c2ac9559f3af699823f00301f53fbdb621dfc3075547752cfc6fb014ca7b3004`.
Its full native/installed/backup-pair checks are running again and preceding wheel
receipts are retained separately rather than attributed to this hash.

The preceding interrupted full native run recorded one failure in the PostgreSQL
remote observed-batch source-restart case. Interruption during teardown prevented a
complete assertion report; it is not a successful full run. The unchanged source-restart
case then passes both backend variants in4.19s in isolation. The cause is unresolved;
no timing fix or weakened assertion is inferred. The current full run stops on the
first failure to retain its precise assertion and investigate if it recurs.


The request-budget-corrected exact wheel
`c2ac9559f3af699823f00301f53fbdb621dfc3075547752cfc6fb014ca7b3004` now passes
205 installed related cases in90.21s outside the checkout and repeats the installed
93→89→93 pairing and offline backup/restore on SQLite/native PostgreSQL with exact
selected rows, valid independent checkpoint, restored sessions0, only two intentional
test POSTs and removed owned resources. Retained latest-source hosted PR run is
[37377405131](https://github.com/SoonGwan/open-aegis/actions/runs/37377405131).
The obsolete5485037 run was automatically cancelled by the later source update; its
container/Compose jobs passed but its verify/native jobs were cancelled. Duplicate
push run37377400210 was cancelled intentionally for the same latest source, retaining
the PR run. Cancelled runs are not all-job success evidence. Full native remains running.

The independent category main merge `f370d91` now passes all six retained hosted jobs
in [37373173305](https://github.com/SoonGwan/open-aegis/actions/runs/37373173305).
Only its unexecuted native job was rerun after the runner-allocation annotation; all
other successful jobs were retained. This confirms the existing category main source
and does not promote the newer notification draft or declare v1 readiness.


The initial standalone90-module archive wheel
`d35e2535efc3308ff88860047e6f839b47267b62d659b834aa42df706a863cd9` passes219
installed related cases in105.43s outside the checkout; owned native/temp resources
are removed. Archive source is then combined with notification candidate4ecf646 for
integration review. Both routing groups, SQL fields, native CI cases, CSS and URL tests
are retained when resolving additive merge conflicts. The combined94-module source
passes164 native related cases in72.82s and two additional actual-receiver tests in
3.42s confirming archive/restore never repeats the original terminal notification.
The combined frontend build passes102 Node checks.

The exact combined wheel is SHA256
`d306f48198c792691786cff8a31ff183249874ecb3c9cded9455a87327bc345d`,94 Python
modules byte-matching frozen source. Combined full native, installed and maintenance
checks are running; prior90-module receipts are retained separately and not attributed
to this hash. The combined browser/preview and hosted checks remain pending. No new
archive record is created in the persistent main preview.


Final request-budget-corrected notification full native regression is terminal:
**1,679 passed in1,169.10s**, with OpenSSL3/PostgreSQL16 and actual native backend
fixtures. The previously recorded source-restart case passes in this complete run;
its earlier interrupted assertion cause remains unproven, and no speculative fix
is attributed. Source remains the exact93-module wheel SHA256
`c2ac9559f3af699823f00301f53fbdb621dfc3075547752cfc6fb014ca7b3004`.
Hosted latest-source verify and both container/Compose variants pass; the native hosted
job remains pending. Notifications stay draft until all required hosted checks finish.


Notification hosted run [37377405131](https://github.com/SoonGwan/open-aegis/actions/runs/37377405131)
is terminal with all six jobs successful on functional source `7e3dd0c7e90acc3a8999939d17d36b42515b86bc`.
Documentation-only follow-ups preserve its frozen93 Python modules. Full native1,679,
installed205, frontend101 and both-backend installed pairing/backup receipts above
apply to this source. This permits merging notification PR3; alpha remains0.2.0a1.


The exact combined94-module package now passes301 installed cases in141.92s outside
the checkout with native PostgreSQL. Installed94→89→94 and offline backup/restore
pass on both stores with exact selected records, valid independent checkpoint and
restored sessions0; only two intentional test POSTs occur and no target GET occurs.
Owned cluster/receiver/install resources are removed. Combined desktop browser
archive503→same-request200→restore200 creates exactly two operations/history rows,
preserves original execution fields and valid audit with0 target requests. Both
notification navigation and a new-document archive filter are observed. Both owned
tabs close and the fixture exits0 removing temporary data. Full native/hosted pending.


Notification main merge `d048337ec3f7210f15ecc09b06d3e4ac68dbdbf6` is installed in
the owned persistent loopback preview at127.0.0.1:8790. All93 Python modules match
the validated frozen candidate. The Node22 frontend build passes; served HTML and
assets compare byte-for-byte with build output. The original11 selected collection
counts and four task states remain identical across the idle restart. Health is200
at0.2.0a1; template/category/channel/delivery reads return401 unauthenticated.
No notification fixture or target request is added to the persistent workspace.
Main hosted run37379865635 remains pending; prior PR all-six success is distinct.


Prompt supplement version candidate connects planner/conversation capture to durable
call attempts and final metadata. Related native/backend checks pass87 cases in16.29s;
owned actual provider POST retains revision1 while the current prompt changes to2,
and same-message replay makes no extra POST. Invalid model tools retain the approved
check set. A controlled two-save race has one200 and one409. UTF-8/variable/request
budgets, fresh role, audit rollback, version cap and corrupt fingerprint are checked.
Frontend build and101 existing Node checks pass. Owned desktop preview/save503→same
request200 preserves one version; two tabs yield200/409, preserve the original draft
and require explicit latest review before200. Default restoration creates version4;
four histories/operations remain,0 provider calls/target requests, valid audit, both
tabs closed, fixture exit0 and temporary data removed. Initial assertions wrongly
expected no audit on POST preview/422; existing request-audit middleware records these
requests. Corrected checks retain zero domain mutation and assert that request event.
Full native, installed, cross-version maintenance and hosted checks remain pending.

Combined task archive/notification full native regression completes with
**1,711 passed in1,187.68s**, OpenSSL3 and PostgreSQL16. Frozen94 Python modules
remain unchanged through documentation-only main merges. Installed301, combined
Node102, owned browser, installed94→89→94 and both-store offline restoration
receipts above apply to wheel SHA256
`d306f48198c792691786cff8a31ff183249874ecb3c9cded9455a87327bc345d`.
Retained hosted PR run37379339479 passes verify and four container/Compose jobs;
native hosted remains pending. PR4 now targets main after notification PR3 merge.


Retained archive hosted PR run[37379339479](https://github.com/SoonGwan/open-aegis/actions/runs/37379339479)
is terminal with all six jobs successful on functional source `a5e5fe51803998a7985e6f903516ffdb10539793`.
Later main merges/documentation preserve all94 frozen Python modules and executable
UI source. The duplicate push run37379267778 was cancelled intentionally and is not
all-job success evidence. Full native1,711, installed301, Node102, both-store
maintenance and combined browser evidence now permit merging archive PR4.


After integrating verified archive main26a1e8a, the prompt candidate passes173 related
native/backend cases in59.39s, frontend build and102 Node checks. The independently
packaged95 Python modules exactly match frozen source; wheel SHA256
`bf22cf5ed105f2587f7c2e954f2160eab3f8273b26c08a7fac5f9ccb01622ce8`.
Official public-source Gitleaks scan covers405 tracked/unignored files with0 candidates.
The additive app/SQL/CI/documentation merge retains both prompt and archive contracts.
Final full native, installed and95→94→95/backup receipts remain pending.


The exact95-module prompt package passes388 installed cases in156.51s outside the
checkout, including native backend cases, with temporary installation/cluster removal.
Installed95→94→95 and offline backup/restore pass on both stores: prompt/config/
version/operation rows and an explicitly synthetic committed call snapshot are
preserved alongside task archive and notification families. Original save replay
returns revision1 without reverting current default revision2. The independent audit
checkpoint verifies, restored sessions are0, no target traffic occurs and only two
intentional notification test POSTs occur. Actual provider snapshot admission is
separately exercised in the earlier owned HTTP tests, not inferred from this fixture.
Retained hosted source run is37381945973 on `ff7a0cd21c2704346ed57e56b43b77834acb2adb`;
full native and hosted checks remain pending. Public PR5 stays draft.


The initial prompt full native run stops honestly at1 failed/468 passed in350.28s.
The source-restart test immediately constructs a new native engine after stopping
only the old engine, leaving the application event planner alive. Its precise
failure is WorkspaceBusy at new ownership admission. Twelve observed isolated runs
pass and do not identify the historical holder. A controlled admitted event-planner
read then reproduces the exact refusal: its reader PID remains a granted runtime
ShareLock after engine-only shutdown. Matching the real application lifecycle
(background worker joins before engine shutdown) passes the same original recovery
assertions. This establishes the tested race mechanism, not the unrecorded holder
in the earlier interrupted run. The restart fixture now closes notification/event
workers before its engine, without sleeps, acquisition retries, weakened assertions
or any change to production ownership fencing. Frozen95 production modules and
wheel hash remain unchanged. The first notification-barrier probe was inconclusive
because no notification worker starts with no destinations; the event-planner
probe supplies the decisive owned lock observation. Full native must run again.


After matching restart shutdown to the application lifecycle,107 native/backend
MCP observation, ownership and notification delivery checks pass in158.48s.
Production source is still the frozen95-module wheel. Latest hosted source run
is37383092295 at `a82836b646c6e34dd7b08b9224b27de3f3ccfed6`; its preceding
ff7a0cd run37381945973 was cancelled by the new test/source update and is not
all-job success evidence. Full native is rerunning with the original strict failure
stop and source-restart recovery assertions retained. The owned distinguishing
probe is rerunnable in an isolated checkout of5db3c36 (before the fixture correction).

The model profile candidate has96 independently authored Python modules. Related
native SQLite/PostgreSQL, prompt, provider, conversation, usage and ledger checks
pass135 cases in28.38s, including owned provider model/key admission, in-flight
selection changes and final snapshot mismatch rollback.42 profile cases alone pass
in11.78s. Frontend build and103 Node checks pass. Owned two-tab browser review
records [503,200,503,200,200,409,200,200,409,200]: lost create/default responses
replay exact UUID/body; concurrent profile/default writes preserve drafts and require
explicit latest-version review. Exactly3 profile and3 default versions/operations
remain, no provider/target calls occur, audit verifies, tabs and disposable fixture
close with temporary-directory removal. Desktop screenshots were inspected.
Full native/installed package/backend maintenance/hosted checks remain pending;
this feature is not yet merged. Task/agent model pins and provider connectivity/
model catalog/failover remain unimplemented.

Archive main merge `26a1e8acdd60c3da15022fbb7f6fe9609fb7840d` is installed in
the persisted loopback preview127.0.0.1:8790. Frozen94 modules match validated
source; Node22 build passes and served HTML/assets compare exactly. Original11
collection counts and four task states remain identical across the idle restart.
No archive/notification fixture is added. Health200 is0.2.0a1 and unauthenticated
archive mutations/history, notification channels, templates/categories return401.
Notification main run37379865635 was cancelled automatically by the newer main merge;
it is not all-job success evidence. Archive main run37381510130 remains pending.


Archive main hosted run[37381510130](https://github.com/SoonGwan/open-aegis/actions/runs/37381510130)
is terminal with all six jobs successful on merge `26a1e8acdd60c3da15022fbb7f6fe9609fb7840d`.
This completes hosted verification for the currently running94-module loopback
preview. The newer95-module prompt draft has separate running checks and is not
promoted by this main receipt. Version remains0.2.0a1.


Final prompt full native regression passes **1,747 in1,197.75s** after the lifecycle
fixture correction, retaining all original recovery assertions. Hosted run
[37383092295](https://github.com/SoonGwan/open-aegis/actions/runs/37383092295)
passes all six jobs on `a82836b646c6e34dd7b08b9224b27de3f3ccfed6`. Later documentation
merges preserve all95 frozen production modules. Exact wheel/install388, Node102,
95→94→95 and both-store backup receipts remain applicable. Combined desktop
read-only review also observes prompt navigation and ordinary/archive task filters
with0 mutations/provider calls/target requests, closed tab and fixture exit0.
This permits merging PR5 while version remains0.2.0a1. The independent96-module
model-profile workspace is not part of this verified candidate.

Prompt main e11878a now serves the frozen95-module source at the local preview
http://127.0.0.1:8790. Restart preserves all59 persisted record bodies exactly
(SHA2566419aec7272b10f9e72c246c956d03dd4d154dd48e79d1262d7189a01ede465c),
including the original pending/completed/failed task states. Served HTML/assets
match the fresh frontend build byte for byte; health reports0.2.0a1 and unauthenticated
prompt/channel/category/template reads return401. This is a local preview,
not an external production deployment. Main hosted run37385598230 remains pending.

Model profile native boundary/race review now passes58 cases in14.34s. Two concurrent
writes admit only one reviewed profile/default revision; invalid recipient addresses,
ports and credential controls never enable a profile. The real25-profile catalog
cap rejects an extra profile, while explicitly synthetic revision200 boundary rows
verify rejection without pretending200 actual saves occurred.
Prompt main hosted run37385598230 fails the native report deadline case with
QueryCanceled(statement timeout), while384 other native checks pass. The actual
new native boundary regression fails before the fix: PostgreSQL is configured for
9.998s despite a9.998767958022654s remaining export budget. Truncating milliseconds
can trigger SQL cancellation before the monotonic permit expires, allowing the raw
exception to escape. Rounding up milliseconds preserves the budget; unchanged
regression and existing reports/disconnect/deadline/export checks pass32 cases
in12.95s. No sleeps/retries, deadline increases or exception suppression are added.
This demonstrates the controlled rounding mechanism, not the unrecorded exact
remaining value on the hosted failure. Prior95-module wheel remains prior source;
the one production module change requires a new package receipt.

An additional real API regression rejects control characters in profile names before
storage. It fails before (SQLite returns200 for a NUL-containing name), then all64
native/backend profile cases pass in15.77s after validation. The initial full run
was intentionally interrupted at340 passes/163.44s and is not full-suite success.
The initial96-module wheel15d155c6 passes both-store96→95→96/offline backup restore;
its receipts apply to that earlier source. The final source/package and full native/
installed/maintenance checks must be refreshed. Provider-origin retention is stated
explicitly: existing call receipts retain scheme/host/port, while profile versions
and call records do not retain API keys or full endpoint paths.

Final96-module model package matches frozen source exactly; wheel SHA256
5eb52b286114fa9a690ffb08aed21c3874d3c6df4f2fbc1342103a2604f24e4e.
Both-store installed96→95→96/offline backup restore is repeated on this package:
model/profile/default families and the explicitly synthetic call snapshot remain
exact, alongside prompt/archive/notification rows. Checkpoint verifies, restored
sessions are0, receiver POSTs are exactly2 intentional notification tests with no
replay duplicates or target traffic, temporary resources are removed. The earlier
wheel15d155c6 passed478 installed checks in187.00s; final installed/full runs continue.

Call details now render the stored profile/default/prompt snapshots. An explicitly
synthetic owned committed call stays at historical model/profile/selection/prompt
revision1 while current configuration is revision2. Browser DOM and desktop images
show the historical model/additional instruction, current model separately and the
settings-to-model-review navigation. No actual provider POST or target traffic is
used for this display fixture, audit verifies and its tab/workspace are removed.
This frontend-only change preserves all frozen96 Python module hashes. Build and
103 Node checks pass. Task/agent pins and connectivity/model-list/failover remain open.

Final wheel5eb52b28 passes484 installed checks in188.24s outside the checkout,
including native/backend model profiles and report deadlines, with installation/
cluster cleanup. Final local full native and retained hosted run37387988876 at
65235660b1af344d369e4fb95853636cfe434c88 remain pending. Duplicate push run
37387983785 is intentionally cancelled and is not success evidence. Earlier model
hosted heads21b1bfb and3d9c1a9 are superseded/cancelled. Environment examples below
are operator documentation; all96 frozen production modules remain exact.
Report deadline wheel has95 modules and changes only aegis/postgres_streams.py
from the prior prompt freeze. SHA256a059c78cd3e7e8f618d7662943709879aa6d4302d5b38e384652f9a936b8eff8.
All32 report/export checks also pass in17.28s on the installed wheel outside checkout,
including native SQL deadline/disconnect cleanup; temporary resources are removed.
Retained PR6 hosted run37387185260 remains pending; its duplicate push37387178574
was intentionally cancelled. The original main run37385598230 is terminal with five
successful jobs and one native report failure, not six-job success.

Retained PR6 hosted run37387185260 is terminal with all six jobs successful at
functional source178ce3eba1c767a02b6951ab30c3222e9961a904. Subsequent branch changes
are validation documentation only; the95 production modules exactly match the
installed32-case wheel receipt. This closes the native report deadline correction;
prior main run37385598230 remains honestly recorded as failed.

Report correction mainf7765f0 now runs at the existing local preview
http://127.0.0.1:8790. Verified owned oldPID57246 was terminated gracefully;
all59 record bodies retain SHA2566419aec7272b10f9e72c246c956d03dd4d154dd48e79d1262d7189a01ede465c
and original pending/completed/failed task states. Exact95-module source matches
the installed report wheel; existing UI assets remain byte-exact and unauthenticated
reads return401. Version is0.2.0a1. This is not an external deployment.
Main hosted run37389130077 remains pending; PR6's six-job success is retained separately.

Final frozen96-module model source passes the complete native/backend suite:
1,812 passed in1,217.29s (20:17), with the strict failure stop retained. Installed484,
frontend build/Node103, owned browser, both-store96→95→96/backup restore and public
scan receipts apply to the same production module hashes. Current hosted source
run37387988876 still awaits its PostgreSQL job; five other jobs are successful.
Subsequent main merges and documentation commits change no production/UI execution
source. The earlier340-pass interrupted run is not substituted for this full result.

Retained model PR7 hosted run37387988876 is terminal with all six jobs successful
at functional UI source65235660b1af344d369e4fb95853636cfe434c88. Later branch commits
are documentation/main-doc merges only; Python96 and executable UI source remain
unchanged. Full native1,812, installed484, Node103, both-store maintenance and owned
browser receipts now permit merging this scoped model profile feature. Candidate
version remains0.2.0a1; catalog/connectivity/task-agent pins/failover/mobile/long-running
work is not declared complete. Main report run37389130077 is tracked separately.

Model profiles main994963d now serve the exact frozen96-module source and the
fresh separately staged frontend at localhttp://127.0.0.1:8790. Verified owned
PID52298 exits before UI replacement/restart; all59 record bodies retain original
SHA2566419aec7272b10f9e72c246c956d03dd4d154dd48e79d1262d7189a01ede465c
and task states. Served assets/index-iRUJ9NXv.js and index-gW8Sd6S8.css match build
bytes. Model configuration/profile/prompt/channel/category/template reads require
authentication(401); health is0.2.0a1. This is a local preview, not external hosting.
Main run37390419067 is pending; prior report main37389130077 is automatically
cancelled by this merge and is not six-job success evidence. PR7 retains six successes.


## Explicit fixed-provider model catalog checkpoint — 2026-10-06

The isolated catalog branch adds an administrator GET to the reviewed provider's
fixed /models path, immutable request receipts, bounded ID-only responses and
25-row SQL history. Owned SQLite/native PostgreSQL tests cover actual auth/path,
response rejection, same-ID replay, stale role/profile/credentials, audit rollback,
shutdown, real restart and native backend-owner termination/replacement fencing.
Actual26-request paging passes on both stores; the200-record rejection boundary
uses174 explicitly synthetic records, not174 additional provider requests.

The first full regression stopped after30 passes at
test_review_auth_roles_and_strict_checkpoint: catalog.close set the app-wide
shutdown event and later user creation returned503. The fix gives the catalog its
own stop event, observes the app-wide event without mutating it, and clears the
local event at lifespan startup after joining old requests. The unchanged failing
audit test plus catalog checks now pass49 cases with one SQLite skip of a native
owner-only case. Original failed logs and the initial97-module wheel are retained
privately; this is not a full-suite success claim.

Owned browser statuses503,200,409,200 prove exact-body/UUID replay after a lost
committed response and explicit latest-profile adoption before another request.
There are exactly two actual provider GETs and two committed query receipts at
profile revisions1/2. Historical details retain the old model, the new result shows
the new model, defaults/call records remain empty, target traffic is zero and the
audit chain is valid. Desktop screenshots/DOM were inspected; owned tabs closed
and temporary fixture/provider removed. Final UI differs from initial retry review
only in readable local timestamp formatting. Full mobile/screen-reader work is open.

Final full native, installed wheel,97→96→97/backup restore and GitHub jobs remain
pending. Version remains0.2.0a1. No third-party scans or actual chat connectivity
claim is added by catalog success.


## Task-specific model selections checkpoint — 2026-10-06

A separate branch extends the existing planner/conversation roles with reviewed
task-specific profile selections, immutable CAS receipts and25-row SQL history.
The selection never alters task scope/checks/plan/approval. Unavailable pins never
silently choose another provider; clearing follows the workspace default. Actual
owned planner/conversation POSTs, held old/new call snapshots and same-ID chat replay
pass on SQLite/native PostgreSQL. Related tests pass136 cases in33.26s.

The first history read failed because purpose was not an admitted SQL filter; the
filter is now restricted to task-model record kinds. An old capture test spy also
required the new optional taskID argument; its no-provider-on-stale assertions are
unchanged. Explicit corrupted stored archive revision-1 was accepted before the
new bound check, then rejected; booleans/overflow and capture error translation
also pass. An unbound profile factory initially ignored a persisted task pin and
returnedNone; that same case passes after constructing TaskModels in the standalone
factory. Original failures are retained privately.

Owned browser statuses503,200,200,409,200,200 prove exact-ID/body response-loss
replay, competing selection conflict, explicit latest adoption and task-only chat
configuration. Four immutable versions/operations result(planner3/conversation1).
Original task/scope/approval remains exact; defaults, target traffic and call records
remain empty and audit is valid. Readable profile labels appear only for exact current
profile revisions; different historical revisions retain their identifiers. Desktop
DOM/screenshots inspected; owned tabs close and fixture temp directory is removed.
Browser uses the bound app profile service; the later backend change affects only
the unbound factory, covered separately. Later frontend change is label formatting
only and its final render was inspected. Node103 and production build pass.

Full source/installed package, both-store98→97→98/restore, hosted checks and complete
mobile/screen-reader validation remain pending. Version remains0.2.0a1. Older97
understands retained records generically but does not honor task model pins during
AI calls; rollback rehearsal must suspend AI planning/conversation and verifies
record preservation rather than equivalent old-version model execution.
Merged model profiles main run37390419067 is now terminal success at
994963dd2d87303b99f76acdb4336fb894a0e0ca: verify, postgres-storage, both image
variants and both Compose variants all succeed. This six-job main result is distinct
from retained PR7 run37387988876; earlier report main37389130077 remains cancelled.
Local preview still serves the exact frozen96 source with all59 record bodies
preserved. The independent catalog branch is not part of this main proof.


Final catalog97 wheel is SHA2566c63042652a03220b0e9e16d0d8dbfa7eae8d60f85d289cc4ae8af093a3e7dcf
at executable sourceead23e0d9e7747356a0caff8f25c309faf4810fe. Outside-checkout
installation passes529 cases, with one SQLite skip of a native-owner-only case,
in222.22s; temporary installation and owned cluster are removed. Both stores pass
97→96→97 and offline backup restore, preserving actual catalog receipts alongside
profile/default/prompt/archive/notification records and explicitly synthetic old
call snapshots. Exactly two owned catalog GETs and two intentional notification
POSTs occur across both stores; replay, version transition and restore add none.
All selected rows and trusted checkpoints remain valid; restored sessions are zero.

The initial pre-fix wheel remains archived with failed full/audit and installed
usage-summary regressions: installed525 pass,2 fail,1 skip in221.63s. Its successful
pair/restore is historical and does not substitute for final wheel validation.
Final full native and retained PR8 run37392213028 remain pending. Duplicate push
run37392167872 was explicitly cancelled and is not success evidence. The subsequent
main-document merge changes no Python/UI/test/CI source fromead23e0.


Final catalog full native/source run passes1,857 cases, with one SQLite skip of a
native-owner-only case, in1,256.86s(20:56). Frozen Python97 and executable UI/test/CI
source remain unchanged fromead23e0. Installed529/Node103, both-store97→96→97 and
backup restore, owned browser and public-source secret scan also pass. The retained
PR8 hosted PostgreSQL job remains pending; five other jobs have succeeded. This
scoped feature is ready for final hosted review, not a v1 or full parity declaration.


Retained PR8 run37392213028 is now terminal success at executable source
ead23e0d9e7747356a0caff8f25c309faf4810fe: verify, postgres-storage, both image
variants and both Compose variants all succeed. Final native1,857(+one native-only
SQLite skip), installed529(+same skip), Node103, both-store transitions/restore and
owned browser receipts permit merging the scoped catalog feature. Later local
commits merge/update documentation only; Python97 and executable UI/test/CI source
remain exact. Version remains0.2.0a1; this is not a full parity/v1 declaration.


Catalog PR8 is merged at mainde38cca7613540bad4ab8c8d781d620e8337fc91. Root
source exactly matches frozen97 and serves the separately staged production UI
at localhttp://127.0.0.1:8790. Owned prior PID67333 exits before replacing web/dist;
served assets index-hm_MBOqY.js/index-gW8Sd6S8.css match build bytes. All59 record
bodies retain SHA2566419aec7272b10f9e72c246c956d03dd4d154dd48e79d1262d7189a01ede465c;
selected counts/task states remain exact. Health is0.2.0a1 and configuration/profile/
prompt/channel/category/template/catalog-history reads require authentication401.
This remains a local preview, not external hosting. Main run37394395526 is pending;
retained PR8 run37392213028 has six terminal successes.

Catalog main run37394395526 is now terminal success at
de38cca7613540bad4ab8c8d781d620e8337fc91: verify, postgres-storage, both container
variants and both Compose variants all succeed. This six-job main result is
separate from retained PR8 run37392213028. Later main commits reconcile documents
only; the local97 preview and all59 persisted record bodies remain unchanged.

Frozen task-model98 wheel is SHA25617516a854cfa2303cb1479ae9b2fa083757c9c5ed1104d5d07ffbb8028d69700
at executable sourced6179affbbba69a3dc0f1ae90aef58f56c129d7d. Outside-checkout
installation passes553 cases, with one SQLite skip of a native-owner-only case,
in232.90s(3:52); temporary installation/owned cluster are removed. Both stores pass
98→97→98 and offline backup restore with task selections/versions/operation receipts,
actual catalog receipts, profile/default/prompt/archive/notification records and
explicitly synthetic old call snapshots preserved. Exactly two owned catalog GETs
and two intentional notification POSTs occur; transition/replay/restore add none.
All selected rows and trusted checkpoints are exact/valid; restored sessions are zero.

Old97 credentials are explicitly unavailable and chat is disabled; settings confirm
AI planning/conversation unavailable, so this demonstrates safe maintenance record
preservation rather than old-version enforcement of task-specific model semantics.
New98 restores the reviewed credentials and immutable old selection receipt without
rolling the current selection back. Later main merge is documentation only and does
not change frozen98/executable UI/test/CI source. Full native and hosted checks remain
pending; Node103, build and the public-source secret scan pass.

Final frozen task-model98 full native/source run passes1,881 cases, with one SQLite
skip of the native-owner-only catalog case, in1,268.43s(21:08). Python98 and all
executable UI/test/CI source remain unchanged fromd6179af. Installed553(+same skip),
Node103, both-store98→97→98 and offline backup restore, owned browser and official
public-source secret scan pass. Retained PR9 hosted run37395323928 is pending;
duplicate push run37395291216 is explicitly cancelled, not successful evidence.
Subsequent documentation-only commits do not constitute another full source run.

Retained PR9 run37395323928 is terminal success at
cd0d8c3952eef889de646bc9d77560741efa3088: verify, postgres-storage, both image
variants and both Compose variants all succeed. Executable implementation remains
d6179af; subsequent commits merge/update documentation only. Final full native1,881
(+one native-only SQLite skip), installed553(+same skip), Node103, both-store pair/
backup, owned browser and public-source secret scan permit merging the scoped
task model selection feature. This is not a v1 or full ARTEX parity declaration.

Task-model PR9 is merged at mainc0116456fc7ac8e1aa199f8fee58de74262dfd02.
Root Python98 and executable UI/test/CI source match the frozen task candidate.
Owned prior preview PID95446 exits before root fast-forward and web/dist replacement;
the separately staged production assets index-DhSwXClv.js/index-gW8Sd6S8.css are
served byte-exact at localhttp://127.0.0.1:8790. All59 record bodies retain
SHA2566419aec7272b10f9e72c246c956d03dd4d154dd48e79d1262d7189a01ede465c;
selected counts/task states are unchanged and idle. Health remains0.2.0a1, and
unauthenticated configuration/profile/catalog/task-model/history reads are401.
This is a local preview, not external hosting. Main run37397383118 is pending;
retained PR9 run37395323928 has six terminal successes. Current readiness/inventory/
feature documents distinguish verified existing-task selections from creation-time
pins, custom agents and other remaining model work.
