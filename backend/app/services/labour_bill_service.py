"""Labour bill service helpers."""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.labour_attendance import LabourAttendance
from app.models.labour_bill import LabourBill
from app.models.labour_bill_item import LabourBillItem
from app.models.labour_contractor import LabourContractor
from app.models.contract import Contract
from app.models.project import Project
from app.models.user import User
from app.schemas.labour_bill import LabourBillCreate, LabourBillUpdate
from app.services.audit_service import (
    log_audit_event,
    serialize_model,
    serialize_models,
)
from app.services.company_scope_service import (
    apply_labour_bill_company_scope,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    apply_write_lock,
    commit_with_conflict_handling,
    flush_with_conflict_handling,
    touch_rows,
)
from app.utils.pagination import PaginationParams, paginate_query

VALID_LABOUR_BILL_STATUSES = {"draft", "submitted", "approved", "paid", "cancelled"}
INITIAL_LABOUR_BILL_STATUSES = {"draft", "submitted"}
LABOUR_BILL_ALLOWED_STATUS_TRANSITIONS = {
    "draft": {"submitted", "cancelled"},
    "submitted": {"approved", "cancelled"},
    "approved": {"paid", "cancelled"},
    "paid": set(),
    "cancelled": set(),
}


def _normalize_status(raw_status: str) -> str:
    normalized = raw_status.strip().lower()
    if normalized not in VALID_LABOUR_BILL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid labour bill status. Allowed values: "
                "draft, submitted, approved, paid, cancelled"
            ),
        )
    return normalized


def _normalize_bill_no(raw_bill_no: str) -> str:
    normalized = raw_bill_no.strip().upper()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="bill_no cannot be empty",
        )
    return normalized


def _validate_status_transition(*, current_status: str, target_status: str) -> None:
    if target_status == current_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Labour bill is already {target_status}",
        )
    allowed_statuses = LABOUR_BILL_ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
    if target_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid labour bill status transition: "
                f"{current_status} -> {target_status}"
            ),
        )


def _normalize_optional_text(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    return raw_value.strip() or None


def _ensure_unique_bill_no(
    db: Session,
    bill_no: str,
    *,
    exclude_bill_id: int | None = None,
) -> None:
    query = db.query(LabourBill).filter(func.lower(LabourBill.bill_no) == bill_no.lower())
    if exclude_bill_id is not None:
        query = query.filter(LabourBill.id != exclude_bill_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bill number already exists",
        )


def _ensure_project_exists(db: Session, project_id: int) -> None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )


def _ensure_contractor_exists(db: Session, contractor_id: int) -> None:
    contractor = (
        db.query(LabourContractor).filter(LabourContractor.id == contractor_id).first()
    )
    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labour contractor not found",
        )


def _ensure_contract_exists_for_project(
    db: Session,
    *,
    contract_id: int | None,
    project_id: int,
) -> None:
    if contract_id is None:
        return
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )
    if contract.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract does not belong to the selected project",
        )


def _validate_period_and_amounts(*, period_start, period_end, gross_amount: float, deductions: float):
    if period_end < period_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period_end cannot be before period_start",
        )
    if deductions > gross_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="deductions cannot be greater than gross_amount",
        )


def _serialize_bill(bill: LabourBill) -> dict:
    return {
        "bill": serialize_model(bill),
        "items": serialize_models(list(bill.items)),
    }


