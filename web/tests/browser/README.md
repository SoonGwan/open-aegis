# Modal keyboard regression fixture

Run `npm --prefix web run dev -- --port 8812` from the repository root, then open
`http://127.0.0.1:8812/tests/browser/modal-focus.html`. This fixture imports the production
Modal and stylesheet, updates its parent every second, and makes no API/target requests.
It is outside Vite's production entry and is not included in the built service.

1. Open the dialog. Focus starts on Close. Tab reaches the middle button, then the final
   summary. The negative-tabindex button and input inside a disabled fieldset are skipped.
2. Tab from the final summary wraps to Close. Shift+Tab from Close returns to the summary.
   Enter toggles its details. Waiting through several parent updates must keep focus.
3. Escape closes the dialog, restores the opener and removes background inert/scroll lock.
   The recorded close tick must match the current tick, proving the latest callback runs.
4. Repeat at `modal-focus.html?last=region`. Shift+Tab from Close reaches the final scroll
   region; ArrowDown scrolls it and Tab wraps back to Close.
5. Inspect the dialog's labelledby/describedby references: they resolve to the visible
   title and subtitle. This checks DOM associations, not real screen-reader output.

A production regression case is the asset archive confirmation: open it without confirming,
Tab from Close to Cancel, wait more than four seconds, and verify focus stays on Cancel.
Escape must return to the source Archive button. The old onClose effect dependency moved
focus back to Close on every background refresh.

## Native radio-group boundaries

Open `modal-focus.html?last=radio`. The final native group initially checks the first
radio. Tab from that radio must wrap to Close; Shift+Tab from Close must return to it.
ArrowRight selects the second radio; repeat both directions and check selection is kept.
Wait through parent tick updates without moving focus, then Escape must return to opener.
The pre-fix regression left document BODY active when Tab departed the checked first
radio: every radio exposed tabIndex=0 but the browser uses one group stop.

Repeat at `?last=radio&choice=none`: fresh-document forward entry reaches first radio,
reverse entry from Close reaches last radio without selecting it. Tab from a focused
unselected member wraps; Shift+Tab from the first returns to summary. Browsers may remember
an unselected group's previously focused member, so check containment and preserved
selection rather than assuming every later forward entry is the first member.

Repeat at `?last=radio&forms=two`: identically named groups with different form owners
remain independent. Shift+Tab from Close reaches the trailing group's checked radio;
another Shift+Tab reaches the separate form's checked radio; forward Tab reverses this.

