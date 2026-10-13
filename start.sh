#!/usr/bin/env bash
# One command to run ScamGuard locally (macOS / Linux):
#     ./start.sh
# Sets up everything on first run (Python venv + npm packages), frees ports
# 8000/3000, starts the backend and the frontend, waits until both answer,
# and opens http://localhost:3000. Press Ctrl+C to stop both.
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
LOGS="$ROOT/.run-logs"
mkdir -p "$LOGS"

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
info()  { printf "\033[36m==>\033[0m %s\n" "$*"; }

# ---- 1. Tools ---------------------------------------------------------------
PY=""
for c in python3.12 python3.11 python3.13 python3; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -z "$PY" ] && { red "Python 3 is not installed. Install it from https://www.python.org/downloads/ and run ./start.sh again."; exit 1; }
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || { red "Python 3.10 or newer is needed (found $($PY --version))."; exit 1; }
command -v node >/dev/null 2>&1 || { red "Node.js is not installed. Install the LTS version from https://nodejs.org and run ./start.sh again."; exit 1; }
node -e 'process.exit(parseInt(process.versions.node) >= 18 ? 0 : 1)' || { red "Node.js 18 or newer is needed (found $(node -v))."; exit 1; }
info "Using $($PY --version) and Node $(node -v)"

# ---- 2. Free the ports ---------------------------------------------------------
for port in 8000 3000; do
  pids="$(lsof -ti tcp:$port 2>/dev/null || true)"
  if [ -n "$pids" ]; then info "Port $port is busy, stopping the old process"; kill $pids 2>/dev/null; sleep 1; fi
done

# ---- 3. Backend setup (own virtual environment, so system Python is untouched) -
VENV="$ROOT/backend/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  info "Creating the Python environment (first run only)"
  "$PY" -m venv "$VENV" || { red "Could not create a virtual environment."; exit 1; }
fi
REQ_HASH="$(cksum "$ROOT/backend/requirements.txt" | cut -d' ' -f1)"
if [ "$(cat "$VENV/.req-hash" 2>/dev/null)" != "$REQ_HASH" ]; then
  info "Installing backend packages (first run takes 2-4 minutes)"
  "$VENV/bin/python" -m pip install --upgrade pip >"$LOGS/pip.log" 2>&1
  if ! "$VENV/bin/python" -m pip install -r "$ROOT/backend/requirements.txt" >>"$LOGS/pip.log" 2>&1; then
    red "Backend packages failed to install. Last lines of .run-logs/pip.log:"; tail -15 "$LOGS/pip.log"; exit 1
  fi
  echo "$REQ_HASH" > "$VENV/.req-hash"
fi

# ---- 4. Frontend setup ----------------------------------------------------------
if [ ! -d "$ROOT/frontend/node_modules" ] || [ "$ROOT/frontend/package-lock.json" -nt "$ROOT/frontend/node_modules" ]; then
  info "Installing frontend packages (first run takes 1-3 minutes)"
  if ! (cd "$ROOT/frontend" && npm install >"$LOGS/npm.log" 2>&1); then
    red "Frontend packages failed to install. Last lines of .run-logs/npm.log:"; tail -15 "$LOGS/npm.log"; exit 1
  fi
  touch "$ROOT/frontend/node_modules"
fi

# ---- 5. Start both --------------------------------------------------------------
cleanup() { info "Stopping ScamGuard"; kill "${BE:-}" "${FE:-}" 2>/dev/null; exit 0; }
trap cleanup INT TERM

info "Starting the backend on http://localhost:8000"
(cd "$ROOT/backend" && exec "$VENV/bin/python" -m uvicorn app_service.main:app --host 127.0.0.1 --port 8000) >"$LOGS/backend.log" 2>&1 &
BE=$!
for i in $(seq 1 60); do
  curl -s -o /dev/null http://127.0.0.1:8000/api/v1/health && break
  kill -0 $BE 2>/dev/null || { red "The backend stopped while starting. Last lines of .run-logs/backend.log:"; tail -20 "$LOGS/backend.log"; exit 1; }
  sleep 1
done
curl -s -o /dev/null http://127.0.0.1:8000/api/v1/health || { red "The backend did not answer in 60 s. See .run-logs/backend.log"; kill $BE; exit 1; }
green "Backend is up"

info "Starting the frontend on http://localhost:3000"
(cd "$ROOT/frontend" && APP_SERVICE_URL=http://127.0.0.1:8000 exec npx next dev -p 3000) >"$LOGS/frontend.log" 2>&1 &
FE=$!
for i in $(seq 1 120); do
  curl -s -o /dev/null http://127.0.0.1:3000/ && break
  kill -0 $FE 2>/dev/null || { red "The frontend stopped while starting. Last lines of .run-logs/frontend.log:"; tail -20 "$LOGS/frontend.log"; kill $BE; exit 1; }
  sleep 1
done
green "ScamGuard is running:  http://localhost:3000   (Ctrl+C to stop)"
( open http://localhost:3000 || xdg-open http://localhost:3000 ) >/dev/null 2>&1 || true
wait
