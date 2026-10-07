# Cloudflare landing hosting

The primary project website uses the same macOS LaunchAgent + locally managed
Cloudflare Tunnel setup as `SoonGwan/questionable-hires`. The shared `site/`
sources also remain publishable by the existing GitHub Pages workflow.

- Domain: `https://aegis.no-money-do-you-have-money.com/` (Korean)
- English: `/en/`; Korean alias: `/ko/`
- Origin: `127.0.0.1:4190`
- App/tunnel identity: `open-aegis-landing`
- Services: `com.open-aegis.landing.web`, `com.open-aegis.landing.tunnel`

Only the generated static landing directory is served. The application console,
API, operational records and repository are installed/operated separately.

## Deploy and verify

Requires macOS, Python3, `cloudflared`, a signed-in macOS user session and existing
`cloudflared tunnel login` credentials. Commit the reviewed source, then run:

```sh
python3 -B scripts/deploy_landing_mac.py
```

The command builds Korean/English HTML, shared assets, canonical/OG/hreflang URLs,
robots and sitemap for the actual HTTPS domain. It copies only those public files
and the static server to a dated release, atomically selects `current`, and checks
local `/_health` app/revision before connecting the dedicated tunnel. It adds DNS
with `--overwrite-dns=false`, then checks the same revision over public HTTPS.
No existing moneybook or questionable-hires services/configuration are changed.

Cloudflare credentials remain in `~/.cloudflared/`. Releases and deployment phase
are retained under `~/Library/Application Support/open-aegis-landing/`; logs are
under `~/Library/Logs/open-aegis-landing/`. No credentials are committed or served.
A failed public check is an incomplete deployment, even if local health passed.

The static origin rejects hidden paths, traversal, directory listings and
symlinks escaping its root. It binds only to loopback, uses a restrictive CSP,
`nosniff` and `no-cache` headers. Only `/_health` reports release metadata.
The dedicated ingress accepts the landing hostname and uses a final404 fallback.

## Update and rollback

Commit changes and rerun the command. Previous release files remain available.
To restore the preceding release using the same domain and port:

```sh
python3 -B scripts/deploy_landing_mac.py --rollback
```

The script restores the previous origin if new local startup fails. A public
DNS/tunnel failure retains its phase for diagnosis rather than claiming success.
The LaunchAgents restart crashed processes and start at user login. The Mac must
remain awake, logged in and connected; this is the existing Mac-origin model,
not an always-on cloud origin. See [Cloudflare's macOS service documentation](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/local-management/as-a-service/macos/).

Scripts `deploy_landing_mac.py` and `serve_landing.py` are adapted from
[SoonGwan/questionable-hires](https://github.com/SoonGwan/questionable-hires)
under MIT, copyright2026 SoonGwan. The project MIT license retains that notice.

[Verified publication on2026-10-07](LANDING-HOSTING-2026-10-07.md).
