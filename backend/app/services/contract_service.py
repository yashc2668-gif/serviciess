"""Contract service helpers."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.contract import Contract
from app.models.project import Project
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.contract import ContractCreate, ContractUpdate
from app.services.audit_service import log_audit_event, serialize_model
from app.services.company_scope_service import (
    apply_contract_company_scope,
    apply_project_company_scope,
    apply_vendor_company_scope,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    commit_with_conflict_handling,
    ensure_lock_version_matches,
    flush_with_conflict_handling,
)
from app.utils.pagination import PaginationParams, paginate_query


def _get_project_or_404(
    db: Session,
    project_id: int,
    *,
    company_id: int | None = None,
) -> Project:
    query = db.query(Project).filter(Project.is_deleted.is_(False), Project.id == project_id)
    query = apply_project_company_scope(query, company_id)
    project = query.first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def _get_vendor_or_404(
    db: Session,
    vendor_id: int,
    *,
    company_id: int | None = None,
) -> Vendor:
    query = db.query(Vendor).filter(Vendor.is_deleted.is_(False), Vendor.id == vendor_id)
    query = apply_vendor_company_scope(query, company_id)
    vendor = query.first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )
    return vendor


def _ensure_contract_no_unique(db: Session, contract_no: str) -> None:
    existing = (
        db.query(Contract)
        .filter(Contract.contract_no == contract_no, Contract.is_deleted.is_(False))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract number already exists",
        )


def create_contract(db: Session, payload: ContractCreate, current_user: User) -> Contract:
    company_id = resolve_company_scope(current_user)
    project = _get_project_or_404(db, payload.project_id, company_id=company_id)
    _get_vendor_or_404(db, payload.vendor_id, company_id=project.company_id)
    _ensure_contract_no_unique(db, payload.contract_no)

    contract = Contract(**payload.model_dump())
    db.add(contract)
    flush_with_conflict_handling(db, entity_name="Contract")
    log_audit_event(
        db,
        entity_type="contract",
        entity_id=contract.id,
        action="create",
        performed_by=current_user,
        after_data=serialize_model(contract),
        remarks=payload.title,
    )
    commit_with_conflict_handling(db, entity_name="Contract")
    db.refresh(contract)
    return contract


def list_contracts(
    db: Session,
    current_user: User,
    project_id: int | None = None,
    *,
    pagination: PaginationParams,
) -> dict[str, object]:
    company_id = resolve_company_scope(current_user)
    query = db.query(Contract).options(joinedload(Contract.vendor)).filter(Contract.is_deleted.is_(False))
    query = apply_contract_company_scope(query, company_id)
    if project_id is not None:
        query = query.filter(Contract.project_id == project_id)
    return paginate_query(
        query.order_by(Contract.created_at.desc(), Contract.id.desc()),
        pagination=pagination,
    )


def get_contract_or_404(db: Session, contract_id: int, *, current_user: User) -> Contract:
    company_id = resolve_company_scope(current_user)
    contract = (
        apply_contract_company_scope(
            db.query(Contract)
            .options(
                joinedload(Contract.vendor),
                joinedload(Contract.revisions),
                joinedload(Contract.boq_items),
            )
            .filter(Contract.is_deleted.is_(False)),
            company_id,
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
    contract = get_contract_or_404(db, contract_id, current_user=current_user)
    updates = payload.model_dump(exclude_unset=True, mode="json")
    ensure_lock_version_matches(
        contract,
        updates.pop("lock_version", None),
        entity_name="Contract",
    )
    company_id = resolve_company_scope(current_user)
    if "vendor_id" in updates and updates["vendor_id"] is not None:
        _get_vendor_or_404(db, updates["vendor_id"], company_id=company_id)
    if "contract_no" in updates and updates["contract_no"] != contract.contract_no:
        _ensure_contract_no_unique(db, updates["contract_no"])

    before_data = serialize_model(contract)
    for field, value in updates.items():
        setattr(contract, field, value)
    flush_with_conflict_handling(db, entity_name="Contract")

    log_audit_event(
        db,
        entity_type="contract",
        entity_id=contract.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=serialize_model(contract),
    )
    commit_with_conflict_handling(db, entity_name="Contract")
    db.refresh(contract)
    return contract


def delete_contract(db: Session, contract_id: int, current_user: User) -> None:
    """Soft-delete a contract after checking for active child records."""
    from app.models.boq import BOQItem
    from app.models.measurement import Measurement
    from app.models.payment import Payment
    from app.models.ra_bill import RABill
    from app.models.secured_advance import SecuredAdvance

    contract = get_contract_or_404(db, contract_id, current_user=current_user)
    dependencies: list[str] = []
    dependency_checks = (
        (
            "active_ra_bills",
            db.query(RABill.id).filter(
                RABill.contract_id == contract.id,
                RABill.status.notin_(["cancelled", "rejected"]),
            ),
        ),
        (
            "active_payments",
            db.query(Payment.id).filter(
                Payment.contract_id == contract.id,
                Payment.status != "cancelled",
            ),
        ),
        (
            "active_secured_advances",
            db.query(SecuredAdvance.id).filter(
                SecuredAdvance.contract_id == contract.id,
                SecuredAdvance.status != "written_off",
            ),
        ),
        (
            "measurements",
            db.query(Measurement.id).filter(
                Measurement.contract_id == contract.id,
                Measurement.status.notin_(["cancelled", "rejected"]),
            ),
        ),
        (
            "boq_items",
            db.query(BOQItem.id).filter(BOQItem.contract_id == contract.id),
        ),
    )
    for label, query in dependency_checks:
        if query.first():
            dependencies.append(label)
    if dependencies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Contract cannot be deleted because it is referenced by: "
                + ", ".join(dependencies)
            ),
        )

    before_data = serialize_model(contract)
    log_audit_event(
        db,
        entity_type="contract",
        entity_id=contract.id,
        action="delete",
        performed_by=current_user,
        before_data=before_data,
        remarks=contract.title,
    )
    contract.is_deleted = True
    contract.deleted_at = datetime.now(timezone.utc)
    flush_with_conflict_handling(db, entity_name="Contract")
    commit_with_conflict_handling(db, entity_name="Contract")
