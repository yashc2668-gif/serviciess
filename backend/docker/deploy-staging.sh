#!/bin/sh
set -eu

if [ ! -f ".env.staging" ]; then
  echo ".env.staging is missing"
  exit 1
fi

set -a
. ./.env.staging
set +a

echo "Deploying staging stack..."
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --build

echo "Checking staging health..."
curl -fsS "${STAGING_BASE_URL:-http://127.0.0.1:8000}/health/ready" >/dev/null

echo "Checking current Alembic revision..."
docker compose -f docker-compose.staging.yml --env-file .env.staging exec -T backend python -m alembic current

if [ "${RUN_DEMO_SEED:-true}" = "true" ]; then
  echo "Seeding demo/UAT data..."
  docker compose -f docker-compose.staging.yml --env-file .env.staging exec -T backend python -m app.db.demo_seed
fi

echo "Running post-deploy verification..."
chmod +x docker/verify-staging.sh
./docker/verify-staging.sh

echo "Staging deploy completed."
