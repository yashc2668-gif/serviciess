"""Backward-compatible singular labour attendance routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.labour_attendance import (
    LabourAttendanceCreate,
    LabourAttendanceOut,
    LabourAttendanceTransitionRequest,
    LabourAttendanceUpdate,
)
from app.services.labour_attendance_service import (
    create_labour_attendance,
    get_labour_attendance_or_404,
    list_labour_attendances,
    update_labour_attendance,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/labour-attendance", tags=["Labour Attendance"])


@router.get("", response_model=PaginatedResponse[LabourAttendanceOut], include_in_schema=False)
@router.get("/", response_model=PaginatedResponse[LabourAttendanceOut], include_in_schema=False)
def list_all_labour_attendances_alias(
    project_id: int | None = None,
    contractor_id: int | None = None,
    status: str | None = None,
    created_by: int | None = None,
    marked_by: int | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("labour_attendance:read")),
):
    return list_labour_attendances(
        db,
        current_user=current_user,
        pagination=pagination,
        project_id=project_id,
        contractor_id=contractor_id,
        status_filter=status,
        marked_by=created_by if created_by is not None else marked_by,
    )


@router.post("", response_model=LabourAttendanceOut, status_code=201, include_in_schema=False)
@router.post("/", response_model=LabourAttendanceOut, status_code=201, include_in_schema=False)
def create_new_labour_attendance_alias(
    payload: LabourAttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("attendance:create")),
):
    return create_labour_attendance(db, payload, current_user)


@router.get("/{attendance_id}", response_model=LabourAttendanceOut, include_in_schema=False)
def get_single_labour_attendance_alias(
    attendance_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("labour_attendance:read")),
):
    return get_labour_attendance_or_404(db, attendance_id)


@router.put("/{attendance_id}", response_model=LabourAttendanceOut, include_in_schema=False)
def update_existing_labour_attendance_alias(
    attendance_id: int,
    payload: LabourAttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("attendance:approve")),
):
    return update_labour_attendance(db, attendance_id, payload, current_user)


@router.post("/{attendance_id}/submit", response_model=LabourAttendanceOut, include_in_schema=False)
def submit_existing_labour_attendance_alias(
    attendance_id: int,
    payload: LabourAttendanceTransitionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("attendance:create")),
):
    update_payload: dict = {"status": "submitted"}
    if payload is not None and payload.remarks is not None:
        update_payload["remarks"] = payload.remarks
    return update_labour_attendance(
        db,
        attendance_id,
        LabourAttendanceUpdate(**update_payload),
        current_user,
    )


@router.post("/{attendance_id}/approve", response_model=LabourAttendanceOut, include_in_schema=False)
def approve_existing_labour_attendance_alias(
    attendance_id: int,
    payload: LabourAttendanceTransitionRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("attendance:approve")),
):
    update_payload: dict = {"status": "approved"}
    if payload is not None and payload.remarks is not None:
        update_payload["remarks"] = payload.remarks
    return update_labour_attendance(
        db,
        attendance_id,
        LabourAttendanceUpdate(**update_payload),
        current_user,
    )
