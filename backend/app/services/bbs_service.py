"""Bar bending schedule service helpers."""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.bar_bending_schedule import BarBendingSchedule
from app.models.contract import Contract
from app.models.project import Project
from app.schemas.bbs import BBSCreate, BBSUpdate
from app.services.concurrency_service import (
    commit_with_conflict_handling,
    ensure_lock_version_matches,
    flush_with_conflict_handling,
)
from app.utils.pagination import PaginationParams, paginate_query


def _get_contract_or_404(db: Session, contract_id: int) -> Contract:
    contract = (
        db.query(Contract)
        .options(joinedload(Contract.project))
        .filter(Contract.id == contract_id, Contract.is_deleted.is_(False))
        .first()
    )
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )
    return contract


def get_bbs_or_404(db: Session, bbs_id: int) -> BarBendingSchedule:
    bbs_entry = (
        db.query(BarBendingSchedule)
        .options(joinedload(BarBendingSchedule.contract).joinedload(Contract.project))
        .filter(BarBendingSchedule.id == bbs_id)
        .first()
    )
    if not bbs_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BBS entry not found",
        )
    return bbs_entry


def _resolved_total_weight(*, nos: int, unit_weight: Decimal, total_weight: float | None) -> Decimal:
    if total_weight is not None:
        return Decimal(str(total_weight))
    return (Decimal(str(nos)) * unit_weight).quantize(Decimal("0.001"))


def list_bbs_entries(
    db: Session,
    *,
    pagination: PaginationParams,
    project_id: int | None = None,
    contract_id: int | None = None,
    drawing_no: str | None = None,
    search: str | None = None,
) -> dict[str, object]:
    query = (
        db.query(BarBendingSchedule)
        .join(Contract, Contract.id == BarBendingSchedule.contract_id)
        .join(Project, Project.id == Contract.project_id)
        .options(joinedload(BarBendingSchedule.contract).joinedload(Contract.project))
    )
    if project_id is not None:
        query = query.filter(Project.id == project_id)
    if contract_id is not None:
        query = query.filter(BarBendingSchedule.contract_id == contract_id)
    if drawing_no:
        query = query.filter(BarBendingSchedule.drawing_no.ilike(f"%{drawing_no.strip()}%"))
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                BarBendingSchedule.drawing_no.ilike(search_term),
                BarBendingSchedule.member_location.ilike(search_term),
                BarBendingSchedule.bar_mark.ilike(search_term),
                BarBendingSchedule.shape_code.ilike(search_term),
                BarBendingSchedule.remarks.ilike(search_term),
                Contract.contract_no.ilike(search_term),
                Contract.title.ilike(search_term),
                Project.name.ilike(search_term),
            )
        )
    return paginate_query(
        query.order_by(
            BarBendingSchedule.drawing_no.asc(),
            BarBendingSchedule.bar_mark.asc(),
            BarBendingSchedule.id.asc(),
        ),
        pagination=pagination,
    )


def create_bbs_entry(db: Session, payload: BBSCreate) -> BarBendingSchedule:
    contract = _get_contract_or_404(db, payload.contract_id)
    unit_weight = Decimal(str(payload.unit_weight))
    bbs_entry = BarBendingSchedule(
        contract_id=contract.id,
        drawing_no=payload.drawing_no.strip(),
        member_location=payload.member_location.strip(),
        bar_mark=payload.bar_mark.strip(),
        dia_mm=Decimal(str(payload.dia_mm)),
        cut_length_mm=Decimal(str(payload.cut_length_mm)),
        shape_code=payload.shape_code.strip() if payload.shape_code else None,
        nos=payload.nos,
        unit_weight=unit_weight,
        total_weight=_resolved_total_weight(
            nos=payload.nos,
            unit_weight=unit_weight,
            total_weight=payload.total_weight,
        ),
        remarks=payload.remarks.strip() if payload.remarks else None,
    )
    db.add(bbs_entry)
    commit_with_conflict_handling(db, entity_name="BarBendingSchedule")
    db.refresh(bbs_entry)
    return get_bbs_or_404(db, bbs_entry.id)


def update_bbs_entry(db: Session, bbs_id: int, payload: BBSUpdate) -> BarBendingSchedule:
    bbs_entry = get_bbs_or_404(db, bbs_id)
    updates = payload.model_dump(exclude_unset=True)
    ensure_lock_version_matches(
        bbs_entry,
        updates.pop("lock_version", None),
        entity_name="BarBendingSchedule",
    )

    for field in ("drawing_no", "member_location", "bar_mark", "shape_code", "remarks"):
        if field in updates and isinstance(updates[field], str):
            updates[field] = updates[field].strip()

    for field, value in updates.items():
        setattr(bbs_entry, field, value)

    if {"nos", "unit_weight", "total_weight"} & updates.keys():
        resolved_nos = int(updates.get("nos", bbs_entry.nos))
        resolved_unit_weight = Decimal(str(updates.get("unit_weight", bbs_entry.unit_weight)))
        resolved_total_weight = updates.get("total_weight")
        bbs_entry.total_weight = _resolved_total_weight(
            nos=resolved_nos,
            unit_weight=resolved_unit_weight,
            total_weight=resolved_total_weight,
        )

    flush_with_conflict_handling(db, entity_name="BarBendingSchedule")
    commit_with_conflict_handling(db, entity_name="BarBendingSchedule")
    db.refresh(bbs_entry)
    return get_bbs_or_404(db, bbs_entry.id)


def delete_bbs_entry(db: Session, bbs_id: int) -> None:
    bbs_entry = get_bbs_or_404(db, bbs_id)
    db.delete(bbs_entry)
    commit_with_conflict_handling(db, entity_name="BarBendingSchedule")
