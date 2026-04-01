#!/bin/sh
set -eu

echo "Waiting for database to be ready..."
attempt=1
max_attempts=20
until python -c "from app.db.session import engine; engine.connect().close()" 2>/dev/null || [ "$attempt" -ge "$max_attempts" ]; do
  echo "Database not ready, retrying in 3 seconds (attempt $attempt/$max_attempts)..."
  attempt=$((attempt + 1))
  sleep 3
done

if [ "$attempt" -ge "$max_attempts" ]; then
  echo "ERROR: Database never became ready. Exiting."
  exit 1
fi

echo "Running database migrations..."
if ! python -m alembic upgrade head; then
  echo "ERROR: Migrations failed. Exiting."
  exit 1
fi

RUNTIME_PORT="${PORT:-${APP_PORT:-8000}}"
echo "Starting FastAPI on port ${RUNTIME_PORT}..."
exec uvicorn main:app --host 0.0.0.0 --port "${RUNTIME_PORT}"