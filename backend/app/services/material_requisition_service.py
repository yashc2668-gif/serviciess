"""Material requisition service helpers."""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.material import Material
from app.models.contract import Contract
from app.models.material_requisition import MaterialRequisition
from app.models.material_requisition_item import MaterialRequisitionItem
from app.models.project import Project
from app.models.user import User
from app.schemas.material_requisition import (
    MaterialRequisitionCreate,
    MaterialRequisitionUpdate,
)
from app.services.audit_service import (
    log_audit_event,
    serialize_model,
    serialize_models,
)
from app.services.company_scope_service import (
    apply_material_requisition_company_scope,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    commit_with_conflict_handling,
    flush_with_conflict_handling,
)
from app.utils.pagination import PaginationParams, paginate_query

VALID_REQUISITION_STATUSES = {
    "draft",
    "submitted",
    "approved",
    "partially_issued",
    "issued",
    "rejected",
    "cancelled",
}

INITIAL_REQUISITION_STATUSES = {"draft", "submitted"}

REQUIRED_FROM_STATUSES_BY_ACTION = {
    "submit": {"draft", "rejected"},
    "approve": {"submitted"},
    "reject": {"submitted"},
}

REQUISTION_ALLOWED_STATUS_TRANSITIONS = {
    "draft": {"submitted", "cancelled"},
    "submitted": {"approved", "rejected", "cancelled"},
    "approved": {"partially_issued", "issued", "cancelled"},
    "partially_issued": {"issued", "cancelled"},
    "issued": set(),
    "rejected": {"submitted", "cancelled"},
    "cancelled": set(),
}


def _normalize_status(raw_status: str) -> str:
    normalized = raw_status.strip().lower()
    if normalized not in VALID_REQUISITION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid requisition status. "
                "Allowed values: draft, submitted, approved, partially_issued, issued, rejected, cancelled"
            ),
        )
    return normalized


def _normalize_optional_text(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    normalized = raw_value.strip()
    return normalized or None


def _normalize_requisition_no(raw_requisition_no: str) -> str:
    normalized = raw_requisition_no.strip().upper()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="requisition_no cannot be empty",
        )
    return normalized


def _ensure_unique_requisition_no(
    db: Session,
    requisition_no: str,
    *,
    exclude_requisition_id: int | None = None,
) -> None:
    query = db.query(MaterialRequisition).filter(
        func.lower(MaterialRequisition.requisition_no) == requisition_no.lower()
    )
    if exclude_requisition_id is not None:
        query = query.filter(MaterialRequisition.id != exclude_requisition_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requisition number already exists",
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
            detail="Requested by user not found",
        )


def _ensure_material_exists_for_project(db: Session, material_id: int | None, project_id: int) -> None:
    if material_id is None:
        return
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


def _validate_qty(
    *,
    requested_qty: float,
    approved_qty: float,
    issued_qty: float,
) -> None:
    if requested_qty <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="requested_qty must be greater than 0",
        )
    if approved_qty > requested_qty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="approved_qty cannot be greater than requested_qty",
        )
    if issued_qty > approved_qty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="issued_qty cannot be greater than approved_qty",
        )


def _serialize_requisition(requisition: MaterialRequisition) -> dict:
    return {
        "requisition": serialize_model(requisition),
        "items": serialize_models(list(requisition.items)),
    }


def _validate_status_transition(*, current_status: str, target_status: str) -> None:
    if target_status == current_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requisition is already {target_status}",
        )
    allowed_statuses = REQUISTION_ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
    if target_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid requisition status transition: "
                f"{current_status} -> {target_status}"
            ),
        )


def _validate_action_transition(
    *,
    current_status: str,
    action: str,
    target_status: str,
) -> None:
    allowed_from_statuses = REQUIRED_FROM_STATUSES_BY_ACTION[action]
    if current_status not in allowed_from_statuses:
        allowed_list = ", ".join(sorted(allowed_from_statuses))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot {action} requisition from status '{current_status}'. "
                f"Allowed current status: {allowed_list}."
            ),
        )
    if current_status == target_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requisition is already {target_status}",
        )


def _apply_item_updates(
    requisition: MaterialRequisition,
    item_updates: list[dict],
) -> None:
    item_map = {item.id: item for item in requisition.items}
    seen_item_ids: set[int] = set()
    for item_update in item_updates:
        item_id = item_update["id"]
        if item_id in seen_item_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate requisition item id in update payload: {item_id}",
            )
        seen_item_ids.add(item_id)
        item = item_map.get(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material requisition item not found for id={item_id}",
            )

        for field in ("requested_qty", "approved_qty", "issued_qty"):
            if field in item_update and item_update[field] is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field} cannot be null",
                )

        next_requested_qty = float(
            item_update["requested_qty"]
            if "requested_qty" in item_update
            else item.requested_qty
        )
        next_approved_qty = float(
            item_update["approved_qty"] if "approved_qty" in item_update else item.approved_qty
        )
        next_issued_qty = float(
            item_update["issued_qty"] if "issued_qty" in item_update else item.issued_qty
        )
        _validate_qty(
            requested_qty=next_requested_qty,
            approved_qty=next_approved_qty,
            issued_qty=next_issued_qty,
        )

        if "requested_qty" in item_update and item_update["requested_qty"] is not None:
            item.requested_qty = item_update["requested_qty"]
        if "approved_qty" in item_update and item_update["approved_qty"] is not None:
            item.approved_qty = item_update["approved_qty"]
        if "issued_qty" in item_update and item_update["issued_qty"] is not None:
            item.issued_qty = item_update["issued_qty"]


