#!/bin/sh
set -eu

echo "Applying database migrations..."
attempt=1
until python -m alembic upgrade head
do
  if [ "$attempt" -ge 10 ]; then
    echo "Migrations failed after ${attempt} attempts."
    exit 1
  fi

  echo "Migration attempt ${attempt} failed, retrying in 3 seconds..."
  attempt=$((attempt + 1))
  sleep 3
done

echo "Starting FastAPI on port ${APP_PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${APP_PORT:-8000}"
