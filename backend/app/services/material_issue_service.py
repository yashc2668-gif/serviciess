"""Material issue service helpers."""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.material import Material
from app.models.contract import Contract
from app.models.material_issue import MaterialIssue
from app.models.material_issue_item import MaterialIssueItem
from app.models.project import Project
from app.models.user import User
from app.schemas.material_issue import MaterialIssueCreate, MaterialIssueUpdate
from app.services.inventory_service import record_inventory_transactions_from_stock_deltas
from app.services.audit_service import (
    log_audit_event,
    serialize_model,
    serialize_models,
)
from app.services.company_scope_service import (
    apply_material_issue_company_scope,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    apply_write_lock,
    commit_with_conflict_handling,
    flush_with_conflict_handling,
)
from app.utils.pagination import PaginationParams, paginate_query

VALID_ISSUE_STATUSES = {"draft", "issued", "cancelled"}
MATERIAL_ISSUE_ALLOWED_STATUS_TRANSITIONS = {
    "draft": {"issued", "cancelled"},
    "issued": {"cancelled"},
    "cancelled": set(),
}


def _normalize_status(raw_status: str) -> str:
    normalized = raw_status.strip().lower()
    if normalized not in VALID_ISSUE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid issue status. Allowed values: draft, issued, cancelled",
        )
    return normalized


def _normalize_issue_no(raw_issue_no: str) -> str:
    normalized = raw_issue_no.strip().upper()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="issue_no cannot be empty",
        )
    return normalized


def _normalize_optional_text(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    return raw_value.strip() or None


def _validate_status_transition(*, current_status: str, target_status: str) -> None:
    if target_status == current_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Material issue is already {target_status}",
        )
    allowed_statuses = MATERIAL_ISSUE_ALLOWED_STATUS_TRANSITIONS.get(
        current_status,
        set(),
    )
    if target_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid material issue status transition: "
                f"{current_status} -> {target_status}"
            ),
        )


def _ensure_unique_issue_no(
    db: Session,
    issue_no: str,
    *,
    exclude_issue_id: int | None = None,
) -> None:
    query = db.query(MaterialIssue).filter(
        func.lower(MaterialIssue.issue_no) == issue_no.lower()
    )
    if exclude_issue_id is not None:
        query = query.filter(MaterialIssue.id != exclude_issue_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Issue number already exists",
        )


def _ensure_project_exists(db: Session, project_id: int) -> None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
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


def _ensure_user_exists(db: Session, user_id: int) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issued by user not found",
        )


def _get_material_for_project_or_400(
    db: Session,
    material_id: int,
    project_id: int,
) -> Material:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Material not found for material_id={material_id}",
        )
    if not material.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Material is inactive for material_id={material_id}",
        )
    if material.project_id is not None and material.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Material {material_id} does not belong to project {project_id}",
        )
    return material


def _validate_item_values(*, issued_qty: float, unit_rate: float) -> None:
    if issued_qty <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="issued_qty must be greater than 0",
        )
    if unit_rate < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unit_rate cannot be negative",
        )


def _calculate_line_amount(*, issued_qty: float, unit_rate: float) -> float:
    return round(issued_qty * unit_rate, 2)


def _serialize_issue(issue: MaterialIssue) -> dict:
    return {
        "issue": serialize_model(issue),
        "items": serialize_models(list(issue.items)),
    }


def _apply_stock_deltas(db: Session, stock_deltas: dict[int, float]) -> None:
    if not stock_deltas:
        return
    material_ids = list(stock_deltas.keys())
    materials = (
        apply_write_lock(
            db.query(Material).filter(Material.id.in_(material_ids)),
            db,
        )
        .order_by(Material.id.asc())
        .all()
    )
    material_map = {material.id: material for material in materials}
    for material_id, delta in stock_deltas.items():
        material = material_map.get(material_id)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material not found for material_id={material_id}",
            )
        next_stock = round(float(material.current_stock) + float(delta), 3)
        if next_stock < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Stock adjustment would make current_stock negative for "
                    f"material_id={material_id}"
                ),
            )
        material.current_stock = next_stock


