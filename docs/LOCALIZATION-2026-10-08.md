# English-default interface verification — 2026-10-08

The source console now defaults to English, with a persistent Korean language selector.
This update changes frontend presentation, website copy and documentation. Existing
stored evidence and the signed v1.0.0 release assets are not rewritten.

- All 1,744 extracted Korean interface messages have English catalog entries; known
  server tool labels, descriptions and sign-in feedback are also translated at display time.
- Node.js 22 frontend suite: **128 passed**, including six localization checks for
  defaults, invalid/blocked storage, subscriptions, interpolation and lazy label tables.
- TypeScript/Vite production build passed. Vite reports the existing large single
  bundle warning; the translation catalog increases bundle size.
- Five interactive-demo state tests passed. Generated static links and module bytes
  matched, with no target-network or storage APIs in the demo workflow.
- Actual built console browser review used a disposable workspace with three sample
  assets and three unexecuted pending plans. English labels, dates and tool choices
  rendered. Switching an unfinished task form to Korean preserved its entered title
  and original goal. No plan was submitted and no target requests were dispatched.
- Language changes propagated to a second actual console tab. The new selector
  remained visible in a 320-pixel owned iframe review; the header wraps at narrow
  widths. This does not establish a complete mobile journey or zero page overflow.
- Dashboard screenshots were captured from that real console in English and Korean,
  then encoded as JPEG. The screenshot does not depict completed scans or findings.

English README: [README.md](../README.md). Korean README: [README.ko.md](../README.ko.md).
[Translation contribution guide](LOCALIZATION.md).

Stored user content and historical server messages retain their original language.
This is not a claim that every record or every backend error is automatically translated,
that the frozen release includes this new console, or that all mobile journeys were tested.

Public Cloudflare delivery was verified against source `75294f58`: 16 HTTPS routes
matched deployed bytes, and five protected paths returned 404. The English demo
completed approval, evidence, remediation and a separately approved retest in the
actual browser, preserving its original response and two other open sample findings.
[HN submission status](SHOW-HN-STATUS-2026-10-08.md).
