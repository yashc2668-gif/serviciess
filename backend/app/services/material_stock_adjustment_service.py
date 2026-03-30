"""Material stock adjustment service helpers."""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.material import Material
from app.models.material_stock_adjustment import MaterialStockAdjustment
from app.models.material_stock_adjustment_item import MaterialStockAdjustmentItem
from app.models.project import Project
from app.models.user import User
from app.schemas.material_stock_adjustment import (
    MaterialStockAdjustmentCreate,
    MaterialStockAdjustmentUpdate,
)
from app.services.audit_service import (
    log_audit_event,
    serialize_model,
    serialize_models,
)
from app.services.company_scope_service import (
    apply_material_stock_adjustment_company_scope,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    apply_write_lock,
    commit_with_conflict_handling,
    flush_with_conflict_handling,
)
from app.services.inventory_service import record_inventory_transactions_from_stock_deltas
from app.utils.pagination import PaginationParams, paginate_query

VALID_STOCK_ADJUSTMENT_STATUSES = {"draft", "posted", "cancelled"}
MATERIAL_STOCK_ADJUSTMENT_ALLOWED_STATUS_TRANSITIONS = {
    "draft": {"posted", "cancelled"},
    "posted": {"cancelled"},
    "cancelled": set(),
}


def _normalize_status(raw_status: str) -> str:
    normalized = raw_status.strip().lower()
    if normalized not in VALID_STOCK_ADJUSTMENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Allowed values: draft, posted, cancelled",
        )
    return normalized


def _normalize_adjustment_no(raw_adjustment_no: str) -> str:
    normalized = raw_adjustment_no.strip().upper()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="adjustment_no cannot be empty",
        )
    return normalized


def _validate_status_transition(*, current_status: str, target_status: str) -> None:
    if target_status == current_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Material stock adjustment is already {target_status}",
        )
    allowed_statuses = MATERIAL_STOCK_ADJUSTMENT_ALLOWED_STATUS_TRANSITIONS.get(
        current_status,
        set(),
    )
    if target_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid material stock adjustment status transition: "
                f"{current_status} -> {target_status}"
            ),
        )


def _normalize_optional_text(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    return raw_value.strip() or None


def _ensure_unique_adjustment_no(
    db: Session,
    adjustment_no: str,
    *,
    exclude_adjustment_id: int | None = None,
) -> None:
    query = db.query(MaterialStockAdjustment).filter(
        func.lower(MaterialStockAdjustment.adjustment_no) == adjustment_no.lower()
    )
    if exclude_adjustment_id is not None:
        query = query.filter(MaterialStockAdjustment.id != exclude_adjustment_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adjustment number already exists",
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
            detail="Adjusted by user not found",
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


def _validate_item_values(*, qty_change: float, unit_rate: float) -> None:
    if qty_change == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="qty_change cannot be 0",
        )
    if unit_rate < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unit_rate cannot be negative",
        )


def _calculate_line_amount(*, qty_change: float, unit_rate: float) -> float:
    return round(abs(qty_change) * unit_rate, 2)


def _serialize_adjustment(adjustment: MaterialStockAdjustment) -> dict:
    return {
        "adjustment": serialize_model(adjustment),
        "items": serialize_models(list(adjustment.items)),
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


def list_material_stock_adjustments(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    project_id: int | None = None,
    status_filter: str | None = None,
    adjusted_by: int | None = None,
) -> dict[str, object]:
    company_id = resolve_company_scope(current_user)
    query = apply_material_stock_adjustment_company_scope(
        db.query(MaterialStockAdjustment).options(
            joinedload(MaterialStockAdjustment.items)
        ),
        company_id,
    )
    if project_id is not None:
        query = query.filter(MaterialStockAdjustment.project_id == project_id)
    if adjusted_by is not None:
        query = query.filter(MaterialStockAdjustment.adjusted_by == adjusted_by)
    if status_filter:
        query = query.filter(
            MaterialStockAdjustment.status == _normalize_status(status_filter)
        )
    return paginate_query(
        query.order_by(
            MaterialStockAdjustment.adjustment_date.desc(),
            MaterialStockAdjustment.id.desc(),
        ),
        pagination=pagination,
    )


def get_material_stock_adjustment_or_404(
    db: Session,
    adjustment_id: int,
) -> MaterialStockAdjustment:
    adjustment = (
        db.query(MaterialStockAdjustment)
        .options(joinedload(MaterialStockAdjustment.items))
        .filter(MaterialStockAdjustment.id == adjustment_id)
        .first()
    )
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material stock adjustment not found",
        )
    return adjustment


