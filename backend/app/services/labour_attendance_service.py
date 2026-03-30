"""Labour attendance service helpers."""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.labour import Labour
from app.models.labour_attendance import LabourAttendance
from app.models.labour_attendance_item import LabourAttendanceItem
from app.models.labour_bill import LabourBill
from app.models.labour_bill_item import LabourBillItem
from app.models.labour_contractor import LabourContractor
from app.models.project import Project
from app.models.user import User
from app.schemas.labour_attendance import LabourAttendanceCreate, LabourAttendanceUpdate
from app.services.audit_service import (
    log_audit_event,
    serialize_model,
    serialize_models,
)
from app.services.company_scope_service import (
    apply_labour_attendance_company_scope,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    apply_write_lock,
    commit_with_conflict_handling,
    flush_with_conflict_handling,
    touch_rows,
)
from app.utils.pagination import PaginationParams, paginate_query

VALID_LABOUR_ATTENDANCE_STATUSES = {"draft", "submitted", "approved", "cancelled"}
VALID_ATTENDANCE_ITEM_STATUSES = {"present", "absent", "half_day", "leave"}
INITIAL_LABOUR_ATTENDANCE_STATUSES = {"draft", "submitted"}
LABOUR_ATTENDANCE_ALLOWED_STATUS_TRANSITIONS = {
    "draft": {"submitted", "cancelled"},
    "submitted": {"approved", "cancelled"},
    "approved": {"cancelled"},
    "cancelled": set(),
}


def _normalize_status(raw_status: str) -> str:
    normalized = raw_status.strip().lower()
    if normalized not in VALID_LABOUR_ATTENDANCE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid attendance status. Allowed values: "
                "draft, submitted, approved, cancelled"
            ),
        )
    return normalized


def _normalize_item_status(raw_status: str) -> str:
    normalized = raw_status.strip().lower()
    if normalized not in VALID_ATTENDANCE_ITEM_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid attendance item status. Allowed values: "
                "present, absent, half_day, leave"
            ),
        )
    return normalized


def _normalize_muster_no(raw_muster_no: str) -> str:
    normalized = raw_muster_no.strip().upper()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="muster_no cannot be empty",
        )
    return normalized


def _normalize_optional_text(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    return raw_value.strip() or None


def _generate_muster_no(db: Session, *, project_id: int, attendance_date) -> str:
    date_part = attendance_date.strftime("%Y%m%d")
    prefix = f"MST-{project_id}-{date_part}"
    query = db.query(func.count(LabourAttendance.id)).filter(
        LabourAttendance.muster_no.ilike(f"{prefix}-%")
    )
    serial = int(query.scalar() or 0) + 1
    return f"{prefix}-{serial:03d}"


def _ensure_unique_muster_no(
    db: Session,
    muster_no: str,
    *,
    exclude_attendance_id: int | None = None,
) -> None:
    query = db.query(LabourAttendance).filter(
        func.lower(LabourAttendance.muster_no) == muster_no.lower()
    )
    if exclude_attendance_id is not None:
        query = query.filter(LabourAttendance.id != exclude_attendance_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Muster number already exists",
        )


def _ensure_project_exists(db: Session, project_id: int) -> None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )


def _ensure_user_exists(db: Session, user_id: int) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Created by user not found",
        )


def _ensure_contractor_exists(db: Session, contractor_id: int | None) -> None:
    if contractor_id is None:
        return
    contractor = (
        db.query(LabourContractor).filter(LabourContractor.id == contractor_id).first()
    )
    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labour contractor not found",
        )


def _ensure_labour_exists(db: Session, labour_id: int) -> Labour:
    labour = db.query(Labour).filter(Labour.id == labour_id).first()
    if not labour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Labour not found for labour_id={labour_id}",
        )
    if not labour.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Labour is inactive for labour_id={labour_id}",
        )
    return labour


def _resolve_present_days(attendance_status: str, present_days: float | None) -> float:
    if present_days is not None:
        value = float(present_days)
    else:
        status_defaults = {
            "present": 1.0,
            "half_day": 0.5,
            "absent": 0.0,
            "leave": 0.0,
        }
        value = status_defaults[attendance_status]
    if value < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="present_days cannot be negative",
        )
    if attendance_status in {"absent", "leave"} and value > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="present_days must be 0 for absent or leave status",
        )
    return value


