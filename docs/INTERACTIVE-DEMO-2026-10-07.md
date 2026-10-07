# Demo publication — 2026-10-07

The [public interactive demo](https://aegis.no-money-do-you-have-money.com/demo/)
is deployed from `ed4c89a09e1c330d4c95c2f41633f7d67d072b07` through the existing
Mac/Cloudflare release switch. The deploy command exited0 and retained phase
`live`; the preceding landing release remains available for rollback.

At14:26:00 UTC,15 anonymous HTTPS200 responses matched the deployed files exactly:
landing routes/assets/discovery/health, demo HTML including the English query
entry, JavaScript, state module and CSS. Five hidden/source/API/listing routes
returned404. The public `.mjs` response uses `text/javascript`, `nosniff`, and a
CSP with own-origin scripts and `connect-src 'none'`.
GitHub Pages workflow37636441827 at the same source completed successfully.
The application Verify workflow is a separate run; this record does not claim
its full suite completed from the Pages result.

Actual public browser actions passed landing→demo, plan creation, approval,
sample execution, three findings, remediation, pending retest and separate retest
approval. The resulting open-finding count is2. The original response text
matches the captured pre-retest text exactly, and the new response includes
`X-Content-Type-Options: nosniff`. Switching to English retains that result;
entering from the English landing selects English and starts a fresh session.

Local browser checks also passed execution cancellation, fresh-plan continuation,
reset while a sample callback was pending and isolated tabs. Reset remained at
zero completed checks/findings after the old callback window.390px Korean and
320px English desktop iframe layouts were visually reviewed, including the
adjusted narrow header. This is not full mobile/screen-reader coverage.

All5 meaningful state tests passed on Node22.18.0 (0 failures/skips). Static build
checks resolved links/resources in six generated HTML routes, verified module
bytes and landing demo links, and found no workflow network/storage API use.
Disposable build/origin fixtures and both owned local preview servers were
cleaned up; owned review tabs were closed after public review.

The demo is the labelled browser-only sample described in
[INTERACTIVE-DEMO.md](INTERACTIVE-DEMO.md). It does not expose the real scanner,
application API, model credentials or operational data. Local receipts and logs
are retained under `artifacts/demo-*`. Application modules, runtime dependency
locks, existing operational data and the signed1.0.0 assets are unchanged.
