"""Labour productivity service helpers."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.labour import Labour
from app.models.labour_productivity import LabourProductivity
from app.models.project import Project
from app.models.user import User
from app.schemas.labour_productivity import LabourProductivityCreate, LabourProductivityUpdate
from app.services.audit_service import log_audit_event, serialize_model
from app.services.company_scope_service import (
    apply_labour_productivity_company_scope,
    resolve_company_scope,
)
from app.utils.pagination import PaginationParams, paginate_query


def _normalize_optional_text(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    return raw_value.strip() or None


def _ensure_project_exists(db: Session, project_id: int) -> None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )


def _ensure_labour_exists(db: Session, labour_id: int | None) -> None:
    if labour_id is None:
        return
    labour = db.query(Labour).filter(Labour.id == labour_id).first()
    if not labour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labour not found",
        )


def _ensure_contract_exists(
    db: Session,
    contract_id: int | None,
    *,
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


def list_labour_productivities(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    project_id: int | None = None,
    contract_id: int | None = None,
    labour_id: int | None = None,
    trade: str | None = None,
) -> dict[str, object]:
    company_id = resolve_company_scope(current_user)
    query = apply_labour_productivity_company_scope(
        db.query(LabourProductivity),
        company_id,
    )
    if project_id is not None:
        query = query.filter(LabourProductivity.project_id == project_id)
    if contract_id is not None:
        query = query.filter(LabourProductivity.contract_id == contract_id)
    if labour_id is not None:
        query = query.filter(LabourProductivity.labour_id == labour_id)
    if trade:
        query = query.filter(LabourProductivity.trade.ilike(f"%{trade.strip()}%"))
    return paginate_query(
        query.order_by(
            LabourProductivity.productivity_date.desc(),
            LabourProductivity.id.desc(),
        ),
        pagination=pagination,
    )


def get_labour_productivity_or_404(
    db: Session,
    productivity_id: int,
) -> LabourProductivity:
    productivity = (
        db.query(LabourProductivity)
        .filter(LabourProductivity.id == productivity_id)
        .first()
    )
    if not productivity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Labour productivity entry not found",
        )
    return productivity


def create_labour_productivity(
    db: Session,
    payload: LabourProductivityCreate,
    current_user: User,
) -> LabourProductivity:
    data = payload.model_dump()
    data["trade"] = data["trade"].strip()
    if not data["trade"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="trade cannot be empty",
        )
    data["date"] = data["date"]
    data["productivity_date"] = data["date"]
    data["activity_name"] = data["trade"]
    data["quantity"] = float(data["quantity_done"])
    labour_count = int(data["labour_count"])
    if labour_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="labour_count must be greater than 0",
        )
    productivity_value = data.get("productivity_value")
    if productivity_value is None:
        data["productivity_value"] = round(float(data["quantity_done"]) / labour_count, 3)
    else:
        data["productivity_value"] = float(productivity_value)

    data["unit"] = data["unit"].strip()
    if not data["unit"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unit cannot be empty",
        )
    data["remarks"] = _normalize_optional_text(data.get("remarks"))

    _ensure_project_exists(db, data["project_id"])
    _ensure_contract_exists(db, data.get("contract_id"), project_id=data["project_id"])
    _ensure_labour_exists(db, data.get("labour_id"))

    productivity = LabourProductivity(**data)
    db.add(productivity)
    db.flush()
    log_audit_event(
        db,
        entity_type="labour_productivity",
        entity_id=productivity.id,
        action="create",
        performed_by=current_user,
        after_data=serialize_model(productivity),
        remarks=productivity.activity_name,
    )
    db.commit()
    db.refresh(productivity)
    return productivity


def update_labour_productivity(
    db: Session,
    productivity_id: int,
    payload: LabourProductivityUpdate,
    current_user: User,
) -> LabourProductivity:
    productivity = get_labour_productivity_or_404(db, productivity_id)
    updates = payload.model_dump(exclude_unset=True)

    if "trade" in updates and updates["trade"] is not None:
        updates["trade"] = updates["trade"].strip()
        if not updates["trade"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="trade cannot be empty",
            )
        updates["activity_name"] = updates["trade"]
    if "date" in updates and updates["date"] is not None:
        updates["productivity_date"] = updates["date"]
    if "labour_count" in updates and updates["labour_count"] is not None:
        if int(updates["labour_count"]) <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="labour_count must be greater than 0",
            )
    if "quantity_done" in updates and updates["quantity_done"] is not None:
        updates["quantity"] = float(updates["quantity_done"])
    if "unit" in updates and updates["unit"] is not None:
        updates["unit"] = updates["unit"].strip()
        if not updates["unit"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unit cannot be empty",
            )
    if "remarks" in updates:
        updates["remarks"] = _normalize_optional_text(updates["remarks"])

    next_contract_id = updates.get("contract_id", productivity.contract_id)
    _ensure_contract_exists(db, next_contract_id, project_id=productivity.project_id)
    _ensure_labour_exists(db, updates.get("labour_id", productivity.labour_id))

    next_quantity_done = float(updates.get("quantity_done", productivity.quantity_done))
    next_labour_count = int(updates.get("labour_count", productivity.labour_count or 1))
    if "productivity_value" not in updates or updates["productivity_value"] is None:
        updates["productivity_value"] = round(next_quantity_done / next_labour_count, 3)

    before_data = serialize_model(productivity)
    for field, value in updates.items():
        setattr(productivity, field, value)
    db.flush()
    log_audit_event(
        db,
        entity_type="labour_productivity",
        entity_id=productivity.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=serialize_model(productivity),
        remarks=productivity.activity_name,
    )
    db.commit()
    db.refresh(productivity)
    return productivity
