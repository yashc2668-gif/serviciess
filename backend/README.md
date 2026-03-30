# M2N Construction ERP Backend

FastAPI backend for construction ERP workflows covering auth, RBAC, projects, vendors, contracts, BOQ, measurements, RA billing, payments, secured advances, documents, audit logs, and dashboard reporting.

## Setup

### Requirements

- Python 3.12+
- PostgreSQL 16+
- Optional: Docker Desktop with Compose

### Fresh local setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Update `.env` before first run:

- set DB credentials
- set a real `SECRET_KEY`
- set `ALLOWED_ORIGINS` to your actual frontend origins
- optionally set `ADMIN_EMAIL` and `ADMIN_PASSWORD` for bootstrap admin creation
- set `DEBUG=True` only for local development when you need verbose errors

## Environment variables

Core variables from [`.env.example`](./.env.example):

- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `DATABASE_URL` for full override
- `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- `PROJECT_NAME`, `ENVIRONMENT`, `DEBUG`, `APP_PORT`, `LOG_LEVEL`
- `ALLOWED_ORIGINS`
- `STORAGE_BACKEND`, `LOCAL_STORAGE_ROOT`, `MAX_UPLOAD_SIZE_MB`
- `ALLOWED_DOCUMENT_MIME_TYPES`, `ALLOWED_DOCUMENT_EXTENSIONS`
- `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_FULL_NAME`, `ADMIN_PHONE`, `ADMIN_ROLE`

## Local run

Apply migrations:

```powershell
cd backend
.\venv\Scripts\python.exe -m alembic upgrade head
```

Seed roles and optional admin manually if needed:

```powershell
cd backend
.\venv\Scripts\python.exe -m app.db.seed
```

Start the API:

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open:

- Docs: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`
- Health: `http://127.0.0.1:8000/health`
- DB health: `http://127.0.0.1:8000/health/db`
- Readiness: `http://127.0.0.1:8000/health/ready`

Every response also includes `X-Request-ID`, which is logged and propagated into audit records where available.

## Docker run

### Recommended: docker-compose

```powershell
cd backend
Copy-Item .env.example .env
docker compose up --build
```

What Compose does:

- starts PostgreSQL 16 on port `5432`
- builds backend image from [`Dockerfile`](./Dockerfile)
- waits for DB health
- runs `alembic upgrade head` on container startup
- starts FastAPI on port `8000`

Useful commands:

```powershell
docker compose up --build -d
docker compose logs -f backend
docker compose exec backend python -m alembic current
docker compose down
docker compose down -v
```

Compose expects PostgreSQL plus backend to become healthy, then the backend entrypoint runs Alembic before serving traffic.

### Plain Docker

```powershell
cd backend
docker build -t m2n-backend .
docker run --rm -p 8000:8000 --env-file .env m2n-backend
```

For plain Docker, the database must already be reachable from the container using the configured env values.

## Railway + Neon + Vercel (Production)

Recommended architecture:

- Backend: Railway
- Database: Neon Postgres
- Frontend: Vercel

Railway service settings:

- Repository format must be `owner/repo` (example: `MARCODEVLOPEMENT/serviciess`)
- Branch: `main`
- Root Directory: `/backend`
- Service Name: `backend`

Required Railway variables:

```env
DATABASE_URL=postgresql://<user>:<password>@<neon-host>/<db>?sslmode=require
SECRET_KEY=<long-random-secret>
ENVIRONMENT=production
DEBUG=False
APP_PORT=${{PORT}}
LOG_LEVEL=INFO
ALLOWED_ORIGINS=["https://<your-frontend>.vercel.app","https://<your-custom-domain>"]

STORAGE_BACKEND=local
LOCAL_STORAGE_ROOT=/app/uploads
MAX_UPLOAD_SIZE_MB=10
ALLOWED_DOCUMENT_MIME_TYPES=["application/pdf","image/png","image/jpeg","application/msword","application/vnd.openxmlformats-officedocument.wordprocessingml.document","application/vnd.ms-excel","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]
ALLOWED_DOCUMENT_EXTENSIONS=[".pdf",".png",".jpg",".jpeg",".doc",".docx",".xls",".xlsx"]
```

Railway notes:

- `railway.toml` is included with healthcheck path `/health/ready`.
- Container startup runs `alembic upgrade head` automatically via entrypoint.
- Entrypoint supports Railway's `PORT` env directly, with `APP_PORT` fallback.
- If you need persistent uploaded files, attach a Railway volume at `/app/uploads`.

Vercel frontend variable:

```env
VITE_API_BASE_URL=https://<your-railway-domain>
```

## CI/CD and staging

GitHub Actions workflows are included at the repo root:

- `/.github/workflows/backend-ci.yml`
- `/.github/workflows/staging-deploy.yml`

CI currently does:

- validate fresh-db Alembic upgrade discipline
- run `alembic check` to catch model changes missing migrations
- smoke-test startup on empty and migrated fresh SQLite databases
- install dependencies
- import the app
- run the backend test suite
- build the backend Docker image

## Backup and recovery

Self-hosted Compose environments persist state in Docker volumes:

- database volume: see [`docker-compose.yml`](./docker-compose.yml) and [`docker-compose.staging.yml`](./docker-compose.staging.yml)
- uploads volume: [`docker-compose.staging.yml`](./docker-compose.staging.yml) mounts `/app/uploads`

Use the dedicated runbook for exact recovery steps:

- [`BACKUP_RECOVERY_RUNBOOK.md`](./BACKUP_RECOVERY_RUNBOOK.md)

