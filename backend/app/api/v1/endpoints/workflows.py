"""Workflow endpoints (read-only — lists approval workflow config)."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.approval_workflow import ApprovalWorkflow
from app.models.approval_step import ApprovalStep
from app.models.approval_log import ApprovalLog
from app.models.user import User
from app.utils.pagination import PaginationParams, apply_pagination, get_pagination_params

from pydantic import BaseModel
from datetime import datetime


class ApprovalWorkflowOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalStepOut(BaseModel):
    id: int
    workflow_id: int
    step_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalLogOut(BaseModel):
    id: int
    workflow_id: int
    action: str
    created_at: datetime

    model_config = {"from_attributes": True}


router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.get("/", response_model=List[ApprovalWorkflowOut])
def list_workflows(
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("workflows:read")),
):
    return (
        apply_pagination(
            db.query(ApprovalWorkflow).order_by(ApprovalWorkflow.id),
            skip=pagination.skip,
            limit=pagination.limit,
        )
        .all()
    )


@router.get("/{workflow_id}", response_model=ApprovalWorkflowOut)
def get_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("workflows:read")),
):
    from fastapi import HTTPException, status

    wf = db.query(ApprovalWorkflow).filter(ApprovalWorkflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return wf


@router.get("/{workflow_id}/steps", response_model=List[ApprovalStepOut])
def list_workflow_steps(
    workflow_id: int,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("workflows:read")),
):
    return (
        apply_pagination(
            db.query(ApprovalStep)
            .filter(ApprovalStep.workflow_id == workflow_id)
            .order_by(ApprovalStep.id),
            skip=pagination.skip,
            limit=pagination.limit,
        )
        .all()
    )


@router.get("/{workflow_id}/logs", response_model=List[ApprovalLogOut])
def list_workflow_logs(
    workflow_id: int,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("workflows:read")),
):
    return (
        apply_pagination(
            db.query(ApprovalLog)
            .filter(ApprovalLog.workflow_id == workflow_id)
            .order_by(ApprovalLog.created_at.desc()),
            skip=pagination.skip,
            limit=pagination.limit,
        )
        .all()
    )
