"""Material master service helpers."""

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.material import Material
from app.models.project import Project
from app.models.user import User
from app.schemas.material import MaterialCreate, MaterialUpdate
from app.services.audit_service import log_audit_event, serialize_model
from app.services.company_scope_service import (
    apply_material_company_scope,
    ensure_company_exists,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    commit_with_conflict_handling,
    ensure_lock_version_matches,
    flush_with_conflict_handling,
)
from app.services.inventory_service import record_inventory_transactions_from_stock_deltas
from app.utils.pagination import PaginationParams, paginate_query
from app.utils.sorting import SortDirection, apply_sorting


MATERIAL_ATTENTION_RANK = case(
    (Material.is_active.is_(False), 3),
    (Material.current_stock <= 0, 0),
    (Material.current_stock <= Material.reorder_level, 1),
    else_=2,
)

MATERIAL_SCOPE_NAME = func.coalesce(Project.name, Company.name, "")

MATERIAL_SORT_OPTIONS = {
    "item_name": (Material.item_name, Material.id),
    "scope_name": (MATERIAL_SCOPE_NAME, Material.id),
    "current_stock": (Material.current_stock, Material.id),
    "reorder_level": (Material.reorder_level, Material.id),
    "default_rate": (Material.default_rate, Material.id),
    "attention": (MATERIAL_ATTENTION_RANK, Material.item_name, Material.id),
    "created_at": (Material.created_at, Material.id),
}

MATERIAL_DEFAULT_ORDER = (Material.item_name.asc(), Material.id.asc())


def _apply_attention_filter(query, attention: str | None):
    if not attention:
        return query

    normalized_attention = attention.strip().lower()
    if normalized_attention == "critical":
        return query.filter(
            Material.is_active.is_(True),
            Material.current_stock <= 0,
        )
    if normalized_attention == "watch":
        return query.filter(
            Material.is_active.is_(True),
            Material.current_stock > 0,
            Material.current_stock <= Material.reorder_level,
        )
    if normalized_attention == "healthy":
        return query.filter(
            Material.is_active.is_(True),
            Material.current_stock > Material.reorder_level,
        )
    if normalized_attention == "inactive":
        return query.filter(Material.is_active.is_(False))
    return query


def list_materials(
    db: Session,
    current_user: User,
    *,
    pagination: PaginationParams,
    is_active: bool | None = None,
    category: str | None = None,
    company_id: int | None = None,
    project_id: int | None = None,
    search: str | None = None,
    attention: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
) -> dict[str, object]:
    scoped_company_id = resolve_company_scope(current_user, company_id)
    query = apply_material_company_scope(db.query(Material), scoped_company_id).outerjoin(
        Project,
        Project.id == Material.project_id,
    ).outerjoin(
        Company,
        Company.id == Material.company_id,
    )
    if is_active is not None:
        query = query.filter(Material.is_active == is_active)
    if category:
        query = query.filter(func.lower(Material.category) == category.strip().lower())
    if company_id is not None:
        query = query.filter(Material.company_id == company_id)
    if project_id is not None:
        query = query.filter(Material.project_id == project_id)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Material.item_code.ilike(search_term),
                Material.item_name.ilike(search_term),
                Material.category.ilike(search_term),
                Project.name.ilike(search_term),
                Company.name.ilike(search_term),
            )
        )
    query = _apply_attention_filter(query, attention)
    return paginate_query(
        apply_sorting(
            query,
            sort_by=sort_by,
            sort_dir=sort_dir,
            sort_options=MATERIAL_SORT_OPTIONS,
            default_order=MATERIAL_DEFAULT_ORDER,
        ),
        pagination=pagination,
    )


def list_materials_for_export(
    db: Session,
    current_user: User,
    *,
    is_active: bool | None = None,
    category: str | None = None,
    company_id: int | None = None,
    project_id: int | None = None,
    search: str | None = None,
    attention: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
) -> list[Material]:
    scoped_company_id = resolve_company_scope(current_user, company_id)
    query = apply_material_company_scope(db.query(Material), scoped_company_id).outerjoin(
        Project,
        Project.id == Material.project_id,
    ).outerjoin(
        Company,
        Company.id == Material.company_id,
    )
    if is_active is not None:
        query = query.filter(Material.is_active == is_active)
    if category:
        query = query.filter(func.lower(Material.category) == category.strip().lower())
    if company_id is not None:
        query = query.filter(Material.company_id == company_id)
    if project_id is not None:
        query = query.filter(Material.project_id == project_id)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Material.item_code.ilike(search_term),
                Material.item_name.ilike(search_term),
                Material.category.ilike(search_term),
                Project.name.ilike(search_term),
                Company.name.ilike(search_term),
            )
        )
    query = _apply_attention_filter(query, attention)
    return apply_sorting(
        query,
        sort_by=sort_by,
        sort_dir=sort_dir,
        sort_options=MATERIAL_SORT_OPTIONS,
        default_order=MATERIAL_DEFAULT_ORDER,
    ).all()


