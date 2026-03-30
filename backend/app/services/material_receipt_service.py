"""Material receipt service helpers."""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.material import Material
from app.models.material_receipt import MaterialReceipt
from app.models.material_receipt_item import MaterialReceiptItem
from app.models.project import Project
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.material_receipt import MaterialReceiptCreate, MaterialReceiptUpdate
from app.services.inventory_service import record_inventory_transactions_from_stock_deltas
from app.services.audit_service import (
    log_audit_event,
    serialize_model,
    serialize_models,
)
from app.services.company_scope_service import (
    apply_material_receipt_company_scope,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    apply_write_lock,
    commit_with_conflict_handling,
    flush_with_conflict_handling,
)
from app.utils.pagination import PaginationParams, paginate_query

VALID_RECEIPT_STATUSES = {"draft", "received", "cancelled"}
MATERIAL_RECEIPT_ALLOWED_STATUS_TRANSITIONS = {
    "draft": {"received", "cancelled"},
    "received": {"cancelled"},
    "cancelled": set(),
}


def _normalize_status(raw_status: str) -> str:
    normalized = raw_status.strip().lower()
    if normalized not in VALID_RECEIPT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid receipt status. Allowed values: draft, received, cancelled",
        )
    return normalized


def _normalize_receipt_no(raw_receipt_no: str) -> str:
    normalized = raw_receipt_no.strip().upper()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="receipt_no cannot be empty",
        )
    return normalized


def _validate_status_transition(*, current_status: str, target_status: str) -> None:
    if target_status == current_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Material receipt is already {target_status}",
        )
    allowed_statuses = MATERIAL_RECEIPT_ALLOWED_STATUS_TRANSITIONS.get(
        current_status,
        set(),
    )
    if target_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid material receipt status transition: "
                f"{current_status} -> {target_status}"
            ),
        )


def _ensure_unique_receipt_no(
    db: Session,
    receipt_no: str,
    *,
    exclude_receipt_id: int | None = None,
) -> None:
    query = db.query(MaterialReceipt).filter(
        func.lower(MaterialReceipt.receipt_no) == receipt_no.lower()
    )
    if exclude_receipt_id is not None:
        query = query.filter(MaterialReceipt.id != exclude_receipt_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receipt number already exists",
        )


def _ensure_vendor_exists(db: Session, vendor_id: int) -> None:
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
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
            detail="Received by user not found",
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


def _validate_item_values(*, received_qty: float, unit_rate: float) -> None:
    if received_qty <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="received_qty must be greater than 0",
        )
    if unit_rate < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unit_rate cannot be negative",
        )


def _calculate_line_amount(*, received_qty: float, unit_rate: float) -> float:
    return round(received_qty * unit_rate, 2)


def _serialize_receipt(receipt: MaterialReceipt) -> dict:
    return {
        "receipt": serialize_model(receipt),
        "items": serialize_models(list(receipt.items)),
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


def list_material_receipts(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    vendor_id: int | None = None,
    project_id: int | None = None,
    status_filter: str | None = None,
) -> dict[str, object]:
    company_id = resolve_company_scope(current_user)
    query = apply_material_receipt_company_scope(
        db.query(MaterialReceipt).options(joinedload(MaterialReceipt.items)),
        company_id,
    )
    if vendor_id is not None:
        query = query.filter(MaterialReceipt.vendor_id == vendor_id)
    if project_id is not None:
        query = query.filter(MaterialReceipt.project_id == project_id)
    if status_filter:
        query = query.filter(MaterialReceipt.status == _normalize_status(status_filter))
    return paginate_query(
        query.order_by(MaterialReceipt.receipt_date.desc(), MaterialReceipt.id.desc()),
        pagination=pagination,
    )


def get_material_receipt_or_404(db: Session, receipt_id: int) -> MaterialReceipt:
    receipt = (
        db.query(MaterialReceipt)
        .options(joinedload(MaterialReceipt.items))
        .filter(MaterialReceipt.id == receipt_id)
        .first()
    )
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material receipt not found",
        )
    return receipt


