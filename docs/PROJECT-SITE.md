# Project introduction website

The `site/` directory contains a static English/Korean introduction, an existing
owned-fixture console screenshot, installation commands and links to the project
contracts. It presents version 1.0.0 and links to implementation
status, release validation and remaining work. The security workspace is installed
and operated separately.

The pages use local CSS and an image, with no JavaScript, forms, account collection,
analytics or external font loading. Responsive CSS includes narrow-screen layouts,
visible keyboard focus, a skip link and reduced-motion handling. Desktop browser
review covers the English hero/install anchor, language switching and Korean hero.
Owned desktop iframe fixtures review English at320/390px and Korean at320/768px.
These are narrow document layout checks, not mobile-device or screen-reader tests.
Both pages' local resources, section anchors and repository documentation links
are checked against their actual files. Source secret scanning reports no findings.

The separate `Project website` workflow publishes only `site/` from `main` to
GitHub Pages. Official actions are pinned to full revisions. GitHub Pages must be
configured to use Actions before the initial manual dispatch. It does not upload
application data, ignored artifacts, a server executable or the entire checkout.
The deploy job has Pages/OIDC permissions and uses the `github-pages` environment;
it does not deploy from pull requests or other branches. A successful deployment
and independent public HTTP/asset checks are required before claiming publication.

The introduction is published at[soongwan.github.io/open-aegis](https://soongwan.github.io/open-aegis/),
with[Korean](https://soongwan.github.io/open-aegis/ko.html) and English pages.
Initial manual workflow37408139703 atmainac97ace completes successfully. Public
HTTPS200 responses for root/index/Korean/CSS/dashboard image match the reviewed
files byte-for-byte; live browser language switching also passes. This publication
does not host the security application's backend.

The version 1.0.0 update at main 79222383a6aa55cb3e07f0fd7151c1d3aec1bb79
passed Pages workflow 37414561869. Anonymous HTTPS200 downloads of root/index,
Korean HTML, CSS and the image match the source bytes. The separate
[v1.0.0 release](https://github.com/SoonGwan/open-aegis/releases/tag/v1.0.0)
is published with signed installable files; the website remains static documentation.

## Cloudflare primary domain

The shared source now also builds a Korean-default landing for
`aegis.no-money-do-you-have-money.com`, with English at`/en/`, release download,
signed-install guide, FAQ, favicon and canonical/OG/hreflang metadata. See the
[Mac/Cloudflare deployment contract](LANDING-HOSTING.md). GitHub Pages remains
available; public Cloudflare deployment verification is recorded separately.
