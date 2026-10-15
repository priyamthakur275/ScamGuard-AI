#!/bin/sh
# Start script for the app_service container (Render).
#
# Runs database migrations, then starts the API. If the configured database
# cannot be reached (for example a free Render PostgreSQL instance that has
# expired or been suspended), the service does not crash-loop: it logs the
# problem loudly and starts on a local SQLite file instead, so the site keeps
# working for demos. Data stored in that fallback is lost whenever the
# container restarts; fix DATABASE_URL to get persistent storage back.
set -u

if alembic upgrade head; then
    echo "[start] migrations applied to the configured database"
else
    echo "[start] ERROR: could not migrate the configured DATABASE_URL (database unreachable, expired or misconfigured)." >&2
    echo "[start] Falling back to a temporary SQLite database. Accounts and scans will NOT survive a restart." >&2
    export DATABASE_URL="sqlite:////tmp/scamguard-fallback.db"
    export SCAMGUARD_DB_FALLBACK=1
    alembic upgrade head || { echo "[start] fallback migration failed" >&2; exit 1; }
fi

exec uvicorn app_service.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${UVICORN_WORKERS:-1}"
