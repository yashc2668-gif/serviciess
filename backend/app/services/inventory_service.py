"""Inventory service helpers."""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.inventory_transaction import InventoryTransaction
from app.models.material import Material
from app.models.user import User
from app.services.company_scope_service import apply_material_company_scope, resolve_company_scope
from app.utils.pagination import PaginationParams, paginate_query


def _normalize_optional_text(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    return raw_value.strip() or None


def list_inventory_transactions(
    db: Session,
    current_user: User,
    *,
    pagination: PaginationParams,
    material_id: int | None = None,
    project_id: int | None = None,
    transaction_type: str | None = None,
    reference_type: str | None = None,
    reference_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, object]:
    company_id = resolve_company_scope(current_user)
    query = db.query(InventoryTransaction).join(Material, InventoryTransaction.material_id == Material.id)
    query = apply_material_company_scope(query, company_id)
    if material_id is not None:
        query = query.filter(InventoryTransaction.material_id == material_id)
    if project_id is not None:
        query = query.filter(InventoryTransaction.project_id == project_id)
    if transaction_type:
        query = query.filter(
            InventoryTransaction.transaction_type == transaction_type.strip().lower()
        )
    if reference_type:
        query = query.filter(
            InventoryTransaction.reference_type == reference_type.strip().lower()
        )
    if reference_id is not None:
        query = query.filter(InventoryTransaction.reference_id == reference_id)
    if date_from is not None:
        query = query.filter(InventoryTransaction.transaction_date >= date_from)
    if date_to is not None:
        query = query.filter(InventoryTransaction.transaction_date <= date_to)
    return paginate_query(
        query.order_by(
            InventoryTransaction.transaction_date.desc(),
            InventoryTransaction.id.desc(),
        ),
        pagination=pagination,
    )


def get_inventory_transaction_or_404(
    db: Session,
    transaction_id: int,
    *,
    current_user: User,
) -> InventoryTransaction:
    transaction = (
        apply_material_company_scope(
            db.query(InventoryTransaction).join(Material, InventoryTransaction.material_id == Material.id),
            resolve_company_scope(current_user),
        )
        .filter(InventoryTransaction.id == transaction_id)
        .first()
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock ledger transaction not found",
        )
    return transaction


def record_inventory_transaction(
    db: Session,
    *,
    material_id: int,
    transaction_type: str,
    qty_in: float = 0,
    qty_out: float = 0,
    balance_after: float,
    reference_type: str | None = None,
    reference_id: int | None = None,
    transaction_date: date,
    project_id: int | None = None,
    remarks: str | None = None,
) -> InventoryTransaction:
    normalized_transaction_type = transaction_type.strip().lower()
    if not normalized_transaction_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="transaction_type cannot be empty",
        )
    normalized_reference_type = _normalize_optional_text(reference_type)
    if normalized_reference_type is not None:
        normalized_reference_type = normalized_reference_type.lower()

    qty_in_value = round(float(qty_in), 3)
    qty_out_value = round(float(qty_out), 3)
    if qty_in_value < 0 or qty_out_value < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="qty_in and qty_out cannot be negative",
        )
    if qty_in_value == 0 and qty_out_value == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either qty_in or qty_out must be greater than 0",
        )
    if qty_in_value > 0 and qty_out_value > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one of qty_in or qty_out can be greater than 0",
        )
    if balance_after < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="balance_after cannot be negative",
        )

    transaction = InventoryTransaction(
        material_id=material_id,
        project_id=project_id,
        transaction_type=normalized_transaction_type,
        qty_in=qty_in_value,
        qty_out=qty_out_value,
        balance_after=round(float(balance_after), 3),
        reference_type=normalized_reference_type,
        reference_id=reference_id,
        transaction_date=transaction_date,
        remarks=_normalize_optional_text(remarks),
    )
    db.add(transaction)
    db.flush()
    return transaction


def record_inventory_transactions_from_stock_deltas(
    db: Session,
    *,
    stock_deltas: dict[int, float],
    transaction_type: str,
    transaction_date: date,
    reference_type: str | None = None,
    reference_id: int | None = None,
    project_id: int | None = None,
    remarks: str | None = None,
) -> list[InventoryTransaction]:
    if not stock_deltas:
        return []

    material_ids = [material_id for material_id, delta in stock_deltas.items() if delta != 0]
    if not material_ids:
        return []

    materials = db.query(Material).filter(Material.id.in_(material_ids)).all()
    material_map = {material.id: material for material in materials}

    created: list[InventoryTransaction] = []
    for material_id in material_ids:
        material = material_map.get(material_id)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material not found for material_id={material_id}",
            )
        delta = round(float(stock_deltas[material_id]), 3)
        if delta == 0:
            continue
        created.append(
            record_inventory_transaction(
                db,
                material_id=material_id,
                project_id=project_id or material.project_id,
                transaction_type=transaction_type,
                qty_in=delta if delta > 0 else 0,
                qty_out=abs(delta) if delta < 0 else 0,
                balance_after=float(material.current_stock),
                reference_type=reference_type,
                reference_id=reference_id,
                transaction_date=transaction_date,
                remarks=remarks,
            )
        )
    return created
