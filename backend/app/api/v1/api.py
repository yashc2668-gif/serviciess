"""v1 API router registry for ready modules."""

from fastapi import APIRouter

from app.api.v1.endpoints.ai_boundary import router as ai_boundary_router
from app.api.v1.endpoints.audit_logs import router as audit_logs_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.boq import router as boq_router
from app.api.v1.endpoints.companies import router as companies_router
from app.api.v1.endpoints.contracts import router as contracts_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.deductions import router as deductions_router
from app.api.v1.endpoints.documents import router as documents_router
from app.api.v1.endpoints.financial_archives import router as financial_archives_router
from app.api.v1.endpoints.labour import router as labour_router
from app.api.v1.endpoints.labour_advances import router as labour_advances_router
from app.api.v1.endpoints.labour_attendance import router as labour_attendance_router
from app.api.v1.endpoints.labour_attendances import router as labour_attendances_router
from app.api.v1.endpoints.labour_bills import router as labour_bills_router
from app.api.v1.endpoints.labour_contractors import router as labour_contractors_router
from app.api.v1.endpoints.labour_productivities import router as labour_productivities_router
from app.api.v1.endpoints.labours import router as labours_router
from app.api.v1.endpoints.measurements import router as measurements_router
from app.api.v1.endpoints.material_issues import router as material_issues_router
from app.api.v1.endpoints.material_stock_adjustments import (
    router as material_stock_adjustments_router,
)
from app.api.v1.endpoints.materials import router as materials_router
from app.api.v1.endpoints.material_receipts import router as material_receipts_router
from app.api.v1.endpoints.material_requisitions import router as material_requisitions_router
from app.api.v1.endpoints.payments import router as payments_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.ra_bills import router as ra_bills_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.secured_advances import router as secured_advances_router
from app.api.v1.endpoints.stock_adjustments import router as stock_adjustments_router
from app.api.v1.endpoints.stock_ledger import router as stock_ledger_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.vendors import router as vendors_router
from app.api.v1.endpoints.work_done import router as work_done_router
from app.api.v1.endpoints.workflows import router as workflows_router

api_router = APIRouter()

for router in (
    # Core foundation
    auth_router,
    ai_boundary_router,
    audit_logs_router,
    users_router,
    companies_router,
    projects_router,
    vendors_router,
    contracts_router,
    documents_router,
    dashboard_router,
    reports_router,
    workflows_router,
    # Material domain build order
    materials_router,
    material_requisitions_router,
    stock_ledger_router,
    material_receipts_router,
    material_issues_router,
    material_stock_adjustments_router,
    stock_adjustments_router,
    # Labour domain build order
    labour_contractors_router,
    labours_router,
    labour_router,
    labour_attendances_router,
    labour_attendance_router,
    labour_productivities_router,
    labour_bills_router,
    labour_advances_router,
    # Finance / RA bill / payment linkages
    boq_router,
    measurements_router,
    work_done_router,
    deductions_router,
    ra_bills_router,
    financial_archives_router,
    secured_advances_router,
    payments_router,
):
    api_router.include_router(router)
