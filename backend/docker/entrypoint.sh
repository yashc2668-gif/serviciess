#!/bin/sh
set -eu

echo "Attempting database migrations..."
attempt=1
until python -m alembic upgrade head
do
  if [ "$attempt" -ge 10 ]; then
    echo "WARNING: Migrations failed after ${attempt} attempts. Starting app anyway for healthcheck."
    break
  fi

  echo "Migration attempt ${attempt} failed, retrying in 3 seconds..."
  attempt=$((attempt + 1))
  sleep 3
done

RUNTIME_PORT="${PORT:-${APP_PORT:-8000}}"
echo "Starting FastAPI on port ${RUNTIME_PORT}..."
exec uvicorn main:app --host 0.0.0.0 --port "${RUNTIME_PORT}"
