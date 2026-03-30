# Backup and Recovery Runbook

## Scope

This runbook covers the assets that are actually persisted by this backend setup:

- PostgreSQL database data
- uploaded files stored under `/app/uploads` when `STORAGE_BACKEND=local`
- environment secrets such as `.env.staging` that must be stored separately from the app repo

## Current verified deployment assumptions

These assumptions were verified from the repo configuration:

- local Docker Compose persists Postgres in the `postgres_data` volume from [docker-compose.yml](./docker-compose.yml)
- staging Docker Compose persists Postgres in the `staging_postgres_data` volume and uploads in `staging_uploads` from [docker-compose.staging.yml](./docker-compose.staging.yml)
- backend readiness is available at `/health/ready`
- backend entrypoint applies `alembic upgrade head` before serving traffic

## Backup strategy

### 1. Self-hosted Docker Compose environments

Use a logical PostgreSQL dump plus an uploads archive:

- run `pg_dump -Fc` for the active database
- capture the current Alembic revision
- archive `/app/uploads` when local file storage is enabled
- copy the resulting backup directory off-host the same day

Recommended minimum cadence:

- daily scheduled database backup
- pre-deploy backup before every staging or production release
- uploads archive whenever database backup is taken

Recommended retention:

- 7 daily backups
- 4 weekly backups
- 3 monthly backups

### 2. Managed Postgres environments

If production uses a managed provider such as Neon:

- keep provider backups / PITR enabled
- still take logical exports before risky schema or billing releases
- keep secrets and restore instructions outside the app database

### 3. Secrets and configuration

Do not rely on the app repo as the only recovery source for secrets.

Store these separately in a password vault or secret manager:

- `.env.staging`
- production `DATABASE_URL`
- `SECRET_KEY`
- any cloud storage credentials if file storage is moved away from local volumes

## Backup commands

These helper scripts were added for Compose-based environments:

```sh
cd backend
sh docker/backup-compose-postgres.sh
```

Useful overrides:

```sh
COMPOSE_FILE=docker-compose.staging.yml \
ENV_FILE=.env.staging \
BACKUP_ROOT=backups \
INCLUDE_UPLOADS=true \
sh docker/backup-compose-postgres.sh
```

The script creates a timestamped backup directory containing:

- `database.dump`
- `alembic_version.txt`
- `postgres_version.txt`
- `manifest.txt`
- `uploads.tar.gz` when uploads are included

## Restore process

### Recommended: scratch restore verification

Use scratch restore first so the live database is not overwritten:

```sh
cd backend
RESTORE_MODE=scratch \
COMPOSE_FILE=docker-compose.staging.yml \
ENV_FILE=.env.staging \
sh docker/restore-compose-postgres.sh backups/<backup-label>
```

Optional uploads verification:

```sh
cd backend
RESTORE_MODE=scratch \
RESTORE_UPLOADS=true \
UPLOAD_RESTORE_DIR=restore-checks/<backup-label>/uploads \
COMPOSE_FILE=docker-compose.staging.yml \
ENV_FILE=.env.staging \
sh docker/restore-compose-postgres.sh backups/<backup-label>
```

### In-place restore

Only run this when you intentionally want to overwrite the active database and have already communicated downtime.

```sh
cd backend
CONFIRM_INPLACE_RESTORE=YES_I_UNDERSTAND \
RESTORE_MODE=inplace \
RESTORE_UPLOADS=true \
COMPOSE_FILE=docker-compose.staging.yml \
ENV_FILE=.env.staging \
sh docker/restore-compose-postgres.sh backups/<backup-label>
```

Recommended in-place sequence:

1. Announce maintenance / freeze writes.
2. Take a fresh pre-restore backup.
3. Stop or isolate client traffic.
4. Run the in-place restore command.
5. Restart backend services if needed.
6. Verify `/health/ready`, login, and one read-only business endpoint.

## Restore test checklist

Run this checklist whenever you validate a backup:

1. Confirm the backup directory contains `database.dump` and `manifest.txt`.
2. Restore into a scratch database using `RESTORE_MODE=scratch`.
3. Verify the restored database has an Alembic revision in `alembic_version`.
4. Run sample row-count checks for critical tables such as:
   - `users`
   - `projects`
   - `contracts`
   - `materials`
   - `labour_attendances`
   - `ra_bills`
   - `payments`
5. If uploads are enabled, verify `uploads.tar.gz` can be listed or extracted successfully.
6. Check that the restored backup timestamp and manifest match the expected backup event.
7. Record restore duration, backup age, success/failure, and any manual fixes required.

Example row-count checks:

```sh
docker compose -f docker-compose.staging.yml --env-file .env.staging exec -T db \
  sh -lc 'export PGPASSWORD="${POSTGRES_PASSWORD}"; psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}_restore_check" -c "select count(*) from users; select count(*) from projects; select count(*) from contracts; select count(*) from payments;"'
```

## Monthly recovery drill recommendation

Run one recovery drill every month.

Recommended drill format:

1. Select the latest successful backup and one older backup at random.
2. Restore the latest backup into a scratch database.
3. Verify Alembic revision, row counts, and uploads archive integrity.
4. Measure how long the restore took end to end.
5. Record:
   - drill date
   - operator name
   - backup label used
   - restore duration
   - blockers or manual fixes
   - follow-up actions
6. Update this runbook if the real recovery process differed from the documented one.

Recommended operational targets:

- staging restore drill target: under 60 minutes
- production restore objective: define and approve explicit RTO/RPO with the business team

## Notes

- Backup directories should be copied off the server. A backup that only lives on the same host is not a disaster-recovery plan.
- If `STORAGE_BACKEND` later changes to cloud object storage, update this runbook and replace uploads archive steps with provider-native backup guidance.
