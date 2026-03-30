# M2N Construction ERP — Project Guidelines

## Architecture

Full-stack construction ERP: **FastAPI** backend + **React 19** frontend in a monorepo.

```
backend/          # Python 3.12 – FastAPI, SQLAlchemy 2, Alembic, Pydantic v2
frontend/         # TypeScript – React 19, Vite 8, TanStack Router & Query, Tailwind 4
```

### Backend layers

Endpoint → Service → Repository → ORM model.
Each domain has `app/api/v1/endpoints/`, `app/services/`, `app/models/`, `app/schemas/`.
Business validation lives in services, not endpoints.
Calculators (`app/calculators/`) handle financial math with `Decimal(ROUND_HALF_UP)`.
Workflows (`app/workflows/`) implement multi-step approval chains.

### Frontend layers

Feature modules (`src/features/`) mirror backend domains 1-to-1.
API layer (`src/api/`) has one file per endpoint group, backed by a shared `apiFetch` client.
TanStack Query manages all server state; local state is for UI toggles only.
Routing via TanStack Router with lazy-loaded routes and `beforeLoad` permission guards.

## Build and Test

### Backend (working directory: `backend/`)

```sh
pip install -r requirements.txt
python -m alembic upgrade head          # apply migrations
python -m app.db.seed                   # seed roles + admin (optional)
python -m uvicorn main:app --reload     # dev server on :8000
python -m unittest discover app/tests -v  # run tests
python scripts/verify_migration_discipline.py  # CI migration check
```

Docker: `docker compose up --build` (PostgreSQL 16 + backend).

### Frontend (working directory: `frontend/`)

```sh
npm ci
npm run dev          # Vite dev server
npm run build        # typecheck + production build
npm run test         # Vitest unit tests
npm run test:e2e     # Playwright end-to-end
npm run lint         # ESLint (zero warnings enforced)
npm run format:check # Prettier
```

## Conventions

### Backend

- **Models**: inherit `Base`; table names are snake_case; money columns use `Numeric`; optimistic locking via `lock_version` column.
- **Schemas**: `{Entity}Create`, `{Entity}Update`, `{Entity}Out`; inherit `ORMModel` (sets `from_attributes=True`).
- **Services**: functions named `get_X_or_404()`, `list_Xs()`, `create_X()`, `update_X()`, `delete_X()`; first param is `db: Session`; call `log_audit_event()` before commit; use `flush_with_conflict_handling()` for writes.
- **Endpoints**: use `Depends(get_db_session)`, `Depends(get_current_user)`, `Depends(require_roles(...))` for auth; explicit `status_code` and `response_model`.
- **Permissions**: RBAC with 6 roles (`admin`, `project_manager`, `engineer`, `accountant`, `contractor`, `viewer`); permission strings as `{entity}:{action}`.
- **Tests**: `unittest.TestCase` + `TestClient`; in-memory SQLite with `StaticPool`; auth via manual JWT flow.
- **Migrations**: one Alembic revision per feature; CI validates with `verify_migration_discipline.py`.

### Frontend

- **Imports**: use `@/` path alias everywhere (maps to `src/`).
- **Components**: `src/components/ui/` for primitives; `src/components/shell/` for app chrome; `src/components/feedback/` for states.
- **Styling**: Tailwind utility classes + CSS custom properties in `src/styles/index.css` (accent = amber, canvas = beige, sidebar = dark).
- **Permissions**: `permission-gate.tsx` for widget-level; `beforeLoad` for route-level; logic in `src/lib/permissions.ts`.
- **Data fetching**: `useQuery` / `useMutation` from TanStack Query; `staleTime: 30s`, `retry: 1`.
- **Forms**: React Hook Form + Zod validation.
- **Tests (unit)**: Vitest + React Testing Library; setup in `src/test/setup.ts`.
- **Tests (e2e)**: Playwright with route intercepts for API mocking; fixtures in `e2e/support/`.

## Key Documentation

- [FRONTEND_BLUEPRINT.md](../FRONTEND_BLUEPRINT.md) — page-by-page ERP map and architecture rationale
- [backend/README.md](../backend/README.md) — API setup, Docker, environment variables
- [backend/RUNBOOK.md](../backend/RUNBOOK.md) — operational procedures
- [backend/BACKUP_RECOVERY_RUNBOOK.md](../backend/BACKUP_RECOVERY_RUNBOOK.md) — DB backup/restore
- [backend/UAT_RUNBOOK.md](../backend/UAT_RUNBOOK.md) — user acceptance testing

## Pitfalls

- **Financial math**: always use `Decimal` with `ROUND_HALF_UP` and `MONEY_QUANTUM = 0.01` — never `float`.
- **Concurrency**: call `apply_write_lock()` + `flush_with_conflict_handling()` for any entity with `lock_version`.
- **Database URL**: backend auto-composes from `POSTGRES_*` env vars; `DATABASE_URL` overrides. SQLite is test-only.
- **CORS**: wildcard `*` is blocked in production by config validation.
- **CI gates**: backend CI runs migration validation + `unittest discover`; frontend CI runs lint + test + build + Playwright.
