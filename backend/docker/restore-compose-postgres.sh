#!/bin/sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "Usage: sh docker/restore-compose-postgres.sh <backup-dir>"
  exit 1
fi

BACKUP_DIR="${1%/}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.staging.yml}"
ENV_FILE="${ENV_FILE:-.env.staging}"
DB_SERVICE="${DB_SERVICE:-db}"
APP_SERVICE="${APP_SERVICE:-backend}"
RESTORE_MODE="${RESTORE_MODE:-scratch}"
RESTORE_UPLOADS="${RESTORE_UPLOADS:-false}"
UPLOAD_RESTORE_DIR="${UPLOAD_RESTORE_DIR:-restore-checks/$(basename "${BACKUP_DIR}")/uploads}"
TMP_DUMP_PATH="/tmp/m2n_restore.dump"

if [ ! -d "${BACKUP_DIR}" ]; then
  echo "Backup directory not found: ${BACKUP_DIR}"
  exit 1
fi

if [ ! -f "${BACKUP_DIR}/database.dump" ]; then
  echo "database.dump missing in ${BACKUP_DIR}"
  exit 1
fi

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

TARGET_DB_NAME="${TARGET_DB_NAME:-}"

if [ -z "${TARGET_DB_NAME}" ]; then
  if [ "${RESTORE_MODE}" = "scratch" ]; then
    TARGET_DB_NAME="$(sed -n 's/^POSTGRES_DB=//p' "${ENV_FILE}" | head -n 1)_restore_check"
  else
    TARGET_DB_NAME="$(sed -n 's/^POSTGRES_DB=//p' "${ENV_FILE}" | head -n 1)"
  fi
fi

if [ -z "${TARGET_DB_NAME}" ]; then
  echo "Unable to determine target database name. Set TARGET_DB_NAME explicitly."
  exit 1
fi

case "${RESTORE_MODE}" in
  scratch)
    echo "Preparing scratch database ${TARGET_DB_NAME}"
    compose exec -T "${DB_SERVICE}" sh -lc "
      export PGPASSWORD=\"\${POSTGRES_PASSWORD}\"
      psql -U \"\${POSTGRES_USER}\" -d postgres -v ON_ERROR_STOP=1 \
        -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${TARGET_DB_NAME}' AND pid <> pg_backend_pid();\" \
        -c \"DROP DATABASE IF EXISTS \\\"${TARGET_DB_NAME}\\\";\" \
        -c \"CREATE DATABASE \\\"${TARGET_DB_NAME}\\\";\"
    "
    ;;
  inplace)
    if [ "${CONFIRM_INPLACE_RESTORE:-}" != "YES_I_UNDERSTAND" ]; then
      echo "In-place restore requires CONFIRM_INPLACE_RESTORE=YES_I_UNDERSTAND"
      exit 1
    fi
    echo "Running in-place restore against ${TARGET_DB_NAME}"
    ;;
  *)
    echo "Unsupported RESTORE_MODE: ${RESTORE_MODE}"
    exit 1
    ;;
esac

echo "Copying dump into database container"
compose exec -T "${DB_SERVICE}" sh -lc "cat > '${TMP_DUMP_PATH}'" < "${BACKUP_DIR}/database.dump"

echo "Restoring database ${TARGET_DB_NAME}"
compose exec -T "${DB_SERVICE}" sh -lc "
  export PGPASSWORD=\"\${POSTGRES_PASSWORD}\"
  pg_restore --clean --if-exists --no-owner --no-privileges -U \"\${POSTGRES_USER}\" -d \"${TARGET_DB_NAME}\" \"${TMP_DUMP_PATH}\"
"

RESTORED_REVISION="$(
  compose exec -T "${DB_SERVICE}" sh -lc "
    export PGPASSWORD=\"\${POSTGRES_PASSWORD}\"
    psql -U \"\${POSTGRES_USER}\" -d \"${TARGET_DB_NAME}\" -At -c \"select version_num from alembic_version limit 1\"
  "
)"

echo "Restored Alembic revision: ${RESTORED_REVISION}"

if [ "${RESTORE_UPLOADS}" = "true" ] && [ -f "${BACKUP_DIR}/uploads.tar.gz" ]; then
  mkdir -p "${UPLOAD_RESTORE_DIR}"

  if [ "${RESTORE_MODE}" = "scratch" ]; then
    echo "Extracting uploads archive into ${UPLOAD_RESTORE_DIR}"
    tar -xzf "${BACKUP_DIR}/uploads.tar.gz" -C "${UPLOAD_RESTORE_DIR}"
  else
    if [ "${CONFIRM_INPLACE_RESTORE:-}" != "YES_I_UNDERSTAND" ]; then
      echo "In-place upload restore requires CONFIRM_INPLACE_RESTORE=YES_I_UNDERSTAND"
      exit 1
    fi
    echo "Restoring uploads archive into /app/uploads"
    compose exec -T "${APP_SERVICE}" sh -lc 'mkdir -p /app/uploads'
    compose exec -T "${APP_SERVICE}" sh -lc 'tar -xzf - -C /app/uploads' < "${BACKUP_DIR}/uploads.tar.gz"
  fi
fi

echo "Restore completed for ${TARGET_DB_NAME}"