def _load_approved_attendances_for_bill(
    db: Session,
    *,
    attendance_ids: list[int],
    project_id: int,
    contractor_id: int,
    period_start,
    period_end,
    exclude_bill_id: int | None = None,
) -> list[LabourAttendance]:
    unique_ids = list(dict.fromkeys(attendance_ids))
    attendances = (
        apply_write_lock(
            db.query(LabourAttendance)
            .options(joinedload(LabourAttendance.items))
            .filter(LabourAttendance.id.in_(unique_ids)),
            db,
        )
        .order_by(LabourAttendance.id.asc())
        .all()
    )
    attendance_map = {attendance.id: attendance for attendance in attendances}
    missing_ids = [attendance_id for attendance_id in unique_ids if attendance_id not in attendance_map]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attendance not found for id(s): {', '.join(map(str, missing_ids))}",
        )

    existing_link = (
        db.query(LabourBillItem.attendance_id)
        .join(LabourBill, LabourBill.id == LabourBillItem.bill_id)
        .filter(
            LabourBillItem.attendance_id.in_(unique_ids),
            LabourBill.status != "cancelled",
        )
    )
    if exclude_bill_id is not None:
        existing_link = existing_link.filter(LabourBill.id != exclude_bill_id)
    already_billed = existing_link.first()
    if already_billed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Attendance already linked to another active bill "
                f"(attendance_id={already_billed.attendance_id})"
            ),
        )

    resolved_attendances = [attendance_map[attendance_id] for attendance_id in unique_ids]
    for attendance in resolved_attendances:
        if attendance.status != "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Labour bill can be generated only from approved attendance "
                    f"(attendance_id={attendance.id})"
                ),
            )
        if attendance.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Attendance project mismatch for labour bill generation "
                    f"(attendance_id={attendance.id})"
                ),
            )
        if attendance.contractor_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Attendance must have contractor scope before bill generation "
                    f"(attendance_id={attendance.id})"
                ),
            )
        if attendance.contractor_id != contractor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Attendance contractor scope mismatch for labour bill "
                    f"(attendance_id={attendance.id})"
                ),
            )
        attendance_date = attendance.attendance_date
        if attendance_date < period_start or attendance_date > period_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Attendance date not inside bill period "
                    f"(attendance_id={attendance.id})"
                ),
            )
    return resolved_attendances


def _build_items_from_attendances(attendances: list[LabourAttendance]) -> tuple[list[dict], float]:
    item_dicts: list[dict] = []
    gross_amount = 0.0
    for attendance in attendances:
        for attendance_item in attendance.items:
            amount = round(float(attendance_item.line_amount), 2)
            if amount <= 0:
                continue
            quantity = round(
                float(attendance_item.present_days) + (float(attendance_item.overtime_hours) / 8.0),
                3,
            )
            rate = float(attendance_item.wage_rate)
            item_dicts.append(
                {
                    "attendance_id": attendance.id,
                    "labour_id": attendance_item.labour_id,
                    "description": f"Attendance {attendance.muster_no}",
                    "quantity": quantity,
                    "rate": rate,
                    "amount": amount,
                }
            )
            gross_amount += amount
    return item_dicts, round(gross_amount, 2)


def _build_manual_items(items_payload: list[dict]) -> tuple[list[dict], float]:
    item_dicts: list[dict] = []
    gross_amount = 0.0
    for item in items_payload:
        quantity = round(float(item.get("quantity", 0)), 3)
        rate = round(float(item.get("rate", 0)), 2)
        amount_raw = item.get("amount")
        amount = round(float(amount_raw), 2) if amount_raw is not None else round(quantity * rate, 2)
        if quantity < 0 or rate < 0 or amount < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Labour bill item values cannot be negative",
            )
        item_dicts.append(
            {
                "attendance_id": item.get("attendance_id"),
                "labour_id": item.get("labour_id"),
                "description": _normalize_optional_text(item.get("description")),
                "quantity": quantity,
                "rate": rate,
                "amount": amount,
            }
        )
        gross_amount += amount
    return item_dicts, round(gross_amount, 2)


def _replace_bill_items(db: Session, bill: LabourBill, item_dicts: list[dict]) -> None:
    for existing in list(bill.items):
        db.delete(existing)
    flush_with_conflict_handling(db, entity_name="Labour bill")

    new_items = [
        LabourBillItem(
            bill_id=bill.id,
            attendance_id=item["attendance_id"],
            labour_id=item["labour_id"],
            description=item["description"],
            quantity=item["quantity"],
            rate=item["rate"],
            amount=item["amount"],
        )
        for item in item_dicts
    ]
    if new_items:
        db.add_all(new_items)
    flush_with_conflict_handling(db, entity_name="Labour bill")


def _ensure_bill_ready_for_approval(db: Session, bill: LabourBill) -> None:
    attendance_ids = [item.attendance_id for item in bill.items if item.attendance_id is not None]
    if not attendance_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approved or paid labour bill must be generated from approved attendance",
        )
    approved_ids = {
        row.id
        for row in db.query(LabourAttendance.id).filter(
            LabourAttendance.id.in_(attendance_ids),
            LabourAttendance.status == "approved",
        )
    }
    missing_approved = [attendance_id for attendance_id in attendance_ids if attendance_id not in approved_ids]
    if missing_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Bill contains attendance that is not approved: "
                f"{', '.join(map(str, missing_approved))}"
            ),
        )


