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

This fixture is a manual browser regression, not part of `npm test`. Full mobile, assistive
technology and all workspace journeys require separate verification.

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
