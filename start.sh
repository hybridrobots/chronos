#!/usr/bin/env bash
# Chronos — local startup for the living multiverse organism
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/node/bin:${PATH}"

# Backend venv
if [[ ! -d backend/.venv ]]; then
  echo "[chronos] Creating Python virtualenv..."
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -r backend/requirements.txt
fi

# Frontend deps
if [[ ! -d frontend/node_modules ]]; then
  echo "[chronos] Installing frontend dependencies..."
  (cd frontend && npm install)
fi

# Build frontend if dist missing or src newer
NEED_BUILD=0
if [[ ! -f frontend/dist/index.html ]]; then
  NEED_BUILD=1
elif find frontend/src -newer frontend/dist/index.html | grep -q .; then
  NEED_BUILD=1
fi
if [[ "$NEED_BUILD" == "1" ]]; then
  echo "[chronos] Building frontend..."
  (cd frontend && npm run build)
fi

mkdir -p data logs

MODE="${1:-prod}"

cleanup() {
  echo
  echo "[chronos] Shutting down..."
  [[ -n "${BACK_PID:-}" ]] && kill "$BACK_PID" 2>/dev/null || true
  [[ -n "${FRONT_PID:-}" ]] && kill "$FRONT_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [[ "$MODE" == "dev" ]]; then
  echo "[chronos] Starting backend (dev) on :8000 ..."
  (cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) &
  BACK_PID=$!
  echo "[chronos] Starting frontend Vite on :5173 ..."
  (cd frontend && npm run dev -- --host 127.0.0.1 --port 5173) &
  FRONT_PID=$!
  echo
  echo "  Living Universe UI → http://127.0.0.1:5173"
  echo "  API / WebSocket    → http://127.0.0.1:8000"
  echo
  wait
else
  echo "[chronos] Starting organism on :8000 (serves built UI)..."
  echo "  Open → http://127.0.0.1:8000"
  echo
  cd backend
  exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
fi
