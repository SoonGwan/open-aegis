# Contributing

Python 3.11+ and Node.js 22 are used for development.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.lock
.venv/bin/pip install --no-deps -e .
.venv/bin/python -m pytest -q
cd web
npm ci
npm test
npm run build
```

For hot reload, run `.venv/bin/python -m aegis` in the repository root and
`npm run dev` in `web/`. The Vite proxy defaults to backend port 8787.
The production UI is served by the Python backend after a frontend build.

## CI and installed package review

The Verify workflow uses Python 3.11 and Node.js 22, locked runtime/dev dependencies,
frontend tests/build, backend tests and selected design contrast/token checks. It also
builds a wheel and rehearses it outside the checkout in a fresh virtual environment.
Run the package stage locally from the repository root after building the frontend:

```sh
.venv/bin/python scripts/check_design.py
.venv/bin/python -m pip wheel --no-deps . --wheel-dir artifacts/ci-wheel
.venv/bin/python scripts/review_runtime_package.py --wheel-dir artifacts/ci-wheel --web-dir web/dist --runtime-lock requirements.lock
```

Use a wheel directory containing exactly one Open Aegis wheel. The review installs
locked runtime dependencies (network access to the package index is required), checks
dependency consistency and CLI entry points, starts the installed server on an inherited
loopback socket, and exercises authentication, synthetic asset/pending-plan persistence,
separately built UI assets, runtime metrics and audit verification. It never approves a
scan or requests a target. It removes inherited AEGIS settings and Python path overrides.
Shutdown must finish the app lifespan and release the workspace lease. The existing
installed backup/restore/audit rehearsal runs afterwards. Temporary installations and
synthetic databases are removed on exit. This POSIX review supports Linux/macOS; Windows
uses WSL or a container, consistent with the workspace-lock implementation.

The wheel contains the Python backend/CLI, not the frontend bundle. Its UI is supplied
explicitly via AEGIS_WEB_DIR for this review; Docker packages the separately built UI.
Build dependencies, runner images and Python/Node patch versions are not fully pinned,
so this is behavior verification rather than a byte-reproducible or signed release.
Action references use full official commit SHAs, checkout credentials are not retained,
the token is read-only and the job has a 15-minute limit. The hosted workflow still needs
an actual run on the published repository; local review does not prove a GitHub job ran.
Docker execution, whole UI accessibility/mobile coverage and release signing remain
separate gates in [V1-READINESS.md](docs/V1-READINESS.md).

## New checks

Register a named check in `aegis/checks.py`, implement it in `run_check`, and
add behavioral tests against a loopback synthetic fixture. Use `Transport`
for every target request. Do not open a second unguarded network transport.
Preserve explicit scope, request limits, cancellation, and metadata redaction.
Report configuration observations separately from confirmed policy failures.

Include a finding that is observed before a fixture change and absent after
the change. Verify that connection errors do not falsely resolve it.
Never add real customer data, production tokens, arbitrary shell execution,
or live third-party scans to tests.

## Pull requests

Describe the user-visible behavior, reproduction, and validation. Screenshots
help for UI changes. Keep generated databases, local artifacts, credentials,
and virtual environments out of Git.