def _validate_item_values(
    *,
    overtime_hours: float,
    wage_rate: float,
) -> None:
    if overtime_hours < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="overtime_hours cannot be negative",
        )
    if wage_rate < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="wage_rate cannot be negative",
        )


def _calculate_line_amount(
    *,
    present_days: float,
    overtime_hours: float,
    wage_rate: float,
) -> float:
    day_equivalent = present_days + (overtime_hours / 8.0)
    return round(day_equivalent * wage_rate, 2)


def _serialize_attendance(attendance: LabourAttendance) -> dict:
    return {
        "attendance": serialize_model(attendance),
        "items": serialize_models(list(attendance.items)),
    }


def _validate_status_transition(*, current_status: str, target_status: str) -> None:
    if target_status == current_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Labour attendance is already {target_status}",
        )
    allowed_statuses = LABOUR_ATTENDANCE_ALLOWED_STATUS_TRANSITIONS.get(
        current_status,
        set(),
    )
    if target_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid labour attendance status transition: "
                f"{current_status} -> {target_status}"
            ),
        )


def _assert_no_duplicate_attendance_for_labours(
    db: Session,
    *,
    labour_ids: set[int],
    project_id: int,
    attendance_date,
    exclude_attendance_id: int | None = None,
) -> None:
    if not labour_ids:
        return
    query = (
        db.query(LabourAttendanceItem.labour_id)
        .join(LabourAttendance, LabourAttendance.id == LabourAttendanceItem.attendance_id)
        .filter(
            LabourAttendanceItem.labour_id.in_(labour_ids),
            LabourAttendance.project_id == project_id,
            LabourAttendance.attendance_date == attendance_date,
            LabourAttendance.status != "cancelled",
        )
    )
    if exclude_attendance_id is not None:
        query = query.filter(LabourAttendance.id != exclude_attendance_id)
    duplicate = query.first()
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Duplicate attendance blocked: labour already marked for same date "
                f"(labour_id={duplicate.labour_id})"
            ),
        )


def _ensure_attendance_not_linked_to_active_bill(
    db: Session,
    attendance_id: int,
) -> None:
    linked_bill = (
        db.query(LabourBillItem.bill_id)
        .join(LabourBill, LabourBill.id == LabourBillItem.bill_id)
        .filter(
            LabourBillItem.attendance_id == attendance_id,
            LabourBill.status != "cancelled",
        )
        .first()
    )
    if linked_bill is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Attendance already linked to an active labour bill and cannot be edited "
                f"(bill_id={linked_bill.bill_id})"
            ),
        )


def _resolve_contractor_scope_or_400(
    db: Session,
    *,
    requested_contractor_id: int | None,
    labours: list[Labour],
) -> int | None:
    labour_contractor_ids = {
        labour.contractor_id for labour in labours if labour.contractor_id is not None
    }

    if requested_contractor_id is None:
        if len(labour_contractor_ids) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All attendance items must belong to a single contractor scope",
            )
        resolved = next(iter(labour_contractor_ids), None)
        if resolved is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contractor scope is required for attendance",
            )
        if resolved is not None:
            for labour in labours:
                if labour.contractor_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Labour contractor scope missing for "
                            f"labour_id={labour.id}"
                        ),
                    )
    else:
        resolved = requested_contractor_id
        for labour in labours:
            if labour.contractor_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Labour does not belong to requested contractor scope "
                        f"(labour_id={labour.id})"
                    ),
                )
            if labour.contractor_id != resolved:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Labour contractor scope mismatch for "
                        f"labour_id={labour.id}"
                    ),
                )

    _ensure_contractor_exists(db, resolved)
    return resolved