def list_material_requisitions(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    project_id: int | None = None,
    contract_id: int | None = None,
    status_filter: str | None = None,
    requested_by: int | None = None,
) -> dict[str, object]:
    company_id = resolve_company_scope(current_user)
    query = apply_material_requisition_company_scope(
        db.query(MaterialRequisition).options(joinedload(MaterialRequisition.items)),
        company_id,
    )
    if project_id is not None:
        query = query.filter(MaterialRequisition.project_id == project_id)
    if contract_id is not None:
        query = query.filter(MaterialRequisition.contract_id == contract_id)
    if requested_by is not None:
        query = query.filter(MaterialRequisition.requested_by == requested_by)
    if status_filter:
        query = query.filter(
            MaterialRequisition.status == _normalize_status(status_filter)
        )
    return paginate_query(
        query.order_by(MaterialRequisition.created_at.desc(), MaterialRequisition.id.desc()),
        pagination=pagination,
    )


def get_material_requisition_or_404(
    db: Session,
    requisition_id: int,
) -> MaterialRequisition:
    requisition = (
        db.query(MaterialRequisition)
        .options(joinedload(MaterialRequisition.items))
        .filter(MaterialRequisition.id == requisition_id)
        .first()
    )
    if not requisition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material requisition not found",
        )
    return requisition


def create_material_requisition(
    db: Session,
    payload: MaterialRequisitionCreate,
    current_user: User,
) -> MaterialRequisition:
    data = payload.model_dump()
    data["requisition_no"] = _normalize_requisition_no(data["requisition_no"])
    data["status"] = _normalize_status(data["status"])
    if data["status"] not in INITIAL_REQUISITION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Material requisition can only be created in draft or submitted status",
        )
    data["requested_by"] = data.get("requested_by") or current_user.id
    if data.get("remarks") is not None:
        data["remarks"] = data["remarks"].strip() or None

    _ensure_unique_requisition_no(db, data["requisition_no"])
    _ensure_project_exists(db, data["project_id"])
    _ensure_contract_exists_for_project(
        db,
        contract_id=data.get("contract_id"),
        project_id=data["project_id"],
    )
    _ensure_user_exists(db, data["requested_by"])

    raw_items = data.pop("items")
    material_ids: set[int] = set()
    custom_names: set[str] = set()
    for item in raw_items:
        material_id = item.get("material_id")
        custom_name = item.get("custom_material_name")
        
        if material_id is not None:
            if material_id in material_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate material_id in items: {material_id}",
                )
            material_ids.add(material_id)
        elif custom_name:
            normalized_name = custom_name.strip().lower()
            if normalized_name in custom_names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate custom material name in items: {custom_name}",
                )
            custom_names.add(normalized_name)
        
        _ensure_material_exists_for_project(db, material_id, data["project_id"])
        _validate_qty(
            requested_qty=float(item["requested_qty"]),
            approved_qty=float(item.get("approved_qty", 0)),
            issued_qty=float(item.get("issued_qty", 0)),
        )

    requisition = MaterialRequisition(**data)
    db.add(requisition)
    flush_with_conflict_handling(db, entity_name="Material requisition")

    items: list[MaterialRequisitionItem] = []
    for item in raw_items:
        requisition_item = MaterialRequisitionItem(
            requisition_id=requisition.id,
            material_id=item.get("material_id"),
            custom_material_name=item.get("custom_material_name"),
            requested_qty=item["requested_qty"],
            approved_qty=item.get("approved_qty", 0),
            issued_qty=item.get("issued_qty", 0),
        )
        items.append(requisition_item)
    db.add_all(items)
    flush_with_conflict_handling(db, entity_name="Material requisition")

    log_audit_event(
        db,
        entity_type="material_requisition",
        entity_id=requisition.id,
        action="create",
        performed_by=current_user,
        after_data=_serialize_requisition(requisition),
        remarks=requisition.requisition_no,
    )
    commit_with_conflict_handling(db, entity_name="Material requisition")
    return get_material_requisition_or_404(db, requisition.id)