def list_material_issues(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    project_id: int | None = None,
    contract_id: int | None = None,
    status_filter: str | None = None,
    issued_by: int | None = None,
) -> dict[str, object]:
    company_id = resolve_company_scope(current_user)
    query = apply_material_issue_company_scope(
        db.query(MaterialIssue).options(joinedload(MaterialIssue.items)),
        company_id,
    )
    if project_id is not None:
        query = query.filter(MaterialIssue.project_id == project_id)
    if contract_id is not None:
        query = query.filter(MaterialIssue.contract_id == contract_id)
    if issued_by is not None:
        query = query.filter(MaterialIssue.issued_by == issued_by)
    if status_filter:
        query = query.filter(MaterialIssue.status == _normalize_status(status_filter))
    return paginate_query(
        query.order_by(MaterialIssue.issue_date.desc(), MaterialIssue.id.desc()),
        pagination=pagination,
    )


def get_material_issue_or_404(db: Session, issue_id: int) -> MaterialIssue:
    issue = (
        db.query(MaterialIssue)
        .options(joinedload(MaterialIssue.items))
        .filter(MaterialIssue.id == issue_id)
        .first()
    )
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material issue not found",
        )
    return issue


def create_material_issue(
    db: Session,
    payload: MaterialIssueCreate,
    current_user: User,
) -> MaterialIssue:
    data = payload.model_dump()
    data["issue_no"] = _normalize_issue_no(data["issue_no"])
    data["status"] = _normalize_status(data["status"])
    data["issued_by"] = data.get("issued_by") or current_user.id
    data["remarks"] = _normalize_optional_text(data.get("remarks"))
    data["site_name"] = _normalize_optional_text(data.get("site_name"))
    data["activity_name"] = _normalize_optional_text(data.get("activity_name"))

    _ensure_unique_issue_no(db, data["issue_no"])
    _ensure_project_exists(db, data["project_id"])
    _ensure_contract_exists_for_project(
        db,
        contract_id=data.get("contract_id"),
        project_id=data["project_id"],
    )
    _ensure_user_exists(db, data["issued_by"])

    raw_items = data.pop("items")
    material_ids: set[int] = set()
    prepared_items: list[dict] = []
    total_amount = 0.0
    for item in raw_items:
        material_id = item["material_id"]
        if material_id in material_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate material_id in items: {material_id}",
            )
        material_ids.add(material_id)
        _get_material_for_project_or_400(db, material_id, data["project_id"])

        issued_qty = float(item["issued_qty"])
        unit_rate = float(item.get("unit_rate", 0))
        _validate_item_values(issued_qty=issued_qty, unit_rate=unit_rate)
        line_amount = _calculate_line_amount(issued_qty=issued_qty, unit_rate=unit_rate)
        total_amount += line_amount
        prepared_items.append(
            {
                "material_id": material_id,
                "issued_qty": issued_qty,
                "unit_rate": unit_rate,
                "line_amount": line_amount,
            }
        )

    data["total_amount"] = round(total_amount, 2)
    issue = MaterialIssue(**data)
    db.add(issue)
    flush_with_conflict_handling(db, entity_name="Material issue")

    issue_items: list[MaterialIssueItem] = []
    for item in prepared_items:
        issue_item = MaterialIssueItem(
            issue_id=issue.id,
            material_id=item["material_id"],
            issued_qty=item["issued_qty"],
            unit_rate=item["unit_rate"],
            line_amount=item["line_amount"],
        )
        issue_items.append(issue_item)
    db.add_all(issue_items)
    flush_with_conflict_handling(db, entity_name="Material issue")

    if issue.status == "issued":
        stock_deltas = {item["material_id"]: -item["issued_qty"] for item in prepared_items}
        _apply_stock_deltas(db, stock_deltas)
        record_inventory_transactions_from_stock_deltas(
            db,
            stock_deltas=stock_deltas,
            transaction_type="material_issue",
            transaction_date=issue.issue_date,
            reference_type="material_issue",
            reference_id=issue.id,
            project_id=issue.project_id,
            remarks=issue.remarks,
        )

    log_audit_event(
        db,
        entity_type="material_issue",
        entity_id=issue.id,
        action="create",
        performed_by=current_user,
        after_data=_serialize_issue(issue),
        remarks=issue.issue_no,
    )
    commit_with_conflict_handling(db, entity_name="Material issue")
    return get_material_issue_or_404(db, issue.id)