def _log_status_transition(
    db: Session,
    *,
    bill: LabourBill,
    before_status: str,
    after_status: str,
    current_user: User,
) -> None:
    if before_status == after_status:
        return
    log_audit_event(
        db,
        entity_type="labour_bill",
        entity_id=bill.id,
        action="status_transition",
        performed_by=current_user,
        before_data={"status": before_status},
        after_data={"status": after_status},
        remarks=f"{before_status} -> {after_status}",
    )


def list_labour_bills(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    project_id: int | None = None,
    contract_id: int | None = None,
    contractor_id: int | None = None,
    status_filter: str | None = None,
) -> dict[str, object]:
    company_id = resolve_company_scope(current_user)
    query = apply_labour_bill_company_scope(
        db.query(LabourBill).options(joinedload(LabourBill.items)),
        company_id,
    )
    if project_id is not None:
        query = query.filter(LabourBill.project_id == project_id)
    if contract_id is not None:
        query = query.filter(LabourBill.contract_id == contract_id)
    if contractor_id is not None:
        query = query.filter(LabourBill.contractor_id == contractor_id)
    if status_filter:
        query = query.filter(LabourBill.status == _normalize_status(status_filter))
    return paginate_query(
        query.order_by(LabourBill.period_end.desc(), LabourBill.id.desc()),
        pagination=pagination,
    )


def get_labour_bill_or_404(
    db: Session,
    bill_id: int,
    *,
    lock_for_update: bool = False,
) -> LabourBill:
    query = (
        db.query(LabourBill)
        .options(joinedload(LabourBill.items))
        .filter(LabourBill.id == bill_id)
    )
    if lock_for_update:
        query = apply_write_lock(query, db)
    bill = query.first()
    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labour bill not found",
        )
    return bill


def create_labour_bill(
    db: Session,
    payload: LabourBillCreate,
    current_user: User,
) -> LabourBill:
    data = payload.model_dump()
    data["bill_no"] = _normalize_bill_no(data["bill_no"])
    data["status"] = _normalize_status(data["status"])
    if data["status"] not in INITIAL_LABOUR_BILL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Labour bill can only be created in draft or submitted status",
        )
    data["remarks"] = _normalize_optional_text(data.get("remarks"))

    attendance_ids = data.pop("attendance_ids", None)
    manual_items_payload = data.pop("items", None)

    _ensure_unique_bill_no(db, data["bill_no"])
    _ensure_project_exists(db, data["project_id"])
    _ensure_contract_exists_for_project(
        db,
        contract_id=data.get("contract_id"),
        project_id=data["project_id"],
    )
    _ensure_contractor_exists(db, data["contractor_id"])

    period_start = data["period_start"]
    period_end = data["period_end"]

    item_dicts: list[dict] = []
    attendances: list[LabourAttendance] = []
    if attendance_ids:
        attendances = _load_approved_attendances_for_bill(
            db,
            attendance_ids=attendance_ids,
            project_id=data["project_id"],
            contractor_id=data["contractor_id"],
            period_start=period_start,
            period_end=period_end,
        )
        item_dicts, gross_amount = _build_items_from_attendances(attendances)
    elif manual_items_payload:
        item_dicts, gross_amount = _build_manual_items(manual_items_payload)
        if data["status"] in {"approved", "paid"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approved or paid labour bill must be generated from approved attendance",
            )
    else:
        gross_amount = float(data.get("gross_amount", 0))

    deductions = float(data.get("deductions", 0))
    _validate_period_and_amounts(
        period_start=period_start,
        period_end=period_end,
        gross_amount=gross_amount,
        deductions=deductions,
    )
    net_payable = round(gross_amount - deductions, 2)
    data["gross_amount"] = gross_amount
    data["net_amount"] = net_payable
    data["net_payable"] = net_payable

    bill = LabourBill(**data)
    db.add(bill)
    flush_with_conflict_handling(db, entity_name="Labour bill")

    if item_dicts:
        touch_rows(attendances if attendance_ids else [])
        _replace_bill_items(db, bill, item_dicts)

    if bill.status in {"approved", "paid"}:
        _ensure_bill_ready_for_approval(db, bill)

    log_audit_event(
        db,
        entity_type="labour_bill",
        entity_id=bill.id,
        action="create",
        performed_by=current_user,
        after_data=_serialize_bill(bill),
        remarks=bill.bill_no,
    )
    commit_with_conflict_handling(db, entity_name="Labour bill")
    return get_labour_bill_or_404(db, bill.id)


