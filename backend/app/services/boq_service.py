"""BOQ service helpers."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.boq import BOQItem
from app.models.contract import Contract
from app.models.user import User
from app.schemas.boq import BOQItemCreate, BOQItemUpdate
from app.services.audit_service import log_audit_event, serialize_model


def _get_contract_or_404(db: Session, contract_id: int) -> Contract:
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )
    return contract


def create_boq_item(db: Session, contract_id: int, payload: BOQItemCreate) -> BOQItem:
    _get_contract_or_404(db, contract_id)
    data = payload.model_dump()
    if data["amount"] == 0 and data["quantity"] and data["rate"]:
        data["amount"] = round(data["quantity"] * data["rate"], 2)
    boq_item = BOQItem(contract_id=contract_id, **data)
    db.add(boq_item)
    db.flush()
    return boq_item


def create_boq_item_with_audit(
    db: Session,
    contract_id: int,
    payload: BOQItemCreate,
    current_user: User,
) -> BOQItem:
    boq_item = create_boq_item(db, contract_id, payload)
    log_audit_event(
        db,
        entity_type="boq_item",
        entity_id=boq_item.id,
        action="create",
        performed_by=current_user,
        after_data=serialize_model(boq_item),
    )
    db.commit()
    db.refresh(boq_item)
    return boq_item


def list_boq_items_by_contract(db: Session, contract_id: int) -> list[BOQItem]:
    _get_contract_or_404(db, contract_id)
    return (
        db.query(BOQItem)
        .filter(BOQItem.contract_id == contract_id)
        .order_by(BOQItem.created_at.asc(), BOQItem.id.asc())
        .all()
    )


def get_boq_item_or_404(db: Session, contract_id: int, boq_item_id: int) -> BOQItem:
    boq_item = (
        db.query(BOQItem)
        .filter(BOQItem.id == boq_item_id, BOQItem.contract_id == contract_id)
        .first()
    )
    if not boq_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOQ item not found",
        )
    return boq_item


def update_boq_item(
    db: Session,
    contract_id: int,
    boq_item_id: int,
    payload: BOQItemUpdate,
    current_user: User,
) -> BOQItem:
    boq_item = get_boq_item_or_404(db, contract_id, boq_item_id)
    updates = payload.model_dump(exclude_unset=True, mode="json")
    before_data = serialize_model(boq_item)
    for field, value in updates.items():
        setattr(boq_item, field, value)

    if (
        ("quantity" in updates or "rate" in updates)
        and "amount" not in updates
        and boq_item.quantity is not None
        and boq_item.rate is not None
    ):
        boq_item.amount = round(float(boq_item.quantity) * float(boq_item.rate), 2)
    db.flush()

    log_audit_event(
        db,
        entity_type="boq_item",
        entity_id=boq_item.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=serialize_model(boq_item),
    )
    db.commit()
    db.refresh(boq_item)
    return boq_item
