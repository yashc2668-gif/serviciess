"""Dashboard endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import (
    ContractDashboardOut,
    DashboardFinanceOut,
    DashboardSummaryOut,
    ProjectDashboardOut,
)
from app.services.dashboard_service import (
    get_contract_dashboard,
    get_dashboard_finance,
    get_dashboard_summary,
    get_project_dashboard,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryOut)
def get_summary_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("dashboard:read")),
):
    return get_dashboard_summary(db)


@router.get("/finance", response_model=DashboardFinanceOut)
def get_finance_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("dashboard:read")),
):
    return get_dashboard_finance(db)


@router.get("/projects/{project_id}", response_model=ProjectDashboardOut)
def get_project_finance_dashboard(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("dashboard:read")),
):
    return get_project_dashboard(db, project_id)


@router.get("/contracts/{contract_id}", response_model=ContractDashboardOut)
def get_contract_finance_dashboard(
    contract_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("dashboard:read")),
):
    return get_contract_dashboard(db, contract_id)


@router.get("/projects/{project_id}/legacy", response_model=ProjectDashboardOut)
def get_legacy_project_dashboard(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("dashboard:read")),
):
    return get_project_dashboard(db, project_id)