def update_material_issue(
    db: Session,
    issue_id: int,
    payload: MaterialIssueUpdate,
    current_user: User,
) -> MaterialIssue:
    issue = get_material_issue_or_404(db, issue_id)
    if issue.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancelled material issue is immutable",
        )
    updates = payload.model_dump(exclude_unset=True)

    for field in ("issue_no", "project_id", "issued_by", "issue_date", "status"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} cannot be null",
            )

    if "issue_no" in updates and updates["issue_no"] is not None:
        updates["issue_no"] = _normalize_issue_no(updates["issue_no"])
        _ensure_unique_issue_no(
            db,
            updates["issue_no"],
            exclude_issue_id=issue.id,
        )
    if "status" in updates and updates["status"] is not None:
        updates["status"] = _normalize_status(updates["status"])
        _validate_status_transition(
            current_status=issue.status,
            target_status=updates["status"],
        )
    for field in ("remarks", "site_name", "activity_name"):
        if field in updates:
            updates[field] = _normalize_optional_text(updates[field])

    next_project_id = updates.get("project_id", issue.project_id)
    next_contract_id = updates.get("contract_id", issue.contract_id)
    next_issued_by = updates.get("issued_by", issue.issued_by)
    next_status = updates.get("status", issue.status)

    _ensure_project_exists(db, next_project_id)
    _ensure_contract_exists_for_project(
        db,
        contract_id=next_contract_id,
        project_id=next_project_id,
    )
    _ensure_user_exists(db, next_issued_by)

    existing_item_map = {item.id: item for item in issue.items}
    next_item_values: dict[int, dict[str, float]] = {
        item.id: {
            "issued_qty": float(item.issued_qty),
            "unit_rate": float(item.unit_rate),
            "line_amount": float(item.line_amount),
            "material_id": item.material_id,
        }
        for item in issue.items
    }

    if "items" in updates and updates["items"] is not None:
        seen_item_ids: set[int] = set()
        for item_update in updates["items"]:
            item_id = item_update["id"]
            if item_id in seen_item_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate issue item id in update payload: {item_id}",
                )
            seen_item_ids.add(item_id)
            item = existing_item_map.get(item_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Material issue item not found for id={item_id}",
                )
            for field in ("issued_qty", "unit_rate"):
                if field in item_update and item_update[field] is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"{field} cannot be null",
                    )

            issued_qty = float(
                item_update["issued_qty"]
                if "issued_qty" in item_update
                else next_item_values[item_id]["issued_qty"]
            )
            unit_rate = float(
                item_update["unit_rate"]
                if "unit_rate" in item_update
                else next_item_values[item_id]["unit_rate"]
            )
            _validate_item_values(issued_qty=issued_qty, unit_rate=unit_rate)
            line_amount = _calculate_line_amount(
                issued_qty=issued_qty,
                unit_rate=unit_rate,
            )
            next_item_values[item_id]["issued_qty"] = issued_qty
            next_item_values[item_id]["unit_rate"] = unit_rate
            next_item_values[item_id]["line_amount"] = line_amount

    for item in issue.items:
        _get_material_for_project_or_400(
            db,
            item.material_id,
            next_project_id,
        )

    before_data = _serialize_issue(issue)

    stock_deltas: dict[int, float] = {}
    for item in issue.items:
        old_effective_qty = float(item.issued_qty) if issue.status == "issued" else 0.0
        new_effective_qty = (
            next_item_values[item.id]["issued_qty"] if next_status == "issued" else 0.0
        )
        delta = round(old_effective_qty - new_effective_qty, 3)
        if delta != 0:
            stock_deltas[item.material_id] = stock_deltas.get(item.material_id, 0.0) + delta

    for field in (
        "issue_no",
        "project_id",
        "contract_id",
        "issued_by",
        "issue_date",
        "status",
        "site_name",
        "activity_name",
        "remarks",
    ):
        if field in updates:
            setattr(issue, field, updates[field])

    total_amount = 0.0
    for item in issue.items:
        item_values = next_item_values[item.id]
        item.issued_qty = item_values["issued_qty"]
        item.unit_rate = item_values["unit_rate"]
        item.line_amount = item_values["line_amount"]
        total_amount += item_values["line_amount"]
    issue.total_amount = round(total_amount, 2)

    _apply_stock_deltas(db, stock_deltas)
    record_inventory_transactions_from_stock_deltas(
        db,
        stock_deltas=stock_deltas,
        transaction_type="material_issue_adjustment",
        transaction_date=issue.issue_date,
        reference_type="material_issue",
        reference_id=issue.id,
        project_id=issue.project_id,
        remarks=issue.remarks,
    )
    flush_with_conflict_handling(db, entity_name="Material issue")

    log_audit_event(
        db,
        entity_type="material_issue",
        entity_id=issue.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=_serialize_issue(issue),
        remarks=issue.issue_no,
    )
    commit_with_conflict_handling(db, entity_name="Material issue")
    return get_material_issue_or_404(db, issue.id)
