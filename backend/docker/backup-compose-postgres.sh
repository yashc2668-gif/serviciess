#!/bin/sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.staging.yml}"
ENV_FILE="${ENV_FILE:-.env.staging}"
DB_SERVICE="${DB_SERVICE:-db}"
APP_SERVICE="${APP_SERVICE:-backend}"
BACKUP_ROOT="${BACKUP_ROOT:-backups}"
INCLUDE_UPLOADS="${INCLUDE_UPLOADS:-true}"
BACKUP_LABEL="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
BACKUP_DIR="${BACKUP_ROOT%/}/${BACKUP_LABEL}"

if [ ! -f "${COMPOSE_FILE}" ]; then
  echo "Compose file not found: ${COMPOSE_FILE}"
  exit 1
fi

if [ ! -f "${ENV_FILE}" ]; then
  echo "Env file not found: ${ENV_FILE}"
  exit 1
fi

compose() {
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" "$@"
}

mkdir -p "${BACKUP_DIR}"

echo "Creating PostgreSQL backup in ${BACKUP_DIR}"
compose exec -T "${DB_SERVICE}" sh -lc '
  export PGPASSWORD="${POSTGRES_PASSWORD}"
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc --no-owner --no-privileges
' > "${BACKUP_DIR}/database.dump"

compose exec -T "${DB_SERVICE}" sh -lc '
  export PGPASSWORD="${POSTGRES_PASSWORD}"
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -At -c "select version_num from alembic_version limit 1"
' > "${BACKUP_DIR}/alembic_version.txt"

compose exec -T "${DB_SERVICE}" sh -lc '
  export PGPASSWORD="${POSTGRES_PASSWORD}"
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -At -c "select version()"
' > "${BACKUP_DIR}/postgres_version.txt"

cat > "${BACKUP_DIR}/manifest.txt" <<EOF
backup_label=${BACKUP_LABEL}
created_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
compose_file=${COMPOSE_FILE}
env_file=${ENV_FILE}
db_service=${DB_SERVICE}
app_service=${APP_SERVICE}
include_uploads=${INCLUDE_UPLOADS}
EOF

if [ "${INCLUDE_UPLOADS}" = "true" ]; then
  echo "Archiving uploads volume"
  compose exec -T "${APP_SERVICE}" sh -lc '
    if [ -d /app/uploads ]; then
      tar -czf - -C /app/uploads .
    fi
  ' > "${BACKUP_DIR}/uploads.tar.gz"
  echo "uploads_archive=uploads.tar.gz" >> "${BACKUP_DIR}/manifest.txt"
else
  echo "uploads_archive=skipped" >> "${BACKUP_DIR}/manifest.txt"
fi

echo "Backup completed: ${BACKUP_DIR}"
