"""Contract service helpers."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.contract import Contract
from app.models.project import Project
from app.models.vendor import Vendor
from app.models.user import User
from app.schemas.contract import ContractCreate, ContractUpdate
from app.services.audit_service import log_audit_event, serialize_model


def _ensure_project_exists(db: Session, project_id: int) -> None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )


def _ensure_vendor_exists(db: Session, vendor_id: int) -> None:
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )


def _ensure_contract_no_unique(db: Session, contract_no: str) -> None:
    existing = db.query(Contract).filter(Contract.contract_no == contract_no).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract number already exists",
        )


def create_contract(db: Session, payload: ContractCreate, current_user: User) -> Contract:
    _ensure_project_exists(db, payload.project_id)
    _ensure_vendor_exists(db, payload.vendor_id)
    _ensure_contract_no_unique(db, payload.contract_no)

    contract = Contract(**payload.model_dump())
    db.add(contract)
    db.flush()
    log_audit_event(
        db,
        entity_type="contract",
        entity_id=contract.id,
        action="create",
        performed_by=current_user,
        after_data=serialize_model(contract),
        remarks=payload.title,
    )
    db.commit()
    db.refresh(contract)
    return contract


def list_contracts(db: Session, project_id: int | None = None) -> list[Contract]:
    query = db.query(Contract).options(joinedload(Contract.vendor))
    if project_id is not None:
        query = query.filter(Contract.project_id == project_id)
    return query.order_by(Contract.created_at.desc(), Contract.id.desc()).all()


def get_contract_or_404(db: Session, contract_id: int) -> Contract:
    contract = (
        db.query(Contract)
        .options(
            joinedload(Contract.vendor),
            joinedload(Contract.revisions),
            joinedload(Contract.boq_items),
        )
        .filter(Contract.id == contract_id)
        .first()
    )
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )
    return contract


def update_contract(
    db: Session,
    contract_id: int,
    payload: ContractUpdate,
    current_user: User,
) -> Contract:
    contract = get_contract_or_404(db, contract_id)
    updates = payload.model_dump(exclude_unset=True, mode="json")
    if "vendor_id" in updates and updates["vendor_id"] is not None:
        _ensure_vendor_exists(db, updates["vendor_id"])
    if "contract_no" in updates and updates["contract_no"] != contract.contract_no:
        _ensure_contract_no_unique(db, updates["contract_no"])

    before_data = serialize_model(contract)
    for field, value in updates.items():
        setattr(contract, field, value)
    db.flush()

    log_audit_event(
        db,
        entity_type="contract",
        entity_id=contract.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=serialize_model(contract),
    )
    db.commit()
    db.refresh(contract)
    return contract
