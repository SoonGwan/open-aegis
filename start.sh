#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null || ! command -v npm >/dev/null; then
  echo "Python 3.11+ and Node.js 20.19+ / 22+ are required."
  exit 1
fi
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
(cd web && npm ci && npm run build)
exec .venv/bin/python scripts/run.py