def create_material_stock_adjustment(
    db: Session,
    payload: MaterialStockAdjustmentCreate,
    current_user: User,
) -> MaterialStockAdjustment:
    data = payload.model_dump()
    data["adjustment_no"] = _normalize_adjustment_no(data["adjustment_no"])
    data["status"] = _normalize_status(data["status"])
    data["adjusted_by"] = data.get("adjusted_by") or current_user.id
    data["reason"] = _normalize_optional_text(data.get("reason"))
    data["remarks"] = _normalize_optional_text(data.get("remarks"))

    _ensure_unique_adjustment_no(db, data["adjustment_no"])
    _ensure_project_exists(db, data["project_id"])
    _ensure_user_exists(db, data["adjusted_by"])

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

        qty_change = float(item["qty_change"])
        unit_rate = float(item.get("unit_rate", 0))
        _validate_item_values(qty_change=qty_change, unit_rate=unit_rate)
        line_amount = _calculate_line_amount(qty_change=qty_change, unit_rate=unit_rate)
        total_amount += line_amount
        prepared_items.append(
            {
                "material_id": material_id,
                "qty_change": qty_change,
                "unit_rate": unit_rate,
                "line_amount": line_amount,
            }
        )

    data["total_amount"] = round(total_amount, 2)
    adjustment = MaterialStockAdjustment(**data)
    db.add(adjustment)
    flush_with_conflict_handling(db, entity_name="Material stock adjustment")

    adjustment_items: list[MaterialStockAdjustmentItem] = []
    for item in prepared_items:
        adjustment_item = MaterialStockAdjustmentItem(
            adjustment_id=adjustment.id,
            material_id=item["material_id"],
            qty_change=item["qty_change"],
            unit_rate=item["unit_rate"],
            line_amount=item["line_amount"],
        )
        adjustment_items.append(adjustment_item)
    db.add_all(adjustment_items)
    flush_with_conflict_handling(db, entity_name="Material stock adjustment")

    if adjustment.status == "posted":
        stock_deltas = {item["material_id"]: item["qty_change"] for item in prepared_items}
        _apply_stock_deltas(db, stock_deltas)
        record_inventory_transactions_from_stock_deltas(
            db,
            stock_deltas=stock_deltas,
            transaction_type="material_stock_adjustment",
            transaction_date=adjustment.adjustment_date,
            reference_type="material_stock_adjustment",
            reference_id=adjustment.id,
            project_id=adjustment.project_id,
            remarks=adjustment.reason or adjustment.remarks,
        )

    log_audit_event(
        db,
        entity_type="material_stock_adjustment",
        entity_id=adjustment.id,
        action="create",
        performed_by=current_user,
        after_data=_serialize_adjustment(adjustment),
        remarks=adjustment.adjustment_no,
    )
    commit_with_conflict_handling(db, entity_name="Material stock adjustment")
    return get_material_stock_adjustment_or_404(db, adjustment.id)


