#!/usr/bin/env bash
# One command to run ScamGuard locally on macOS / Linux. Same as: python3 run.py
cd "$(dirname "$0")" || exit 1
PY=""
for c in python3.13 python3.12 python3.14 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -z "$PY" ] && { echo "Python 3.10-3.14 is not installed. Get it from https://www.python.org/downloads/"; exit 1; }
exec "$PY" run.py "$@"
