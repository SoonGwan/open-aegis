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
