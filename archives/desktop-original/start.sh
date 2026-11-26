#!/usr/bin/env bash
# Build the frontend and serve everything from FastAPI on :8000
set -e
cd "$(dirname "$0")"
( cd frontend && npm install && npm run build )
cd backend
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
