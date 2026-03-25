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

retry_curl() {
  url="${1}"
  attempts="${2:-12}"
  delay_seconds="${3:-5}"
  count=1

  until curl -fsS "${url}" >/dev/null
  do
    if [ "${count}" -ge "${attempts}" ]; then
      echo "Request failed for ${url} after ${count} attempts."
      exit 1
    fi

    echo "Request to ${url} failed on attempt ${count}, retrying in ${delay_seconds}s..."
    count=$((count + 1))
    sleep "${delay_seconds}"
  done
}

retry_login() {
  attempts="${1:-12}"
  delay_seconds="${2:-5}"
  count=1

  until LOGIN_RESPONSE=$(
    curl -fsS \
      -H "Content-Type: application/json" \
      -d "{\"email\":\"${DEMO_EMAIL}\",\"password\":\"${DEMO_PASSWORD}\"}" \
      "${BASE_URL}/api/v1/auth/login"
  )
  do
    if [ "${count}" -ge "${attempts}" ]; then
      echo "Login verification failed after ${count} attempts."
      exit 1
    fi

    echo "Login attempt ${count} failed, retrying in ${delay_seconds}s..."
    count=$((count + 1))
    sleep "${delay_seconds}"
  done
}

echo "Verifying /health..."
retry_curl "${BASE_URL}/health" 12 5

echo "Verifying /health/db..."
retry_curl "${BASE_URL}/health/db" 12 5

echo "Verifying /docs..."
retry_curl "${BASE_URL}/docs" 12 5

echo "Verifying login..."
retry_login 12 5

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
