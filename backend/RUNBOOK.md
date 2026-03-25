# Backend Runbook

## Default ports

- API: `8000`
- PostgreSQL: `5432`
- Docs: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`

## Health checks

- App health: `GET /health`
- DB health: `GET /health/db`
- Readiness: `GET /health/ready`
- Every response carries `X-Request-ID` for traceability

## Local operations

- Install deps: `pip install -r requirements.txt`
- Apply migrations: `python -m alembic upgrade head`
- Check current migration: `python -m alembic current`
- Seed roles/admin manually: `python -m app.db.seed`
- Start app: `uvicorn main:app --reload --host 127.0.0.1 --port 8000`
- Run tests: `python -m unittest discover app/tests -v`
- Run upload/download focused tests: `python -m unittest app.tests.test_api_integration app.tests.test_document_upload app.tests.test_storage -v`

## Docker operations

- Build and start: `docker compose up --build`
- Start in background: `docker compose up --build -d`
- Stop services: `docker compose down`
- Stop and remove DB volume: `docker compose down -v`
- Stream backend logs: `docker compose logs -f backend`
- Stream DB logs: `docker compose logs -f db`
- Re-run migrations in backend container: `docker compose exec backend python -m alembic upgrade head`
- Staging deploy script: `sh docker/deploy-staging.sh`
- Staging verify script: `sh docker/verify-staging.sh`
- Ubuntu staging bootstrap: `sudo sh docker/bootstrap-staging-ubuntu.sh`

## Bootstrap admin

- Set both `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env` before first startup if you want an initial admin.
- Roles are seeded automatically on startup.
- Admin user is created automatically only when the configured email does not already exist.

## Fresh clone checklist

1. Copy `.env.example` to `.env`.
2. Update DB credentials and `SECRET_KEY`.
3. Optionally set bootstrap admin variables.
4. Run migrations.
5. Start API and confirm `/health/ready` and `/docs`.
6. For demo/UAT data, run `python -m app.db.demo_seed`.

## Staging checklist

1. Copy `.env.staging.example` to `.env.staging`.
2. Replace placeholder DB password and `SECRET_KEY`.
3. Set strict `ALLOWED_ORIGINS`.
4. Install Docker on Ubuntu with `sudo sh docker/bootstrap-staging-ubuntu.sh` if needed.
5. Run `sh docker/deploy-staging.sh`.
6. Confirm smoke checks pass for `/health`, `/health/db`, `/docs`, login, and demo data visibility.

## Troubleshooting

- If DB is unreachable, check `.env` values and `GET /health/db`.
- If migrations drift, run `python -m alembic upgrade head` again and re-check `python -m alembic current`.
- If auth requests fail after cloning, verify `SECRET_KEY` and bootstrap admin credentials in `.env`.
- If Docker backend cannot connect to Postgres, confirm `POSTGRES_HOST=db` inside Compose and DB health is `healthy`.
- If `/docs` opens but business endpoints fail, confirm migrations were applied to the same database configured in `.env`.
- If a production request fails, search logs by `request_id` from the response header.