def _log_status_transition(
    db: Session,
    *,
    attendance: LabourAttendance,
    before_status: str,
    after_status: str,
    current_user: User,
) -> None:
    if before_status == after_status:
        return
    log_audit_event(
        db,
        entity_type="labour_attendance",
        entity_id=attendance.id,
        action="status_transition",
        performed_by=current_user,
        before_data={"status": before_status},
        after_data={"status": after_status},
        remarks=f"{before_status} -> {after_status}",
    )


def list_labour_attendances(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    project_id: int | None = None,
    contractor_id: int | None = None,
    status_filter: str | None = None,
    marked_by: int | None = None,
) -> dict[str, object]:
    company_id = resolve_company_scope(current_user)
    query = apply_labour_attendance_company_scope(
        db.query(LabourAttendance).options(joinedload(LabourAttendance.items)),
        company_id,
    )
    if project_id is not None:
        query = query.filter(LabourAttendance.project_id == project_id)
    if contractor_id is not None:
        query = query.filter(LabourAttendance.contractor_id == contractor_id)
    if marked_by is not None:
        query = query.filter(LabourAttendance.marked_by == marked_by)
    if status_filter:
        query = query.filter(LabourAttendance.status == _normalize_status(status_filter))
    return paginate_query(
        query.order_by(LabourAttendance.attendance_date.desc(), LabourAttendance.id.desc()),
        pagination=pagination,
    )


def get_labour_attendance_or_404(
    db: Session,
    attendance_id: int,
    *,
    lock_for_update: bool = False,
) -> LabourAttendance:
    query = (
        db.query(LabourAttendance)
        .options(joinedload(LabourAttendance.items))
        .filter(LabourAttendance.id == attendance_id)
    )
    if lock_for_update:
        query = apply_write_lock(query, db)
    attendance = query.first()
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labour attendance not found",
        )
    return attendance


def create_labour_attendance(
    db: Session,
    payload: LabourAttendanceCreate,
    current_user: User,
) -> LabourAttendance:
    data = payload.model_dump()
    attendance_date = data["date"]
    data["status"] = _normalize_status(data["status"])
    if data["status"] not in INITIAL_LABOUR_ATTENDANCE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Labour attendance can only be created in draft or submitted status",
        )
    data["remarks"] = _normalize_optional_text(data.get("remarks"))
    data["date"] = attendance_date
    data["attendance_date"] = attendance_date
    data["created_by"] = data.get("created_by") or current_user.id
    data["marked_by"] = data["created_by"]
    if data.get("muster_no"):
        data["muster_no"] = _normalize_muster_no(data["muster_no"])
    else:
        data["muster_no"] = _generate_muster_no(
            db,
            project_id=data["project_id"],
            attendance_date=attendance_date,
        )

    _ensure_unique_muster_no(db, data["muster_no"])
    _ensure_project_exists(db, data["project_id"])
    _ensure_user_exists(db, data["created_by"])

    raw_items = data.pop("items")
    labour_ids: set[int] = set()
    labour_map: dict[int, Labour] = {}
    for item in raw_items:
        labour_id = item["labour_id"]
        if labour_id in labour_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate labour_id in items: {labour_id}",
            )
        labour_ids.add(labour_id)
        labour_map[labour_id] = _ensure_labour_exists(db, labour_id)

    resolved_contractor_id = _resolve_contractor_scope_or_400(
        db,
        requested_contractor_id=data.get("contractor_id"),
        labours=list(labour_map.values()),
    )
    data["contractor_id"] = resolved_contractor_id
    touch_rows(labour_map.values())

    _assert_no_duplicate_attendance_for_labours(
        db,
        labour_ids=labour_ids,
        project_id=data["project_id"],
        attendance_date=attendance_date,
    )

    prepared_items: list[dict] = []
    total_wage = 0.0
    for item in raw_items:
        labour = labour_map[item["labour_id"]]
        attendance_status = _normalize_item_status(
            item.get("attendance_status", "present")
        )
        present_days = _resolve_present_days(attendance_status, item.get("present_days"))
        overtime_hours = float(item.get("overtime_hours", 0))
        wage_rate_raw = item.get("wage_rate")
        if wage_rate_raw is None:
            wage_rate = float(labour.daily_rate or labour.default_wage_rate or 0)
        else:
            wage_rate = float(wage_rate_raw)
        _validate_item_values(
            overtime_hours=overtime_hours,
            wage_rate=wage_rate,
        )
        line_amount = _calculate_line_amount(
            present_days=present_days,
            overtime_hours=overtime_hours,
            wage_rate=wage_rate,
        )
        total_wage += line_amount
        prepared_items.append(
            {
                "labour_id": labour.id,
                "attendance_status": attendance_status,
                "present_days": present_days,
                "overtime_hours": overtime_hours,
                "wage_rate": wage_rate,
                "line_amount": line_amount,
                "remarks": _normalize_optional_text(item.get("remarks")),
            }
        )

    data["total_wage"] = round(total_wage, 2)
    attendance = LabourAttendance(**data)
    db.add(attendance)
    flush_with_conflict_handling(db, entity_name="Labour attendance")

    attendance_items: list[LabourAttendanceItem] = []
    for item in prepared_items:
        attendance_items.append(
            LabourAttendanceItem(
                attendance_id=attendance.id,
                labour_id=item["labour_id"],
                attendance_status=item["attendance_status"],
                present_days=item["present_days"],
                overtime_hours=item["overtime_hours"],
                wage_rate=item["wage_rate"],
                line_amount=item["line_amount"],
                remarks=item["remarks"],
            )
        )
    db.add_all(attendance_items)
    flush_with_conflict_handling(db, entity_name="Labour attendance")

    log_audit_event(
        db,
        entity_type="labour_attendance",
        entity_id=attendance.id,
        action="create",
        performed_by=current_user,
        after_data=_serialize_attendance(attendance),
        remarks=attendance.muster_no,
    )
    commit_with_conflict_handling(db, entity_name="Labour attendance")
    return get_labour_attendance_or_404(db, attendance.id)


