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