def update_material_stock_adjustment(
    db: Session,
    adjustment_id: int,
    payload: MaterialStockAdjustmentUpdate,
    current_user: User,
) -> MaterialStockAdjustment:
    adjustment = get_material_stock_adjustment_or_404(db, adjustment_id)
    if adjustment.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancelled material stock adjustment is immutable",
        )
    updates = payload.model_dump(exclude_unset=True)

    for field in (
        "adjustment_no",
        "project_id",
        "adjusted_by",
        "adjustment_date",
        "status",
    ):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} cannot be null",
            )

    if "adjustment_no" in updates and updates["adjustment_no"] is not None:
        updates["adjustment_no"] = _normalize_adjustment_no(updates["adjustment_no"])
        _ensure_unique_adjustment_no(
            db,
            updates["adjustment_no"],
            exclude_adjustment_id=adjustment.id,
        )
    if "status" in updates and updates["status"] is not None:
        updates["status"] = _normalize_status(updates["status"])
        _validate_status_transition(
            current_status=adjustment.status,
            target_status=updates["status"],
        )
    for field in ("reason", "remarks"):
        if field in updates:
            updates[field] = _normalize_optional_text(updates[field])

    next_project_id = updates.get("project_id", adjustment.project_id)
    next_adjusted_by = updates.get("adjusted_by", adjustment.adjusted_by)
    next_status = updates.get("status", adjustment.status)

    _ensure_project_exists(db, next_project_id)
    _ensure_user_exists(db, next_adjusted_by)

    existing_item_map = {item.id: item for item in adjustment.items}
    next_item_values: dict[int, dict[str, float]] = {
        item.id: {
            "qty_change": float(item.qty_change),
            "unit_rate": float(item.unit_rate),
            "line_amount": float(item.line_amount),
            "material_id": item.material_id,
        }
        for item in adjustment.items
    }

    if "items" in updates and updates["items"] is not None:
        seen_item_ids: set[int] = set()
        for item_update in updates["items"]:
            item_id = item_update["id"]
            if item_id in seen_item_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate adjustment item id in update payload: {item_id}",
                )
            seen_item_ids.add(item_id)
            item = existing_item_map.get(item_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Material stock adjustment item not found for id={item_id}",
                )
            for field in ("qty_change", "unit_rate"):
                if field in item_update and item_update[field] is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"{field} cannot be null",
                    )

            qty_change = float(
                item_update["qty_change"]
                if "qty_change" in item_update
                else next_item_values[item_id]["qty_change"]
            )
            unit_rate = float(
                item_update["unit_rate"]
                if "unit_rate" in item_update
                else next_item_values[item_id]["unit_rate"]
            )
            _validate_item_values(qty_change=qty_change, unit_rate=unit_rate)
            line_amount = _calculate_line_amount(
                qty_change=qty_change,
                unit_rate=unit_rate,
            )
            next_item_values[item_id]["qty_change"] = qty_change
            next_item_values[item_id]["unit_rate"] = unit_rate
            next_item_values[item_id]["line_amount"] = line_amount

    for item in adjustment.items:
        _get_material_for_project_or_400(
            db,
            item.material_id,
            next_project_id,
        )

    before_data = _serialize_adjustment(adjustment)

    stock_deltas: dict[int, float] = {}
    for item in adjustment.items:
        old_effective_qty = (
            float(item.qty_change) if adjustment.status == "posted" else 0.0
        )
        new_effective_qty = (
            next_item_values[item.id]["qty_change"] if next_status == "posted" else 0.0
        )
        delta = round(new_effective_qty - old_effective_qty, 3)
        if delta != 0:
            stock_deltas[item.material_id] = stock_deltas.get(item.material_id, 0.0) + delta

    for field in (
        "adjustment_no",
        "project_id",
        "adjusted_by",
        "adjustment_date",
        "status",
        "reason",
        "remarks",
    ):
        if field in updates:
            setattr(adjustment, field, updates[field])

    total_amount = 0.0
    for item in adjustment.items:
        item_values = next_item_values[item.id]
        item.qty_change = item_values["qty_change"]
        item.unit_rate = item_values["unit_rate"]
        item.line_amount = item_values["line_amount"]
        total_amount += item_values["line_amount"]
    adjustment.total_amount = round(total_amount, 2)

    _apply_stock_deltas(db, stock_deltas)
    record_inventory_transactions_from_stock_deltas(
        db,
        stock_deltas=stock_deltas,
        transaction_type="material_stock_adjustment_update",
        transaction_date=adjustment.adjustment_date,
        reference_type="material_stock_adjustment",
        reference_id=adjustment.id,
        project_id=adjustment.project_id,
        remarks=adjustment.reason or adjustment.remarks,
    )
    flush_with_conflict_handling(db, entity_name="Material stock adjustment")

    log_audit_event(
        db,
        entity_type="material_stock_adjustment",
        entity_id=adjustment.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=_serialize_adjustment(adjustment),
        remarks=adjustment.adjustment_no,
    )
    commit_with_conflict_handling(db, entity_name="Material stock adjustment")
    return get_material_stock_adjustment_or_404(db, adjustment.id)
