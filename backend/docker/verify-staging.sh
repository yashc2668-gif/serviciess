#!/bin/sh
set -eu

if [ ! -f ".env.staging" ]; then
  echo ".env.staging is missing"
  exit 1
fi

set -a
. ./.env.staging
set +a

BASE_URL="${STAGING_BASE_URL:-http://127.0.0.1:8000}"
DEMO_EMAIL="${DEMO_LOGIN_EMAIL:-demo-admin@example.com}"
DEMO_PASSWORD="${DEMO_LOGIN_PASSWORD:-DemoPass123!}"

echo "Verifying /health..."
curl -fsS "${BASE_URL}/health" >/dev/null

echo "Verifying /health/db..."
curl -fsS "${BASE_URL}/health/db" >/dev/null

echo "Verifying /docs..."
curl -fsS "${BASE_URL}/docs" >/dev/null

echo "Verifying login..."
LOGIN_RESPONSE=$(
  curl -fsS \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${DEMO_EMAIL}\",\"password\":\"${DEMO_PASSWORD}\"}" \
    "${BASE_URL}/api/v1/auth/login"
)

ACCESS_TOKEN=$(
  printf '%s' "${LOGIN_RESPONSE}" | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])"
)

if [ -z "${ACCESS_TOKEN}" ]; then
  echo "Login verification failed: access token missing"
  exit 1
fi

echo "Verifying demo seed data visibility..."
PROJECT_COUNT=$(
  curl -fsS \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    "${BASE_URL}/api/v1/projects/" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))"
)

if [ "${PROJECT_COUNT}" -lt 1 ]; then
  echo "Demo seed verification failed: no projects returned"
  exit 1
fi

curl -fsS \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${BASE_URL}/api/v1/dashboard/summary" >/dev/null

echo "Staging verification passed."
