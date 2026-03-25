"""Audit log read APIs."""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.audit import AuditLogOut
from app.services.audit_service import get_audit_log_or_404, list_audit_logs

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("/", response_model=List[AuditLogOut])
def list_all_audit_logs(
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: str | None = None,
    performed_by: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("audit_logs:read")),
):
    return list_audit_logs(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{audit_log_id}", response_model=AuditLogOut)
def get_single_audit_log(
    audit_log_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("audit_logs:read")),
):
    return get_audit_log_or_404(db, audit_log_id)
