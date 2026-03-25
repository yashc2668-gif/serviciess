# UAT / Demo Runbook

## Goal

Bring up a demo-ready backend with seeded finance, billing, documents, dashboard, and audit data.

## Pre-steps

1. Configure `.env` or `.env.staging`.
2. Apply migrations:
   - `python -m alembic upgrade head`
3. Seed base roles/admin:
   - `python -m app.db.seed`

## Demo data seed

Run:

```powershell
cd backend
.\venv\Scripts\python.exe -m app.db.demo_seed
```

The script is idempotent and creates:

- demo company
- demo admin / project manager / accountant users
- project
- vendor
- contract
- BOQ items
- approved measurement + work done
- approved RA bill
- partial payment allocation
- contract document with version history

## Demo login users

- `demo-admin@example.com` / `DemoPass123!`
- `demo-pm@example.com` / `DemoPass123!`
- `demo-accounts@example.com` / `DemoPass123!`

## Suggested UAT flow

1. Login as demo admin.
2. Open `/docs` and verify auth flow.
3. Check project, contract, BOQ, measurement, RA bill, payment, dashboard, audit log APIs.
4. Download seeded contract document through `/api/v1/documents/{id}/download`.
5. Review dashboard finance endpoints after seeded payment allocation.

## Expected demo outcomes

- dashboard has meaningful values
- RA bill shows approved / partially paid flow
- payment allocation exists
- audit logs exist for billing, payment, and document events
- document version download works
