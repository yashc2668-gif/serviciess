"""Secured advance endpoints."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.secured_advance import (
    SecuredAdvanceIssueCreate,
    SecuredAdvanceOut,
    SecuredAdvanceRecoveryOut,
    SecuredAdvanceUpdate,
)
from app.services.secured_advance_service import (
    get_secured_advance_or_404,
    issue_secured_advance,
    list_secured_advance_recoveries,
    list_secured_advances,
    update_secured_advance,
)

router = APIRouter(prefix="/secured-advances", tags=["Secured Advances"])


@router.get("/", response_model=List[SecuredAdvanceOut])
def list_all_secured_advances(
    contract_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("secured_advances:read")),
):
    return list_secured_advances(db, contract_id=contract_id)


@router.post("/issue", response_model=SecuredAdvanceOut, status_code=201)
def issue_new_secured_advance(
    payload: SecuredAdvanceIssueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("secured_advances:create")),
):
    return issue_secured_advance(db, payload, current_user)


@router.get("/{secured_advance_id}", response_model=SecuredAdvanceOut)
def get_single_secured_advance(
    secured_advance_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("secured_advances:read")),
):
    return get_secured_advance_or_404(db, secured_advance_id)


@router.put("/{secured_advance_id}", response_model=SecuredAdvanceOut)
def update_existing_secured_advance(
    secured_advance_id: int,
    payload: SecuredAdvanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("secured_advances:update")),
):
    return update_secured_advance(db, secured_advance_id, payload, current_user)


@router.get("/{secured_advance_id}/recoveries", response_model=List[SecuredAdvanceRecoveryOut])
def list_recoveries_for_secured_advance(
    secured_advance_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("secured_advances:read")),
):
    return list_secured_advance_recoveries(db, secured_advance_id)
