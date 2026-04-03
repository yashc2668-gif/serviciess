"""Measurement service helpers."""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.boq import BOQItem
from app.models.contract import Contract
from app.models.measurement import Measurement
from app.models.measurement_item import MeasurementItem
from app.models.user import User
from app.models.work_done import WorkDoneItem
from app.schemas.measurement import MeasurementCreate, MeasurementItemCreate, MeasurementUpdate
from app.services.audit_service import log_audit_event
from app.utils.pagination import PaginationParams, paginate_query

ABSURD_EXCESS_MULTIPLIER = Decimal("1.25")


def _get_contract_or_404(db: Session, contract_id: int) -> Contract:
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )
    return contract


def _get_boq_item_or_404(db: Session, boq_item_id: int) -> BOQItem:
    boq_item = db.query(BOQItem).filter(BOQItem.id == boq_item_id).first()
    if not boq_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BOQ item not found",
        )
    return boq_item


def _get_measurement_query(db: Session):
    return db.query(Measurement).options(
        joinedload(Measurement.items),
        joinedload(Measurement.work_done_entries),
    )


def get_measurement_or_404(db: Session, measurement_id: int) -> Measurement:
    measurement = (
        _get_measurement_query(db)
        .filter(Measurement.id == measurement_id)
        .first()
    )
    if not measurement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement not found",
        )
    return measurement


def list_measurements(
    db: Session,
    current_user: User | None = None,
    contract_id: int | None = None,
    status_filter: str | None = None,
    *,
    pagination: PaginationParams,
) -> dict[str, object]:
    query = _get_measurement_query(db)
    if contract_id is not None:
        query = query.filter(Measurement.contract_id == contract_id)
    if status_filter is not None:
        query = query.filter(Measurement.status == status_filter)
    return paginate_query(
        query.order_by(Measurement.created_at.desc(), Measurement.id.desc()),
        pagination=pagination,
    )


def _approved_quantity_before_measurement(
    db: Session,
    boq_item_id: int,
    measurement_id: int | None = None,
) -> Decimal:
    query = db.query(func.coalesce(func.sum(WorkDoneItem.current_quantity), 0)).filter(
        WorkDoneItem.boq_item_id == boq_item_id
    )
    if measurement_id is not None:
        query = query.filter(WorkDoneItem.measurement_id != measurement_id)
    return Decimal(str(query.scalar() or 0))


def _build_measurement_item(
    db: Session,
    contract_id: int,
    payload: MeasurementItemCreate,
    measurement_id: int | None = None,
) -> MeasurementItem:
    boq_item = _get_boq_item_or_404(db, payload.boq_item_id)
    if boq_item.contract_id != contract_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BOQ item does not belong to the selected contract",
        )
    if payload.current_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current quantity cannot be negative",
        )

    previous_quantity = _approved_quantity_before_measurement(
        db,
        boq_item.id,
        measurement_id=measurement_id,
    )
    current_quantity = Decimal(str(payload.current_quantity))
    cumulative_quantity = previous_quantity + current_quantity
    boq_quantity = Decimal(str(boq_item.quantity))

    warning_message = None
    if boq_quantity > 0 and cumulative_quantity > boq_quantity * ABSURD_EXCESS_MULTIPLIER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Measurement quantity for BOQ item {boq_item.id} exceeds the allowed "
                f"threshold of 125% of contract quantity"
            ),
        )
    if boq_quantity > 0 and cumulative_quantity > boq_quantity and not payload.allow_excess:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Measurement quantity for BOQ item {boq_item.id} exceeds contract quantity. "
                "Set allow_excess=true to continue with an explicit warning."
            ),
        )
    if boq_quantity > 0 and cumulative_quantity > boq_quantity and payload.allow_excess:
        warning_message = (
            f"Cumulative quantity {float(cumulative_quantity)} exceeds BOQ quantity "
            f"{float(boq_quantity)}"
        )

    rate = Decimal(str(payload.rate if payload.rate is not None else boq_item.rate))
    amount = Decimal(str(payload.amount))
    if amount == 0:
        amount = (current_quantity * rate).quantize(Decimal("0.01"))

    return MeasurementItem(
        boq_item_id=boq_item.id,
        description_snapshot=boq_item.description,
        unit_snapshot=boq_item.unit,
        previous_quantity=previous_quantity,
        current_quantity=current_quantity,
        cumulative_quantity=cumulative_quantity,
        rate=rate,
        amount=amount,
        allow_excess=payload.allow_excess,
        warning_message=warning_message,
        remarks=payload.remarks,
    )


def _replace_measurement_items(
    db: Session,
    measurement: Measurement,
    items: list[MeasurementItemCreate],
) -> None:
    measurement.items.clear()
    db.flush()
    measurement.items.extend(
        _build_measurement_item(
            db,
            measurement.contract_id,
            item,
            measurement_id=measurement.id,
        )
        for item in items
    )


