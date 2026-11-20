#!/usr/bin/env bash
# Serve the bundled frontend and API with the project's Python environment.
set -eu
cd "$(dirname "$0")"
if [[ ! -f frontend/dist/index.html ]]; then
  ( cd frontend && npm ci && npm run build )
fi
cd backend
if [[ ! -x .venv/bin/python ]]; then
  "${PYTHON:-python3}" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else "Python 3.10+ required. Set PYTHON to its executable.")'
  "${PYTHON:-python3}" -m venv .venv
fi
.venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
exec .venv/bin/python -m uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