Helper scripts included:

- `sh docker/backup-compose-postgres.sh`
- `sh docker/restore-compose-postgres.sh backups/<backup-label>`

Staging deploy can take an automatic pre-deploy backup when `RUN_PREDEPLOY_BACKUP=true` in `.env.staging`.

## AI usage boundary

This backend does not expose any AI-powered write workflow.

- AI is disabled by default through `.env`
- if enabled later, the only supported mode is `suggestion_only`
- AI cannot directly create, approve, issue, allocate, pay, or mutate business records
- final business actions must still pass backend services, DB constraints, workflow rules, and tests
- admin-only policy inspection endpoint: `/api/v1/ai-boundary`

Staging deploy expects these GitHub secrets:

- `STAGING_HOST`
- `STAGING_USER`
- `STAGING_SSH_KEY`
- `STAGING_TARGET_DIR`

Staging files included in this repo:

- [`docker-compose.staging.yml`](./docker-compose.staging.yml)
- [`.env.staging.example`](./.env.staging.example)
- [`docker/deploy-staging.sh`](./docker/deploy-staging.sh)
- [`docker/verify-staging.sh`](./docker/verify-staging.sh)
- [`docker/bootstrap-staging-ubuntu.sh`](./docker/bootstrap-staging-ubuntu.sh)

Remote deploy flow:

- sync backend directory to the staging host
- run staging compose build/up
- run Alembic through the backend entrypoint
- optionally seed demo/UAT data
- verify `/health`, `/health/db`, `/docs`, auth login, and demo project visibility

Typical first-time staging bootstrap on Ubuntu:

```bash
sudo bash backend/docker/bootstrap-staging-ubuntu.sh
cp backend/.env.staging.example backend/.env.staging
```

## Migrations

Create a revision:

```powershell
cd backend
.\venv\Scripts\python.exe -m alembic revision --autogenerate -m "your_change"
```

Apply latest migration:

```powershell
cd backend
.\venv\Scripts\python.exe -m alembic upgrade head
```

Check current revision:

```powershell
cd backend
.\venv\Scripts\python.exe -m alembic current
```

Run migration discipline validation locally:

```powershell
cd backend
.\venv\Scripts\python.exe scripts/verify_migration_discipline.py
```

## Seed roles and admin

- Roles are seeded automatically on app startup.
- Admin user is seeded automatically only when both `ADMIN_EMAIL` and `ADMIN_PASSWORD` are present.
- Manual seed command:

```powershell
cd backend
.\venv\Scripts\python.exe -m app.db.seed
```

Default seeded roles:

- Admin
- Project Manager
- Engineer
- Accountant
- Contractor
- Viewer

## Run tests

```powershell
cd backend
.\venv\Scripts\python.exe -m unittest discover app/tests -v
```

Coverage gate for service/calculator/workflow logic:

```powershell
cd backend
.\venv\Scripts\coverage.exe erase
.\venv\Scripts\coverage.exe run -m unittest discover app/tests -v
.\venv\Scripts\coverage.exe report
.\venv\Scripts\coverage.exe xml
```

Focused upload/document tests:

```powershell
cd backend
.\venv\Scripts\python.exe -m unittest app.tests.test_api_integration app.tests.test_document_upload app.tests.test_storage -v
```

## Default ports

- API: `8000`
- PostgreSQL: `5432`
- Swagger docs: `8000/docs`
- ReDoc: `8000/redoc`

## Upload storage config

- Phase 1 storage backend: `local`
- Files are stored under `LOCAL_STORAGE_ROOT`
- Upload max size is controlled by `MAX_UPLOAD_SIZE_MB`
- Allowed types/extensions are controlled by `ALLOWED_DOCUMENT_MIME_TYPES` and `ALLOWED_DOCUMENT_EXTENSIONS`
- Paths are generated server-side and do not reuse raw user filenames

## Known modules

- Authentication and JWT
- RBAC and users
- Projects
- Vendors
- Contracts and contract revisions
- BOQ
- Measurements and work done
- RA bills and deductions
- Secured advances
- Payments and allocations
- Documents and versions
- Audit logs
- Dashboard summaries

## Operational runbook

See [`RUNBOOK.md`](./RUNBOOK.md) for daily operations, health checks, troubleshooting, and Docker commands.

## UAT / Demo flow

Use [`UAT_RUNBOOK.md`](./UAT_RUNBOOK.md) for demo preparation.

Demo seed command:

```powershell
cd backend
.\venv\Scripts\python.exe -m app.db.demo_seed
```

This creates a demo company, users, project, vendor, contract, BOQ, approved measurement, RA bill, payment allocation, and versioned document data for walkthroughs.

## Production notes

- Use `ENVIRONMENT=production`
- Keep `DEBUG=False`
- Configure strict `ALLOWED_ORIGINS` for real frontend domains only
- Replace `SECRET_KEY` before deploy
- Review upload limits and allowed MIME types before exposing file uploads publicly

## Future roadmap

- Binary file upload integration for documents
- Richer approval workflow engine
- Notifications and async tasks
- Bank/payment gateway integration
- Reporting exports and scheduled summaries
- Deployment manifests for staging and production

## Verification status

Local verification completed:

- migrations apply via Alembic
- app starts successfully
- health endpoints respond
- docs and OpenAPI load
- auth, projects, contracts, BOQ, RA bills, payments, documents upload/download, dashboard, and audit log API tests pass

Docker files are finalized for Compose-based startup, but Docker runtime verification could not be executed on this machine because Docker CLI is not installed in the current environment.
