# Cloudflare publication — 2026-10-07

The landing from source `fb280fc86582538c3e634555a470e9d21253bceb` is publicly
hosted at [aegis.no-money-do-you-have-money.com](https://aegis.no-money-do-you-have-money.com/),
with [English](https://aegis.no-money-do-you-have-money.com/en/).
The deployment script completed successfully and retained phase `live`.

Anonymous public HTTPS checks at13:55:33 UTC verified10 responses with status200
and exact deployed-file bytes: root/index, Korean alias, English, CSS, screenshot,
favicon, robots, sitemap and release health. Health identifies `open-aegis-landing`
and the source above. Hidden `.env`, `.git/config`, directory listing, application
API and server-source routes return404. A separate disposable-origin boundary
check rejects encoded traversal and escaping file/directory symlinks; its server,
thread and temporary files were cleaned up.

The actual public browser passed Korean→English→Korean language switching,
English canonical URL, zero broken images, FAQ expansion and the1.0.0 release
link. Local desktop review passed the install anchor and FAQ; owned390px Korean
and320px English iframe layouts were visually reviewed. This is bounded layout
review, not full physical-mobile or screen-reader coverage. A sandboxed iframe DOM
measurement was unavailable, so no numeric scroll-width assertion is claimed.
Both temporary preview servers and the owned review tabs were closed after review.

Dedicated web/tunnel LaunchAgents are running. Existing moneybook and
questionable-hires web/tunnel services also report running. The repository
homepage and both README website links now point to the new primary domain.
GitHub Pages workflow37632229890 at the same source completed successfully;
the earlier GitHub Pages URL remains available.

This publishes the static introduction, not the security workspace backend.
The Mac must stay awake, logged in and connected, following the
[deployment contract](LANDING-HOSTING.md).
Local command logs, public hashes and checks are retained in
`artifacts/cloudflare-landing-*`. This site-only work changes no application
modules, operational databases, dependency locks or signed1.0.0 release assets.
