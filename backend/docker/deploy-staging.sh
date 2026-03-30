#!/bin/sh
set -eu

if [ ! -f ".env.staging" ]; then
  echo ".env.staging is missing"
  exit 1
fi

set -a
. ./.env.staging
set +a

compose() {
  docker compose -f docker-compose.staging.yml --env-file .env.staging "$@"
}

wait_for_ready() {
  attempts="${1:-20}"
  delay_seconds="${2:-5}"
  count=1

  until curl -fsS "${STAGING_BASE_URL:-http://127.0.0.1:8000}/health/ready" >/dev/null
  do
    if [ "${count}" -ge "${attempts}" ]; then
      echo "Staging readiness check failed after ${count} attempts."
      exit 1
    fi

    echo "Readiness attempt ${count} failed, retrying in ${delay_seconds}s..."
    count=$((count + 1))
    sleep "${delay_seconds}"
  done
}

if [ "${RUN_PREDEPLOY_BACKUP:-false}" = "true" ]; then
  RUNNING_DB_CONTAINER="$(compose ps -q db || true)"
  if [ -n "${RUNNING_DB_CONTAINER}" ]; then
    echo "Running pre-deploy backup..."
    chmod +x docker/backup-compose-postgres.sh
    COMPOSE_FILE=docker-compose.staging.yml \
    ENV_FILE=.env.staging \
    BACKUP_ROOT="${BACKUP_ROOT:-backups}" \
    INCLUDE_UPLOADS="${BACKUP_UPLOADS:-true}" \
    ./docker/backup-compose-postgres.sh "${PREDEPLOY_BACKUP_LABEL:-predeploy-$(date -u +%Y%m%dT%H%M%SZ)}"
  else
    echo "Skipping pre-deploy backup because no existing db container is running."
  fi
fi

echo "Deploying staging stack..."
compose up -d --build

echo "Checking staging health..."
wait_for_ready 24 5

echo "Checking current Alembic revision..."
compose exec -T backend python -m alembic current

if [ "${RUN_DEMO_SEED:-true}" = "true" ]; then
  echo "Seeding demo/UAT data..."
  compose exec -T backend python -m app.db.demo_seed
fi

echo "Running post-deploy verification..."
chmod +x docker/verify-staging.sh
./docker/verify-staging.sh

echo "Staging deploy completed."