def update_labour_bill(
    db: Session,
    bill_id: int,
    payload: LabourBillUpdate,
    current_user: User,
) -> LabourBill:
    bill = get_labour_bill_or_404(db, bill_id, lock_for_update=True)
    if bill.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paid labour bill is immutable",
        )
    if bill.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancelled labour bill is immutable",
        )

    updates = payload.model_dump(exclude_unset=True)

    if "bill_no" in updates and updates["bill_no"] is not None:
        updates["bill_no"] = _normalize_bill_no(updates["bill_no"])
        _ensure_unique_bill_no(db, updates["bill_no"], exclude_bill_id=bill.id)
    if "status" in updates and updates["status"] is not None:
        updates["status"] = _normalize_status(updates["status"])
        _validate_status_transition(
            current_status=bill.status,
            target_status=updates["status"],
        )
    if "remarks" in updates:
        updates["remarks"] = _normalize_optional_text(updates["remarks"])

    next_project_id = updates.get("project_id", bill.project_id)
    next_contract_id = updates.get("contract_id", bill.contract_id)
    next_contractor_id = updates.get("contractor_id", bill.contractor_id)
    next_period_start = updates.get("period_start", bill.period_start)
    next_period_end = updates.get("period_end", bill.period_end)
    next_status = updates.get("status", bill.status)

    _ensure_project_exists(db, next_project_id)
    _ensure_contract_exists_for_project(
        db,
        contract_id=next_contract_id,
        project_id=next_project_id,
    )
    _ensure_contractor_exists(db, next_contractor_id)

    attendance_ids = updates.pop("attendance_ids", None)
    manual_items_payload = updates.pop("items", None)
    updates.pop("net_payable", None)

    item_dicts: list[dict] | None = None
    gross_amount_from_items: float | None = None
    attendances: list[LabourAttendance] = []
    existing_attendance_ids = [
        item.attendance_id for item in bill.items if item.attendance_id is not None
    ]
    if attendance_ids is not None:
        attendances = _load_approved_attendances_for_bill(
            db,
            attendance_ids=attendance_ids,
            project_id=next_project_id,
            contractor_id=next_contractor_id,
            period_start=next_period_start,
            period_end=next_period_end,
            exclude_bill_id=bill.id,
        )
        item_dicts, gross_amount_from_items = _build_items_from_attendances(attendances)
    elif manual_items_payload is not None:
        item_dicts, gross_amount_from_items = _build_manual_items(manual_items_payload)
    else:
        if existing_attendance_ids:
            attendances = _load_approved_attendances_for_bill(
                db,
                attendance_ids=existing_attendance_ids,
                project_id=next_project_id,
                contractor_id=next_contractor_id,
                period_start=next_period_start,
                period_end=next_period_end,
                exclude_bill_id=bill.id,
            )

    if next_status in {"approved", "paid"} and manual_items_payload is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approved or paid labour bill must be generated from approved attendance",
        )

    if gross_amount_from_items is not None:
        next_gross = gross_amount_from_items
    else:
        next_gross = float(updates.get("gross_amount", bill.gross_amount))
    next_deductions = float(updates.get("deductions", bill.deductions))

    _validate_period_and_amounts(
        period_start=next_period_start,
        period_end=next_period_end,
        gross_amount=next_gross,
        deductions=next_deductions,
    )
    net_payable = round(next_gross - next_deductions, 2)
    updates["gross_amount"] = next_gross
    updates["net_amount"] = net_payable
    updates["net_payable"] = net_payable

    before_data = _serialize_bill(bill)
    before_status = bill.status

    for field in (
        "bill_no",
        "project_id",
        "contract_id",
        "contractor_id",
        "period_start",
        "period_end",
        "status",
        "gross_amount",
        "deductions",
        "net_amount",
        "net_payable",
        "remarks",
    ):
        if field in updates:
            setattr(bill, field, updates[field])

    if item_dicts is not None:
        touch_rows(attendances if attendance_ids is not None else [])
        _replace_bill_items(db, bill, item_dicts)
    elif attendances:
        touch_rows(attendances)

    if bill.status in {"approved", "paid"}:
        _ensure_bill_ready_for_approval(db, bill)

    flush_with_conflict_handling(db, entity_name="Labour bill")
    log_audit_event(
        db,
        entity_type="labour_bill",
        entity_id=bill.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=_serialize_bill(bill),
        remarks=bill.bill_no,
    )
    _log_status_transition(
        db,
        bill=bill,
        before_status=before_status,
        after_status=bill.status,
        current_user=current_user,
    )
    commit_with_conflict_handling(db, entity_name="Labour bill")
    return get_labour_bill_or_404(db, bill.id)