def get_material_stock_summary(
    db: Session,
    current_user: User,
    *,
    group_by: str = "project",
    company_id: int | None = None,
    project_id: int | None = None,
    is_active: bool | None = None,
) -> list[dict]:
    scoped_company_id = resolve_company_scope(current_user, company_id)
    normalized_group_by = group_by.strip().lower()
    if normalized_group_by not in {"project", "company"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_by must be either 'project' or 'company'",
        )

    if normalized_group_by == "project":
        query = (
            db.query(
                Material.project_id.label("scope_id"),
                Project.name.label("scope_name"),
                func.count(Material.id).label("material_count"),
                func.coalesce(func.sum(Material.current_stock), 0).label("total_stock"),
            )
            .outerjoin(Project, Project.id == Material.project_id)
        )
        if scoped_company_id is not None:
            query = query.filter(Material.company_id == scoped_company_id)
        if project_id is not None:
            query = query.filter(Material.project_id == project_id)
        if is_active is not None:
            query = query.filter(Material.is_active == is_active)
        rows = (
            query.group_by(Material.project_id, Project.name)
            .order_by(Project.name.asc(), Material.project_id.asc())
            .all()
        )
    else:
        query = (
            db.query(
                Material.company_id.label("scope_id"),
                Company.name.label("scope_name"),
                func.count(Material.id).label("material_count"),
                func.coalesce(func.sum(Material.current_stock), 0).label("total_stock"),
            )
            .outerjoin(Company, Company.id == Material.company_id)
        )
        if scoped_company_id is not None:
            query = query.filter(Material.company_id == scoped_company_id)
        if project_id is not None:
            query = query.filter(Material.project_id == project_id)
        if is_active is not None:
            query = query.filter(Material.is_active == is_active)
        rows = (
            query.group_by(Material.company_id, Company.name)
            .order_by(Company.name.asc(), Material.company_id.asc())
            .all()
        )

    return [
        {
            "scope_type": normalized_group_by,
            "scope_id": row.scope_id,
            "scope_name": row.scope_name,
            "material_count": int(row.material_count or 0),
            "total_stock": float(row.total_stock or 0),
        }
        for row in rows
    ]


def get_material_or_404(db: Session, material_id: int, *, current_user: User) -> Material:
    material = (
        apply_material_company_scope(
            db.query(Material),
            resolve_company_scope(current_user),
        )
        .filter(Material.id == material_id)
        .first()
    )
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found",
        )
    return material


def _ensure_unique_item_code(
    db: Session,
    item_code: str,
    *,
    exclude_material_id: int | None = None,
) -> None:
    query = db.query(Material).filter(func.lower(Material.item_code) == item_code.lower())
    if exclude_material_id is not None:
        query = query.filter(Material.id != exclude_material_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Material item code already exists",
        )


def _validate_scope(
    db: Session,
    current_user: User,
    *,
    company_id: int | None,
    project_id: int | None,
) -> tuple[int | None, int | None]:
    project: Project | None = None
    scoped_company_id = resolve_company_scope(current_user, company_id)
    if project_id is not None:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.is_deleted.is_(False))
            .first()
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

    if scoped_company_id is not None:
        ensure_company_exists(db.query(Company), scoped_company_id)

    if project is not None and scoped_company_id is not None and project.company_id != scoped_company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project does not belong to the provided company",
        )

    resolved_company_id = scoped_company_id
    if project is not None and resolved_company_id is None:
        resolved_company_id = project.company_id

    return resolved_company_id, project_id


def create_material(db: Session, payload: MaterialCreate, current_user: User) -> Material:
    data = payload.model_dump()
    data["item_code"] = data["item_code"].strip().upper()
    data["item_name"] = data["item_name"].strip()
    data["unit"] = data["unit"].strip()
    if not data["item_code"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="item_code cannot be empty",
        )
    if not data["item_name"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="item_name cannot be empty",
        )
    if not data["unit"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unit cannot be empty",
        )
    if data.get("category") is not None:
        data["category"] = data["category"].strip() or None

    _ensure_unique_item_code(db, data["item_code"])
    data["company_id"], data["project_id"] = _validate_scope(
        db,
        current_user=current_user,
        company_id=data.get("company_id"),
        project_id=data.get("project_id"),
    )

    material = Material(**data)
    db.add(material)
    flush_with_conflict_handling(db, entity_name="Material")
    if float(material.current_stock) > 0:
        record_inventory_transactions_from_stock_deltas(
            db,
            stock_deltas={material.id: float(material.current_stock)},
            transaction_type="material_opening_balance",
            transaction_date=date.today(),
            reference_type="material",
            reference_id=material.id,
            project_id=material.project_id,
            remarks="Opening stock from material creation",
        )
    log_audit_event(
        db,
        entity_type="material",
        entity_id=material.id,
        action="create",
        performed_by=current_user,
        after_data=serialize_model(material),
        remarks=material.item_name,
    )
    commit_with_conflict_handling(db, entity_name="Material")
    db.refresh(material)
    return material


