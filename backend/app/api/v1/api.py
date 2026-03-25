"""v1 API router registry for ready modules."""

from fastapi import APIRouter

from app.api.v1.endpoints.audit_logs import router as audit_logs_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.boq import router as boq_router
from app.api.v1.endpoints.contracts import router as contracts_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.documents import router as documents_router
from app.api.v1.endpoints.measurements import router as measurements_router
from app.api.v1.endpoints.payments import router as payments_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.ra_bills import router as ra_bills_router
from app.api.v1.endpoints.secured_advances import router as secured_advances_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.vendors import router as vendors_router
from app.api.v1.endpoints.work_done import router as work_done_router

api_router = APIRouter()

for router in (
    auth_router,
    audit_logs_router,
    users_router,
    projects_router,
    vendors_router,
    contracts_router,
    boq_router,
    dashboard_router,
    documents_router,
    measurements_router,
    work_done_router,
    ra_bills_router,
    secured_advances_router,
    payments_router,
):
    api_router.include_router(router)