def update_material_requisition(
    db: Session,
    requisition_id: int,
    payload: MaterialRequisitionUpdate,
    current_user: User,
) -> MaterialRequisition:
    requisition = get_material_requisition_or_404(db, requisition_id)
    updates = payload.model_dump(exclude_unset=True)

    for field in ("requisition_no", "status"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} cannot be null",
            )

    if "requisition_no" in updates and updates["requisition_no"] is not None:
        updates["requisition_no"] = _normalize_requisition_no(updates["requisition_no"])
        _ensure_unique_requisition_no(
            db,
            updates["requisition_no"],
            exclude_requisition_id=requisition.id,
        )
    if "status" in updates and updates["status"] is not None:
        updates["status"] = _normalize_status(updates["status"])
        _validate_status_transition(
            current_status=requisition.status,
            target_status=updates["status"],
        )
    if "contract_id" in updates:
        _ensure_contract_exists_for_project(
            db,
            contract_id=updates["contract_id"],
            project_id=requisition.project_id,
        )
    if "remarks" in updates:
        updates["remarks"] = _normalize_optional_text(updates["remarks"])
    if requisition.status in {"issued", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{requisition.status.capitalize()} material requisition is immutable",
        )

    before_data = _serialize_requisition(requisition)

    for field in ("requisition_no", "contract_id", "status", "remarks"):
        if field in updates:
            setattr(requisition, field, updates[field])

    if "items" in updates and updates["items"] is not None:
        _apply_item_updates(requisition, updates["items"])

    flush_with_conflict_handling(db, entity_name="Material requisition")
    log_audit_event(
        db,
        entity_type="material_requisition",
        entity_id=requisition.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=_serialize_requisition(requisition),
        remarks=requisition.requisition_no,
    )
    commit_with_conflict_handling(db, entity_name="Material requisition")
    return get_material_requisition_or_404(db, requisition.id)


def transition_material_requisition_status(
    db: Session,
    requisition_id: int,
    *,
    action: str,
    target_status: str,
    current_user: User,
    remarks: str | None = None,
    item_updates: list[dict] | None = None,
) -> MaterialRequisition:
    requisition = get_material_requisition_or_404(db, requisition_id)
    current_status = requisition.status
    _validate_action_transition(
        current_status=current_status,
        action=action,
        target_status=target_status,
    )

    before_data = _serialize_requisition(requisition)

    if item_updates is not None:
        _apply_item_updates(requisition, item_updates)

    if remarks is not None:
        requisition.remarks = _normalize_optional_text(remarks)

    requisition.status = target_status
    flush_with_conflict_handling(db, entity_name="Material requisition")

    log_audit_event(
        db,
        entity_type="material_requisition",
        entity_id=requisition.id,
        action=action,
        performed_by=current_user,
        before_data=before_data,
        after_data=_serialize_requisition(requisition),
        remarks=f"{current_status} -> {target_status}",
    )
    commit_with_conflict_handling(db, entity_name="Material requisition")
    return get_material_requisition_or_404(db, requisition.id)


def submit_material_requisition(
    db: Session,
    requisition_id: int,
    current_user: User,
    *,
    remarks: str | None = None,
) -> MaterialRequisition:
    return transition_material_requisition_status(
        db,
        requisition_id,
        action="submit",
        target_status="submitted",
        current_user=current_user,
        remarks=remarks,
    )


def approve_material_requisition(
    db: Session,
    requisition_id: int,
    current_user: User,
    *,
    remarks: str | None = None,
    item_updates: list[dict] | None = None,
) -> MaterialRequisition:
    return transition_material_requisition_status(
        db,
        requisition_id,
        action="approve",
        target_status="approved",
        current_user=current_user,
        remarks=remarks,
        item_updates=item_updates,
    )


def reject_material_requisition(
    db: Session,
    requisition_id: int,
    current_user: User,
    *,
    remarks: str | None = None,
) -> MaterialRequisition:
    return transition_material_requisition_status(
        db,
        requisition_id,
        action="reject",
        target_status="rejected",
        current_user=current_user,
        remarks=remarks,
    )


def delete_material_requisition(
    db: Session,
    requisition_id: int,
    current_user: User,
) -> None:
    requisition = get_material_requisition_or_404(db, requisition_id)
    
    # Only allow deleting draft or rejected requisitions
    if requisition.status not in {"draft", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete requisition with status '{requisition.status}'. Only draft or rejected requisitions can be deleted.",
        )
    
    # Only allow creator or admin to delete
    if requisition.requested_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator or admin can delete this requisition.",
        )
    
    # Store data for audit before deletion
    before_data = _serialize_requisition(requisition)
    requisition_no = requisition.requisition_no
    
    # Delete the requisition (cascade will delete items)
    db.delete(requisition)
    flush_with_conflict_handling(db, entity_name="Material requisition")
    
    log_audit_event(
        db,
        entity_type="material_requisition",
        entity_id=requisition_id,
        action="delete",
        performed_by=current_user,
        before_data=before_data,
        after_data=None,
        remarks=requisition_no,
    )
    commit_with_conflict_handling(db, entity_name="Material requisition")
