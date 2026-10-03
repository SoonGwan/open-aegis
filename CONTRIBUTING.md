# Contributing

Python 3.11+ and Node.js 22 are used for development.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.lock
.venv/bin/pip install --no-deps -e .
.venv/bin/python -m pytest -q
cd web
npm ci
npm run build
```

For hot reload, run `.venv/bin/python -m aegis` in the repository root and
`npm run dev` in `web/`. The Vite proxy defaults to backend port 8787.
The production UI is served by the Python backend after a frontend build.

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