These checks follow [W3C modal keyboard guidance](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
and [native radio-group considerations](https://www.w3.org/WAI/ARIA/apg/patterns/radio/).
They verify DOM focus and native keys, not real screen-reader output or every browser.

Open `modal-width-review.html` for the same production Modal with synthetic long radio
labels. Its 320/390/768 controls resize actual iframe documents. The visible metrics report
root and dialog client/scroll width plus vertical content height. Review wrapping and the
vertical scrollbar; a narrow document is not real mobile/touch/zoom emulation. The fixture
makes no API requests and adds no production route/bundle.

This fixture is a manual browser regression, not part of `npm test`. Full mobile, assistive
technology and all workspace journeys require separate verification.

## Reduced-motion button review

Enable the operating system/browser's reduce-motion preference, then open the app or
modal fixture. Confirm `matchMedia('(prefers-reduced-motion: reduce)').matches` in a
read-only inspection. Hover and press a regular button and a `.button` link: their
computed transform should remain none and their bounds should not shift. Background,
shadow and focus feedback should remain visible. Repeat with the preference off to
check the ordinary 1px hover/2px press behavior, allowing more specific component rules.
Check modal/toast centering and graph zoom separately; layout transforms are preserved.
This is a manual preference regression, not covered by npm test or the contrast checker.

## Workspace skip navigation

Open an authenticated workspace in a fresh document. The first Tab should expose
‘본문으로 건너뛰기’. Enter focuses the current page's h1; URL/query/hash must remain
unchanged. Next Tab continues at page controls instead of the sidebar. Repeat after
scrolling down, with a filtered/bookmarked list, and at narrow widths/zoom. The main
landmark's aria-labelledby points to that h1. Open a modal without submitting: the
skip link must inherit background inert, and Escape restores its previous inert state.
DOM associations and keyboard focus do not prove actual screen-reader announcements.

## Real document viewport review

Build the frontend first (`npm --prefix web run build`), then launch a separate loopback
QA server against an isolated workspace:

```sh
.venv/bin/python scripts/responsive_review.py --data-dir artifacts/mobile-qa --port 8811
```

Use a copied QA database or set up the new workspace and authenticate at
`http://localhost:8811/` before opening `http://localhost:8811/responsive-review` in the
same browser. The existing workspace lease applies; do not share a data directory with
another running server. Add `--finding-id ID --task-id ID` to enable the two detail
buttons. Add `--lab` only for owned local lab assets. The tool never automatically runs
scans or submits changes. Product controls in the embedded app retain their real actions.

The controls select actual iframe document widths of 320, 390, 768 and 1280 CSS pixels.
Displayed metrics originate in that app document: viewport width, root client/scroll
width, heading, dialog width, and selected controls/sections outside the viewport.
`containedOverflow` counts elements inside an ancestor with horizontal scrolling and
is separate from uncontained overflow. It is not a comprehensive visual/accessibility
checker: overlap, clipped text, touch targets, scroll reachability and responsive dialogs
need visual/manual review. No mobile browser/device/zoom emulation is performed.

This server intentionally changes frame-ancestors to self and removes X-Frame-Options
so the diagnostic page can embed the actual built app. It inserts a same-origin DOM
metrics script in that app HTML. These overrides exist only in this manually launched
QA entry, bound to 127.0.0.1; they are not in create_app, the normal launchers, Vite's
production entry or the production bundle. Authentication and operation checks remain.
Use isolated QA data and stop this server after review. This fixture is not an npm test.

## API policy editor component widths

Run `npm --prefix web run dev -- --port 8812 --strictPort`, then open
`http://127.0.0.1:8812/tests/browser/policy-editor-review.html`.
The 320/390/768 buttons resize the actual document containing the production policy
editor and stylesheet, with one explicitly synthetic rule including schema/ownership.
It makes no API/target requests and is outside the production entry. The frame's form
prevents submission; this fixture cannot prove persistence or server error recovery.

Check column stacking, labels, textarea/fieldset overflow, and reachability by scrolling
the frame. The displayed metrics include selected textarea, fieldset and legend bounds.
They do not prove clipping, touch/zoom behavior or real phone compatibility. For input
and keyboard checks, open `policy-editor-frame.html` directly: add/delete rules, toggle
optional fields, switch form/JSON, and try invalid schema or unsupported rule fields.
Full registration, error/retry, native select interaction, 20-rule workload and assistive
technology require separate real-app review.

## Built-app session replacement during pending saves

Build the frontend, then run `.venv/bin/python scripts/review_session_ui.py --port 8811`.
Open `http://127.0.0.1:8811/`. This launcher creates disposable users `admin` and
`operator`, both with synthetic password `owned-session-ui-password-only`. It removes
inherited AEGIS settings and never opens existing data or executes target checks.
The injected QA controls are outside the production bundle. Notes really persist on
the local server; only successful POST acknowledgments are held. Other HTTP/auth/SSE
remain real. Stop the launcher to remove all temporary data.

1. Log in as admin, open Workspace → Write note and save. Confirm one held reply
   and disabled saving button. With the modal focused, F9 invokes server logout.
   Wait for the app's real periodic read to receive 401 and show Login.
2. Log in as operator. User management must be absent. Note creation and logout
   must be enabled even though the old acknowledgment remains pending.
3. Open a new note, enter a different title/body and save. Confirm two held replies.
   F8 releases the oldest reply. New modal/input must remain and saving stay disabled;
   no old completion toast or records-changed event should appear.
4. F8 releases the current reply. Dialog closes, records-changed becomes one and
   controls unlock. Product Logout returns to Login.

QA shortcuts work inside the modal; normal background inert still applies. Reload
loses held client acknowledgments but retains committed notes until server shutdown.
This checks one document's real cookie/session replacement and pending note save,
not cross-tab/phone/tenant isolation or every mutation. It does not cancel committed writes.

## Submission input locking and failure recovery

The same built-app fixture can hold a note save to inspect its actual input state.
After submitting, native title/body controls must match `:disabled`, the form exposes
aria-busy true, and a separate status explains that input is locked until completion.
F8 can be pressed with Close focused to release the reply; inputs are disabled, so
do not send that key through a disabled textbox. Cancel/Close remain available and
retain the existing closed-view completion behavior.

For failure recovery, open a new note and enter a title/body. F7 makes the next note
POST return a synthetic 503 **before any server request**. Save must leave the modal,
both values and the error visible, with aria-busy false and inputs enabled. Edit and
resubmit, confirm inputs lock again, then F8 completes the actual successful save.
The rejected fixture request must not create a note. This is transport fault injection,
not a real server outage, and does not certify every registration form or mobile state.

## Authentication submission and recovery

Open the disposable launcher at `/?hold_auth=1`. Additional controls submit the
actual authentication form twice synchronously via native requestSubmit and release
the oldest authentication response. The wrapper records only request/pending counts,
never credentials or cookies, and sends real login/setup requests to the local server.

Enter admin and a wrong synthetic password of at least 12 characters. Click the burst
control: exactly one HTTP request must appear, both inputs disable, form aria-busy is
true and progress status appears. Release the real 401 response: inputs enable,
error appears and the form describedby resolves to that error. Correct the password
and repeat; one additional request should enter. Release to reach the workspace,
then test product Logout. The synchronous burst checks the latch before React's
disabled-button update; it is stronger than two sequential clicks on a disabled button.

For first setup, run a separate empty fixture with
`.venv/bin/python scripts/review_session_ui.py --port 8813 --setup` and open
`http://localhost:8813/?hold_auth=1`. Enter a synthetic admin/password, leave the local
setup token blank and burst-submit. One setup request, all three disabled inputs and
successful administrator workspace after release are expected. This does not test
remote token configuration/errors, real credential providers or every mobile/AT flow.

## Planner usage statuses and narrow documents

Run Vite on port 8812 and open `/tests/browser/planner-usage-review.html`. It imports
production PlannerUsage and styles with synthetic reported/partial/missing/invalid
calls, including a rejected plan and unavailable response. No API/provider calls occur.
Select 320/390/768, then Measure: root client/scroll width should match the requested
actual iframe document. Check labels, unknown counts and total mismatch remain
readable and wrapped. This is component/manual document QA, not real mobile/AT or a
complete backend/task-detail user journey. The fixture is outside production entry.

## Usage aggregate recovery and widths

The combined card now also displays synthetic flat token-price estimates. All-source
cost USD 18915118434956.081107, planner 18915118434956.0811 and conversation
0.000007 must preserve all decimals; empty/missing periods have no calculated totals.
Source delay/release and 503/retry must preserve both tokens and cost for the current
selection. These are synthetic prices, not actual provider charges.

The planner usage fixture includes one synthetic price quote with a long source URL.
In `?frame=1`, Enter/Space on the native price summary must open/close its proof.
On the outer page, the owned "문서 가격 근거 펼침" button toggles the iframe's native
details to allow measuring its opened 320/390/768 documents. No URL is fetched.
Actual AI UI + synthetic prices: start review_conversation_ui.py with
`--ai-fixture --price-fixture`. Accepted/invalid-citation calls each report 20/10/30
tokens and should estimate USD0.00005 at the fixture 1.25/2.5 per-million rates.
HTTP503 must show unknown cost. After those three questions, system settings should
show estimated2/unknown1 and USD0.0001. All fixture URLs/rates are synthetic.

Open `/tests/browser/usage-summary-review.html?frame=1` on Vite 8812 for the production
UsageSummary with synthetic fetch only. Default combined total 18,915,118,434,956,081,105 must
retain all digits. Arm Next delay, Refresh and inspect loading/disabled refresh;
Release restores data. Arm Next error, Refresh, then Retry must recover.
Use the combobox locator `selectOption('7')`, `selectOption('30')`, and
`selectOption('')` to select recent 7 days, recent 30 days, and all records. The empty
7-day result has zero calls and unknown token totals; 30 days has one missing-only
call and unknown totals. All records restores the exact large total above. Select source planner for the
original 18,915,118,434,956,081,100 total or conversation for 5. Delay a planner
source request, switch to conversation and release: conversation must stay selected
and keep 5. The source/period label in the fixture status identifies each request.
Next previous-server response returns metadata without source/source_counts; the
component must show a version compatibility error instead of crashing or showing
planner-only data as combined usage. Refresh must recover under the same selection.
The fixture status shows held request periods/status codes and the last six requests.
Arm Next delay, select 7, confirm `all/7 HTTP 200` is pending, select 30, wait for its
result, then Release: the 30-day selection and result must remain. Arm Next error
and Next delay, select 7, confirm `all/7 HTTP 503` is pending, select all, wait for its
result, then Release: the all-period result must remain without an alert.
Select 30, arm Next error, Refresh, then Retry: both error and recovered data must
retain the 30-day selection. These semantic browser selections and response-order
sequences were executed; hardware keyboard, mobile touch and screen-reader picker
journeys still require verification. Avoid fixture edits/HMR while responses are held.
Open without frame query to measure actual 320/390/768 documents. No API/provider
requests occur and the fixture is outside the production entry.

## Recorded conversation provenance

Open `/tests/browser/message-provenance-review.html?frame=1` on Vite 8812.
The fixture imports production MessageProvenance and automatically opens the native
details for width review. Its task and finding IDs are synthetic and have no backend
records. Test Enter to collapse/reopen, inspect task/finding links and the historical
values, and verify the legacy answer has no fabricated provenance. Open without the
frame query for real 320/390/768px document widths with long titles/remediation.
The fixture also displays a capped synthetic observation excerpt (literal script
text), truncation notice and a finding with missing evidence. Vertical document
scrollbars reduce the root client width by 15px; compare client/scroll widths.
Only the owned built-app review can verify actual persisted exchanges and link
destinations; this component fixture makes no API/provider requests.

For that actual HTTP/UI journey, run `python scripts/review_conversation_ui.py` after
building the UI. It starts a fresh disposable workspace on loopback 8811, prints its
synthetic credentials and seeds explicitly synthetic observations, including missing
proof and a long literal excerpt. Submit a summary question, open its provenance,
confirm missing/truncated notices, follow the evidence link, and inspect its one-item
filtered source list and full original. Reopen the task in a fresh document to check
persisted excerpts. Ctrl+C shuts down and removes the workspace. The launcher does
not approve tasks or send target/provider requests; synthetic seeded observations
are not execution evidence. Backend loopback integration verifies actual check output.

Use `--ai-fixture` to enable an owned loopback Chat Completions provider (lab mode).
Select AI draft explicitly, inspect the transmission notice, and submit a normal
question: a cited synthetic draft with reported 20/10/30 usage is saved. Questions
containing `잘못` return a foreign citation and must recover to recorded rules while
retaining reported usage; `실패` returns HTTP 503 and must recover with unknown usage.
Open a fresh task document to inspect all saved replies. This fixture never contacts
a commercial provider or executes targets. Check the vertically stacked mode,
notice, question and submit controls in the built UI; whole mobile/AT QA is separate.


## Durable AI attempt ledger

Run the disposable launcher with `--ai-fixture --price-fixture --ledger-fixture`.
Only this temporary workspace/provider is affected: `세션 폐기` in a question revokes
fixture sessions during a successful synthetic response; log back in and compare
persisted vs attempt aggregates. `저장 실패` returns provider HTTP200 but fails the
exchange write. It takes precedence over the generic provider-503 `실패` trigger.
The original messages must remain absent, while attempts retain observed20/10/30
and estimated USD0.00005. Synthetic quotes require no commercial provider.
Unconfirmed AI retry explains that a new call can incur additional cost.

On `usage-summary-review.html?frame=1`, switch 집계 기준 to 호출 시도 기록.
Hold a persisted request, change the ledger, then release it: stale results must not
replace the selection. Test 503/retry, and 다음 시도 미지원 응답 + 새로 조회:
valid source fields with missing ledger/state fields must show compatibility error.
Retry must recover without changing the selected ledger. Without `frame`, width
buttons measure the default persisted aggregate with the added selection controls;
320/390/768px documents are not whole mobile/touch/screen-reader coverage.


## Individual provider attempts

Open `call-history-review.html?frame=1&page=settings` on the local Vite server.
It imports production CallHistory, navigation and useRecords with29 explicitly
synthetic records; it does not contact a provider or execute targets. Check the
25-row page, next page26–29, fresh-document URL restoration and filter reset.
Enter/Space opens native call details and price proof. Interrupted unknown usage
must say 미확인, not zero or a fabricated response observation time. Test delayed
prior responses using the visible 보류된 조회 counter; change state before releasing
and verify the selected state/list stays current. 서버 오류 유지 keeps503 across
periodic refreshes; the last list must show an alert, then 서버 복구 + 최신 목록
recovers without clearing filters. Back/Forward uses production history handling.
Open without `frame` for320/390/768 document widths; 문서 상세 펼치기 opens all
native details, including long price sources, before measuring. These documents
are component geometry checks, not whole mobile or screen-reader coverage.

For the real HTTP journey use the disposable conversation launcher with
`--ai-fixture --price-fixture --ledger-fixture`. Save a normal AI reply, then ask a
question containing 저장 실패. Settings must show one committed and one uncommitted
call with distinct IDs. Open details/quote, filter uncommitted, reopen its URL and
follow 작업 보기. The seeded observations and quoted prices are synthetic; the
attempts are generated by actual owned HTTP provider requests. No commercial
billing proof or arbitrary target execution is produced.


## Worker process in the built app

Build the frontend and run `python scripts/review_observation_ui.py --next-plan
--worker-process --worker-fail-flag artifacts/worker-process-ui-fail.flag` on8815.
Use the disposable fixture admin documented by that script and open
`?page=tasks&detail=task&detail_id=qa-source-task`. Under Worker 실행 과정 select
qa-asset and query: two coverage cells,32 events and61 observations. Event next
page shows26–32; observation search owned-link-59 returns one item. The legacy
Worker event is unconfirmed. Select qa-parent-asset: prior records disappear before
query, then two completed cells, one parent event and no observations. These are
synthetic records, not proof of actual execution.

Create the owned flag to make Worker GET return503; query shows an alert and focuses
Worker 과정 조회. Remove it and query again. Use the fixture's /qa-frame width320/390
and its visible 너비 검사 button to inspect actual document/dialog dimensions;
result tables intentionally scroll internally. Close only owned tabs, stop the fixture
and verify its zero-target/zero-creation counters and temporary directory cleanup.
This is manual built UI QA, not coverage provided by npm test or physical-device QA.
