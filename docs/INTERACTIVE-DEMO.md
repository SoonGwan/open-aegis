# Interactive product demo

[Try the demo](https://aegis.no-money-do-you-have-money.com/demo/) ·
[English](https://aegis.no-money-do-you-have-money.com/demo/?lang=en)

The public demo illustrates a bounded Open Aegis workflow without installation:

1. Inspect the fixed sample asset and its scope.
2. Create a plan and inspect the GET method, request limit and scope boundary.
3. Approve execution separately. Three browser-scheduled sample steps show
   progress and an activity log. Stop preserves completed sample findings;
   continuing requires a new plan and approval.
4. Inspect sample header, cookie and operator-defined CORS-policy findings,
   original requests/responses, reasoning and suggested remediation.
5. Record the header remediation, create a new retest plan and approve it.
   The sample retest resolves one finding while retaining its original evidence;
   the other two findings remain open.

Korean and English share the same session state. Start over cancels pending sample
callbacks and clears the session. New tabs/reloads start fresh; the demo stores no
visitor or target information. `?lang=en` selects English on initial load.

## What the demo executes

The demo is an independent, dependency-free static interface, not the production
console connected to a live scanner. All findings and HTTP responses are clearly
labelled samples. `shop-demo.example` is illustrative; no request is sent there.
The progress timing is a browser animation, not a backend health/scan measurement.
The public website downloads its own HTML/CSS/JavaScript; workflow actions produce
no API, LLM, webhook or external-target calls. It has no credentials or target input.

The demo CSP allows its own scripts/styles, with `connect-src 'none'`, no forms,
no embedded external pages and no inline scripts. Existing landing-page CSP
continues to disallow scripts. The static hosting origin remains separate from
application data, API and operational databases. GitHub Pages serves the same demo
sources, while the Cloudflare builder also emits `/demo/`.

## Verification

`node --test scripts/check_demo_state.mjs` checks actual demo state transitions:
no execution before approval, repeated approval, stale callbacks after reset,
cancel/resume with evidence preservation, separate retest approval and original
proof retention. It uses Node built-ins and adds no dependencies. The Verify
workflow runs it separately from the application suite.

Browser checks cover plan/approve/progress/findings/remediation/retest and
language switching, cancellation/reset and isolated new tabs. Narrow desktop
iframe reviews are bounded layout checks, not full physical-mobile or
screen-reader certification. Public hosting must pass actual HTTPS source-byte
and app/revision checks; local success alone is not publication evidence.

[Public deployment and observed results — 2026-10-07](INTERACTIVE-DEMO-2026-10-07.md).