def create_material_receipt(
    db: Session,
    payload: MaterialReceiptCreate,
    current_user: User,
) -> MaterialReceipt:
    data = payload.model_dump()
    data["receipt_no"] = _normalize_receipt_no(data["receipt_no"])
    data["status"] = _normalize_status(data["status"])
    data["received_by"] = data.get("received_by") or current_user.id
    if data.get("remarks") is not None:
        data["remarks"] = data["remarks"].strip() or None

    _ensure_unique_receipt_no(db, data["receipt_no"])
    _ensure_vendor_exists(db, data["vendor_id"])
    _ensure_project_exists(db, data["project_id"])
    _ensure_user_exists(db, data["received_by"])

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

        received_qty = float(item["received_qty"])
        unit_rate = float(item.get("unit_rate", 0))
        _validate_item_values(received_qty=received_qty, unit_rate=unit_rate)
        line_amount = _calculate_line_amount(received_qty=received_qty, unit_rate=unit_rate)
        total_amount += line_amount
        prepared_items.append(
            {
                "material_id": material_id,
                "received_qty": received_qty,
                "unit_rate": unit_rate,
                "line_amount": line_amount,
            }
        )

    data["total_amount"] = round(total_amount, 2)
    receipt = MaterialReceipt(**data)
    db.add(receipt)
    flush_with_conflict_handling(db, entity_name="Material receipt")

    receipt_items: list[MaterialReceiptItem] = []
    for item in prepared_items:
        receipt_item = MaterialReceiptItem(
            receipt_id=receipt.id,
            material_id=item["material_id"],
            received_qty=item["received_qty"],
            unit_rate=item["unit_rate"],
            line_amount=item["line_amount"],
        )
        receipt_items.append(receipt_item)
    db.add_all(receipt_items)
    flush_with_conflict_handling(db, entity_name="Material receipt")

    if receipt.status == "received":
        stock_deltas = {
            item["material_id"]: item["received_qty"] for item in prepared_items
        }
        _apply_stock_deltas(db, stock_deltas)
        record_inventory_transactions_from_stock_deltas(
            db,
            stock_deltas=stock_deltas,
            transaction_type="material_receipt",
            transaction_date=receipt.receipt_date,
            reference_type="material_receipt",
            reference_id=receipt.id,
            project_id=receipt.project_id,
            remarks=receipt.remarks,
        )

    log_audit_event(
        db,
        entity_type="material_receipt",
        entity_id=receipt.id,
        action="create",
        performed_by=current_user,
        after_data=_serialize_receipt(receipt),
        remarks=receipt.receipt_no,
    )
    commit_with_conflict_handling(db, entity_name="Material receipt")
    return get_material_receipt_or_404(db, receipt.id)