def _revalidate_measurement_items_for_approval(
    db: Session,
    measurement: Measurement,
) -> None:
    for item in measurement.items:
        boq_item = _get_boq_item_or_404(db, item.boq_item_id)
        previous_quantity = _approved_quantity_before_measurement(
            db,
            boq_item.id,
            measurement_id=measurement.id,
        )
        current_quantity = Decimal(str(item.current_quantity))
        cumulative_quantity = previous_quantity + current_quantity
        boq_quantity = Decimal(str(boq_item.quantity))

        if boq_quantity > 0 and cumulative_quantity > boq_quantity * ABSURD_EXCESS_MULTIPLIER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Measurement quantity for BOQ item {boq_item.id} exceeds the allowed "
                    f"threshold of 125% of contract quantity"
                ),
            )
        if boq_quantity > 0 and cumulative_quantity > boq_quantity and not item.allow_excess:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Measurement quantity for BOQ item {boq_item.id} exceeds contract quantity. "
                    "Set allow_excess=true to continue with an explicit warning."
                ),
            )

        item.previous_quantity = previous_quantity
        item.cumulative_quantity = cumulative_quantity
        item.warning_message = None
        if boq_quantity > 0 and cumulative_quantity > boq_quantity and item.allow_excess:
            item.warning_message = (
                f"Cumulative quantity {float(cumulative_quantity)} exceeds BOQ quantity "
                f"{float(boq_quantity)}"
            )


def create_measurement(db: Session, payload: MeasurementCreate, current_user: User) -> Measurement:
    _get_contract_or_404(db, payload.contract_id)
    existing = db.query(Measurement).filter(Measurement.measurement_no == payload.measurement_no).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Measurement number already exists",
        )

    measurement = Measurement(
        contract_id=payload.contract_id,
        measurement_no=payload.measurement_no,
        measurement_date=payload.measurement_date,
        status="draft",
        remarks=payload.remarks,
        created_by=current_user.id,
    )
    db.add(measurement)
    db.flush()
    _replace_measurement_items(db, measurement, payload.items)
    db.commit()
    db.refresh(measurement)
    return get_measurement_or_404(db, measurement.id)


def update_measurement(
    db: Session,
    measurement_id: int,
    payload: MeasurementUpdate,
) -> Measurement:
    measurement = get_measurement_or_404(db, measurement_id)
    if measurement.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft measurements can be updated",
        )

    if payload.measurement_date is not None:
        measurement.measurement_date = payload.measurement_date
    if payload.remarks is not None:
        measurement.remarks = payload.remarks
    if payload.items is not None:
        _replace_measurement_items(db, measurement, payload.items)

    db.commit()
    db.refresh(measurement)
    return get_measurement_or_404(db, measurement.id)


def delete_measurement(db: Session, measurement_id: int) -> None:
    measurement = get_measurement_or_404(db, measurement_id)
    if measurement.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft measurements can be deleted",
        )
    db.delete(measurement)
    db.commit()


def submit_measurement(db: Session, measurement_id: int, current_user: User) -> Measurement:
    measurement = get_measurement_or_404(db, measurement_id)
    if measurement.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft measurements can be submitted",
        )
    if not measurement.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Measurement must have at least one line item before submission",
        )

    previous_status = measurement.status
    measurement.status = "submitted"
    measurement.submitted_by = current_user.id
    measurement.submitted_at = datetime.now(timezone.utc)
    log_audit_event(
        db,
        entity_type="measurement",
        entity_id=measurement.id,
        action="submit",
        performed_by=current_user,
        before_data={"status": previous_status},
        after_data={
            "status": measurement.status,
            "measurement_no": measurement.measurement_no,
            "items_count": len(measurement.items),
        },
        remarks=measurement.measurement_no,
    )
    db.commit()
    db.refresh(measurement)
    return get_measurement_or_404(db, measurement.id)


def approve_measurement(db: Session, measurement_id: int, current_user: User) -> Measurement:
    measurement = get_measurement_or_404(db, measurement_id)
    if measurement.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only submitted measurements can be approved",
        )
    if not measurement.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Measurement must have items to be approved",
        )

    if measurement.work_done_entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Work done entries already exist for this measurement",
        )

    _revalidate_measurement_items_for_approval(db, measurement)

    previous_status = measurement.status
    for item in measurement.items:
        db.add(
            WorkDoneItem(
                contract_id=measurement.contract_id,
                measurement_id=measurement.id,
                measurement_item_id=item.id,
                boq_item_id=item.boq_item_id,
                recorded_date=measurement.measurement_date,
                previous_quantity=item.previous_quantity,
                current_quantity=item.current_quantity,
                cumulative_quantity=item.cumulative_quantity,
                rate=item.rate,
                amount=item.amount,
                remarks=item.remarks,
                approved_by=current_user.id,
            )
        )

    measurement.status = "approved"
    measurement.approved_by = current_user.id
    measurement.approved_at = datetime.now(timezone.utc)
    log_audit_event(
        db,
        entity_type="measurement",
        entity_id=measurement.id,
        action="approve",
        performed_by=current_user,
        before_data={"status": previous_status},
        after_data={
            "status": measurement.status,
            "measurement_no": measurement.measurement_no,
            "work_done_count": len(measurement.items),
        },
        remarks=measurement.measurement_no,
    )
    db.commit()
    db.refresh(measurement)
    return get_measurement_or_404(db, measurement.id)
