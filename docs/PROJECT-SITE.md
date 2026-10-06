# Project introduction website

The `site/` directory contains a static English/Korean introduction, an existing
owned-fixture console screenshot, installation commands and links to the project
contracts. It presents the current pre-release version and links to implementation
status and open release work. It is a project website; the security workspace is
installed and operated separately.

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