def update_material_receipt(
    db: Session,
    receipt_id: int,
    payload: MaterialReceiptUpdate,
    current_user: User,
) -> MaterialReceipt:
    receipt = get_material_receipt_or_404(db, receipt_id)
    if receipt.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancelled material receipt is immutable",
        )
    updates = payload.model_dump(exclude_unset=True)

    for field in ("receipt_no", "vendor_id", "project_id", "received_by", "receipt_date", "status"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} cannot be null",
            )

    if "receipt_no" in updates and updates["receipt_no"] is not None:
        updates["receipt_no"] = _normalize_receipt_no(updates["receipt_no"])
        _ensure_unique_receipt_no(
            db,
            updates["receipt_no"],
            exclude_receipt_id=receipt.id,
        )
    if "status" in updates and updates["status"] is not None:
        updates["status"] = _normalize_status(updates["status"])
        _validate_status_transition(
            current_status=receipt.status,
            target_status=updates["status"],
        )
    if "remarks" in updates:
        updates["remarks"] = (updates["remarks"] or "").strip() or None

    next_vendor_id = updates.get("vendor_id", receipt.vendor_id)
    next_project_id = updates.get("project_id", receipt.project_id)
    next_received_by = updates.get("received_by", receipt.received_by)
    next_status = updates.get("status", receipt.status)

    _ensure_vendor_exists(db, next_vendor_id)
    _ensure_project_exists(db, next_project_id)
    _ensure_user_exists(db, next_received_by)

    existing_item_map = {item.id: item for item in receipt.items}
    next_item_values: dict[int, dict[str, float]] = {
        item.id: {
            "received_qty": float(item.received_qty),
            "unit_rate": float(item.unit_rate),
            "line_amount": float(item.line_amount),
            "material_id": item.material_id,
        }
        for item in receipt.items
    }

    if "items" in updates and updates["items"] is not None:
        seen_item_ids: set[int] = set()
        for item_update in updates["items"]:
            item_id = item_update["id"]
            if item_id in seen_item_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate receipt item id in update payload: {item_id}",
                )
            seen_item_ids.add(item_id)
            item = existing_item_map.get(item_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Material receipt item not found for id={item_id}",
                )
            for field in ("received_qty", "unit_rate"):
                if field in item_update and item_update[field] is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"{field} cannot be null",
                    )

            received_qty = float(
                item_update["received_qty"]
                if "received_qty" in item_update
                else next_item_values[item_id]["received_qty"]
            )
            unit_rate = float(
                item_update["unit_rate"]
                if "unit_rate" in item_update
                else next_item_values[item_id]["unit_rate"]
            )
            _validate_item_values(received_qty=received_qty, unit_rate=unit_rate)
            line_amount = _calculate_line_amount(
                received_qty=received_qty,
                unit_rate=unit_rate,
            )
            next_item_values[item_id]["received_qty"] = received_qty
            next_item_values[item_id]["unit_rate"] = unit_rate
            next_item_values[item_id]["line_amount"] = line_amount

    for item in receipt.items:
        _get_material_for_project_or_400(
            db,
            item.material_id,
            next_project_id,
        )

    before_data = _serialize_receipt(receipt)

    stock_deltas: dict[int, float] = {}
    for item in receipt.items:
        old_effective_qty = float(item.received_qty) if receipt.status == "received" else 0.0
        new_effective_qty = (
            next_item_values[item.id]["received_qty"] if next_status == "received" else 0.0
        )
        delta = round(new_effective_qty - old_effective_qty, 3)
        if delta != 0:
            stock_deltas[item.material_id] = stock_deltas.get(item.material_id, 0.0) + delta

    for field in ("receipt_no", "vendor_id", "project_id", "received_by", "receipt_date", "status", "remarks"):
        if field in updates:
            setattr(receipt, field, updates[field])

    total_amount = 0.0
    for item in receipt.items:
        item_values = next_item_values[item.id]
        item.received_qty = item_values["received_qty"]
        item.unit_rate = item_values["unit_rate"]
        item.line_amount = item_values["line_amount"]
        total_amount += item_values["line_amount"]
    receipt.total_amount = round(total_amount, 2)

    _apply_stock_deltas(db, stock_deltas)
    record_inventory_transactions_from_stock_deltas(
        db,
        stock_deltas=stock_deltas,
        transaction_type="material_receipt_adjustment",
        transaction_date=receipt.receipt_date,
        reference_type="material_receipt",
        reference_id=receipt.id,
        project_id=receipt.project_id,
        remarks=receipt.remarks,
    )
    flush_with_conflict_handling(db, entity_name="Material receipt")

    log_audit_event(
        db,
        entity_type="material_receipt",
        entity_id=receipt.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=_serialize_receipt(receipt),
        remarks=receipt.receipt_no,
    )
    commit_with_conflict_handling(db, entity_name="Material receipt")
    return get_material_receipt_or_404(db, receipt.id)