def update_material(
    db: Session,
    material_id: int,
    payload: MaterialUpdate,
    current_user: User,
) -> Material:
    material = get_material_or_404(db, material_id, current_user=current_user)
    previous_stock = float(material.current_stock)
    updates = payload.model_dump(exclude_unset=True)
    ensure_lock_version_matches(
        material,
        updates.pop("lock_version", None),
        entity_name="Material",
    )

    for field in (
        "item_code",
        "item_name",
        "unit",
        "reorder_level",
        "default_rate",
        "current_stock",
        "is_active",
    ):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} cannot be null",
            )

    if "item_code" in updates and updates["item_code"] is not None:
        updates["item_code"] = updates["item_code"].strip().upper()
        if not updates["item_code"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="item_code cannot be empty",
            )
    if "item_name" in updates and updates["item_name"] is not None:
        updates["item_name"] = updates["item_name"].strip()
        if not updates["item_name"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="item_name cannot be empty",
            )
    if "unit" in updates and updates["unit"] is not None:
        updates["unit"] = updates["unit"].strip()
        if not updates["unit"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="unit cannot be empty",
            )
    if "category" in updates:
        updates["category"] = (updates["category"] or "").strip() or None

    next_item_code = updates.get("item_code", material.item_code)
    _ensure_unique_item_code(db, next_item_code, exclude_material_id=material.id)

    next_company_id = updates.get("company_id", material.company_id)
    next_project_id = updates.get("project_id", material.project_id)
    next_company_id, next_project_id = _validate_scope(
        db,
        current_user=current_user,
        company_id=next_company_id,
        project_id=next_project_id,
    )
    updates["company_id"] = next_company_id
    updates["project_id"] = next_project_id

    before_data = serialize_model(material)
    for field, value in updates.items():
        setattr(material, field, value)
    flush_with_conflict_handling(db, entity_name="Material")
    if "current_stock" in updates and updates["current_stock"] is not None:
        stock_delta = round(float(material.current_stock) - previous_stock, 3)
        if stock_delta != 0:
            record_inventory_transactions_from_stock_deltas(
                db,
                stock_deltas={material.id: stock_delta},
                transaction_type="material_manual_adjustment",
                transaction_date=date.today(),
                reference_type="material",
                reference_id=material.id,
                project_id=material.project_id,
                remarks="Manual stock update from material master",
            )
    log_audit_event(
        db,
        entity_type="material",
        entity_id=material.id,
        action="update",
        performed_by=current_user,
        before_data=before_data,
        after_data=serialize_model(material),
        remarks=material.item_name,
    )
    commit_with_conflict_handling(db, entity_name="Material")
    db.refresh(material)
    return material


def delete_material(db: Session, material_id: int, current_user: User) -> None:
    """Deactivate a material after checking for active child references."""
    from app.models.material_issue import MaterialIssue, MaterialIssueItem
    from app.models.material_receipt import MaterialReceipt, MaterialReceiptItem
    from app.models.material_requisition import MaterialRequisition, MaterialRequisitionItem

    material = get_material_or_404(db, material_id, current_user=current_user)
    dependencies: list[str] = []
    dependency_checks = (
        (
            "active_receipts",
            db.query(MaterialReceipt.id)
            .join(MaterialReceiptItem, MaterialReceiptItem.receipt_id == MaterialReceipt.id)
            .filter(
                MaterialReceiptItem.material_id == material.id,
                MaterialReceipt.status.notin_(["cancelled"]),
            ),
        ),
        (
            "active_issues",
            db.query(MaterialIssue.id)
            .join(MaterialIssueItem, MaterialIssueItem.issue_id == MaterialIssue.id)
            .filter(
                MaterialIssueItem.material_id == material.id,
                MaterialIssue.status.notin_(["cancelled"]),
            ),
        ),
        (
            "active_requisitions",
            db.query(MaterialRequisition.id)
            .join(
                MaterialRequisitionItem,
                MaterialRequisitionItem.requisition_id == MaterialRequisition.id,
            )
            .filter(
                MaterialRequisitionItem.material_id == material.id,
                MaterialRequisition.status.notin_(["cancelled", "rejected"]),
            ),
        ),
    )
    for label, query in dependency_checks:
        if query.first():
            dependencies.append(label)
    if material.current_stock and float(material.current_stock) > 0:
        dependencies.append("positive_stock_balance")
    if dependencies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Material cannot be deleted because it is referenced by: "
                + ", ".join(dependencies)
            ),
        )

    before_data = serialize_model(material)
    log_audit_event(
        db,
        entity_type="material",
        entity_id=material.id,
        action="delete",
        performed_by=current_user,
        before_data=before_data,
        remarks=material.item_name,
    )
    material.is_active = False
    flush_with_conflict_handling(db, entity_name="Material")
    commit_with_conflict_handling(db, entity_name="Material")
