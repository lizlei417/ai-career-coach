#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo 'Create .venv and install requirements.txt first. See README.md.'
  exit 1
fi
if [[ ! -f frontend/dist/index.html ]]; then
  (cd frontend && npm ci && npm run build)
fi
exec .venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port "${PORT:-8765}" --no-access-log