def update_labour_attendance(
    db: Session,
    attendance_id: int,
    payload: LabourAttendanceUpdate,
    current_user: User,
) -> LabourAttendance:
    attendance = get_labour_attendance_or_404(
        db,
        attendance_id,
        lock_for_update=True,
    )
    if attendance.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancelled labour attendance is immutable",
        )
    _ensure_attendance_not_linked_to_active_bill(db, attendance.id)
    updates = payload.model_dump(exclude_unset=True)

    if "date" in updates and updates["date"] is not None:
        updates["attendance_date"] = updates["date"]
    if "created_by" in updates and updates["created_by"] is not None:
        updates["marked_by"] = updates["created_by"]

    for field in ("muster_no", "marked_by", "attendance_date", "status"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} cannot be null",
            )

    if "muster_no" in updates and updates["muster_no"] is not None:
        updates["muster_no"] = _normalize_muster_no(updates["muster_no"])
        _ensure_unique_muster_no(
            db,
            updates["muster_no"],
            exclude_attendance_id=attendance.id,
        )
    if "status" in updates and updates["status"] is not None:
        updates["status"] = _normalize_status(updates["status"])
        _validate_status_transition(
            current_status=attendance.status,
            target_status=updates["status"],
        )
    if "remarks" in updates:
        updates["remarks"] = _normalize_optional_text(updates["remarks"])

    next_marked_by = updates.get("marked_by", attendance.marked_by)
    _ensure_user_exists(db, next_marked_by)

    next_attendance_date = updates.get("attendance_date", attendance.attendance_date)
    next_status = updates.get("status", attendance.status)

    existing_item_map = {item.id: item for item in attendance.items}
    next_item_values: dict[int, dict[str, float | str | None | int]] = {
        item.id: {
            "labour_id": item.labour_id,
            "attendance_status": item.attendance_status,
            "present_days": float(item.present_days),
            "overtime_hours": float(item.overtime_hours),
            "wage_rate": float(item.wage_rate),
            "line_amount": float(item.line_amount),
            "remarks": item.remarks,
        }
        for item in attendance.items
    }

    if "items" in updates and updates["items"] is not None:
        seen_item_ids: set[int] = set()
        for item_update in updates["items"]:
            item_id = item_update["id"]
            if item_id in seen_item_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate attendance item id in update payload: {item_id}",
                )
            seen_item_ids.add(item_id)
            item = existing_item_map.get(item_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Labour attendance item not found for id={item_id}",
                )

            if "attendance_status" in item_update and item_update["attendance_status"] is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="attendance_status cannot be null",
                )
            for field in ("present_days", "overtime_hours", "wage_rate"):
                if field in item_update and item_update[field] is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"{field} cannot be null",
                    )

            labour = _ensure_labour_exists(db, item.labour_id)
            attendance_status = _normalize_item_status(
                item_update.get(
                    "attendance_status",
                    str(next_item_values[item_id]["attendance_status"]),
                )
            )
            present_days = _resolve_present_days(
                attendance_status,
                (
                    item_update["present_days"]
                    if "present_days" in item_update
                    else float(next_item_values[item_id]["present_days"])
                ),
            )
            overtime_hours = float(
                item_update["overtime_hours"]
                if "overtime_hours" in item_update
                else float(next_item_values[item_id]["overtime_hours"])
            )
            wage_rate = float(
                item_update["wage_rate"]
                if "wage_rate" in item_update
                else float(next_item_values[item_id]["wage_rate"])
            )
            if "wage_rate" not in item_update and next_item_values[item_id]["wage_rate"] == 0:
                wage_rate = float(labour.daily_rate or labour.default_wage_rate or 0)
            _validate_item_values(
                overtime_hours=overtime_hours,
                wage_rate=wage_rate,
            )
            line_amount = _calculate_line_amount(
                present_days=present_days,
                overtime_hours=overtime_hours,
                wage_rate=wage_rate,
            )
            next_item_values[item_id]["attendance_status"] = attendance_status
            next_item_values[item_id]["present_days"] = present_days
            next_item_values[item_id]["overtime_hours"] = overtime_hours
            next_item_values[item_id]["wage_rate"] = wage_rate
            next_item_values[item_id]["line_amount"] = line_amount
            if "remarks" in item_update:
                next_item_values[item_id]["remarks"] = _normalize_optional_text(
                    item_update["remarks"]
                )

    labour_ids = {item.labour_id for item in attendance.items}
    labours = [_ensure_labour_exists(db, labour_id) for labour_id in labour_ids]
    next_contractor_id = updates.get("contractor_id", attendance.contractor_id)
    next_contractor_id = _resolve_contractor_scope_or_400(
        db,
        requested_contractor_id=next_contractor_id,
        labours=labours,
    )
    updates["contractor_id"] = next_contractor_id
    touch_rows(labours)

    if next_status != "cancelled":
        _assert_no_duplicate_attendance_for_labours(
            db,
            labour_ids=labour_ids,
            project_id=attendance.project_id,
            attendance_date=next_attendance_date,
            exclude_attendance_id=attendance.id,
        )

    before_data = _serialize_attendance(attendance)
    before_status = attendance.status
    for field in (
        "muster_no",
        "contractor_id",
        "date",
        "attendance_date",
        "created_by",
        "marked_by",
        "status",
        "remarks",
    ):
        if field in updates:
            setattr(attendance, field, updates[field])

    total_wage = 0.0
    for item in attendance.items:
        item_values = next_item_values[item.id]
        item.attendance_status = str(item_values["attendance_status"])
        item.present_days = float(item_values["present_days"])
        item.overtime_hours = float(item_values["overtime_hours"])
        item.wage_rate = float(item_values["wage_rate"])
        item.line_amount = float(item_values["line_amount"])
        item.remarks = item_values["remarks"]
        total_wage += float(item_values["line_amount"])
    attendance.total_wage = round(total_wage, 2)

    flush_with_conflict_handling(db, entity_name="Labour attendance")
    log_audit_event(
        db,
        entity_type="labour_attendance",
        entity_id=attendance.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=_serialize_attendance(attendance),
        remarks=attendance.muster_no,
    )
    _log_status_transition(
        db,
        attendance=attendance,
        before_status=before_status,
        after_status=attendance.status,
        current_user=current_user,
    )
    commit_with_conflict_handling(db, entity_name="Labour attendance")
    return get_labour_attendance_or_404(db, attendance.id)
