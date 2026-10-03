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
