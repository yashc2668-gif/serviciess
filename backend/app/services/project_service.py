"""Project service helpers."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.contract import Contract
from app.models.inventory_transaction import InventoryTransaction
from app.models.labour_advance import LabourAdvance
from app.models.labour_attendance import LabourAttendance
from app.models.labour_bill import LabourBill
from app.models.labour_productivity import LabourProductivity
from app.models.material import Material
from app.models.material_issue import MaterialIssue
from app.models.material_receipt import MaterialReceipt
from app.models.material_requisition import MaterialRequisition
from app.models.material_stock_adjustment import MaterialStockAdjustment
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.company_scope_service import (
    apply_project_company_scope,
    ensure_company_exists,
    require_company_scope,
    resolve_company_scope,
)
from app.services.concurrency_service import (
    commit_with_conflict_handling,
    ensure_lock_version_matches,
    flush_with_conflict_handling,
)
from app.utils.pagination import PaginationParams, paginate_query
from app.utils.sorting import SortDirection, apply_sorting


def _base_project_query(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
):
    scoped_company_id = resolve_company_scope(current_user, company_id)
    query = db.query(Project).filter(Project.is_deleted.is_(False))
    return apply_project_company_scope(query, scoped_company_id)


PROJECT_SORT_OPTIONS = {
    "name": (Project.name, Project.id),
    "company_name": (func.coalesce(Company.name, ""), Project.id),
    "client_name": (func.coalesce(Project.client_name, ""), Project.id),
    "revised_value": (Project.revised_value, Project.id),
    "start_date": (Project.start_date, Project.id),
    "status": (Project.status, Project.id),
    "created_at": (Project.created_at, Project.id),
}

PROJECT_DEFAULT_ORDER = (Project.created_at.desc(), Project.id.desc())


def _project_list_query(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
):
    query = _base_project_query(db, current_user=current_user, company_id=company_id).outerjoin(
        Company,
        Company.id == Project.company_id,
    )
    if status_filter:
        query = query.filter(Project.status == status_filter.strip().lower())
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Project.name.ilike(search_term),
                Project.code.ilike(search_term),
                Project.client_name.ilike(search_term),
                Project.location.ilike(search_term),
                Company.name.ilike(search_term),
            )
        )
    return query


def list_projects(
    db: Session,
    *,
    current_user: User,
    pagination: PaginationParams,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
) -> dict[str, object]:
    query = _project_list_query(
        db,
        current_user=current_user,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
    )
    return paginate_query(
        apply_sorting(
            query,
            sort_by=sort_by,
            sort_dir=sort_dir,
            sort_options=PROJECT_SORT_OPTIONS,
            default_order=PROJECT_DEFAULT_ORDER,
        ),
        pagination=pagination,
    )


def list_projects_for_export(
    db: Session,
    *,
    current_user: User,
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: SortDirection = SortDirection.ASC,
) -> list[Project]:
    query = _project_list_query(
        db,
        current_user=current_user,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
    )
    return apply_sorting(
        query,
        sort_by=sort_by,
        sort_dir=sort_dir,
        sort_options=PROJECT_SORT_OPTIONS,
        default_order=PROJECT_DEFAULT_ORDER,
    ).all()


def get_project_or_404(
    db: Session,
    project_id: int,
    *,
    current_user: User,
    company_id: int | None = None,
) -> Project:
    project = (
        _base_project_query(db, current_user=current_user, company_id=company_id)
        .filter(Project.id == project_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def _ensure_unique_code(db: Session, code: str | None, exclude_project_id: int | None = None) -> None:
    if not code:
        return
    query = db.query(Project).filter(Project.code == code, Project.is_deleted.is_(False))
    if exclude_project_id is not None:
        query = query.filter(Project.id != exclude_project_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project code already exists",
        )


def create_project(db: Session, payload: ProjectCreate, current_user: User) -> Project:
    company_id = require_company_scope(current_user, payload.company_id)
    ensure_company_exists(db.query(Company), company_id)
    _ensure_unique_code(db, payload.code)

    project = Project(**payload.model_dump(exclude={"company_id"}), company_id=company_id)
    db.add(project)
    commit_with_conflict_handling(db, entity_name="Project")
    db.refresh(project)
    return project


def update_project(
    db: Session,
    project_id: int,
    payload: ProjectUpdate,
    current_user: User,
) -> Project:
    project = get_project_or_404(db, project_id, current_user=current_user)
    update_data = payload.model_dump(exclude_unset=True)
    ensure_lock_version_matches(
        project,
        update_data.pop("lock_version", None),
        entity_name="Project",
    )

    if "company_id" in update_data and update_data["company_id"] is not None:
        update_data["company_id"] = require_company_scope(current_user, update_data["company_id"])
        ensure_company_exists(db.query(Company), update_data["company_id"])
    if "code" in update_data:
        _ensure_unique_code(db, update_data["code"], exclude_project_id=project_id)

    for field, value in update_data.items():
        setattr(project, field, value)

    flush_with_conflict_handling(db, entity_name="Project")
    commit_with_conflict_handling(db, entity_name="Project")
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int, current_user: User) -> None:
    project = get_project_or_404(db, project_id, current_user=current_user)
    dependencies: list[str] = []
    dependency_checks = (
        (
            "active_contracts",
            db.query(Contract.id).filter(
                Contract.project_id == project.id,
                Contract.is_deleted.is_(False),
                Contract.status.in_(["draft", "active", "on_hold"]),
            ),
        ),
        ("materials", db.query(Material.id).filter(Material.project_id == project.id)),
        (
            "material_requisitions",
            db.query(MaterialRequisition.id).filter(MaterialRequisition.project_id == project.id),
        ),
        (
            "material_receipts",
            db.query(MaterialReceipt.id).filter(MaterialReceipt.project_id == project.id),
        ),
        ("material_issues", db.query(MaterialIssue.id).filter(MaterialIssue.project_id == project.id)),
        (
            "material_stock_adjustments",
            db.query(MaterialStockAdjustment.id).filter(
                MaterialStockAdjustment.project_id == project.id
            ),
        ),
        (
            "inventory_transactions",
            db.query(InventoryTransaction.id).filter(InventoryTransaction.project_id == project.id),
        ),
        ("labour_attendances", db.query(LabourAttendance.id).filter(LabourAttendance.project_id == project.id)),
        ("labour_bills", db.query(LabourBill.id).filter(LabourBill.project_id == project.id)),
        (
            "labour_advances",
            db.query(LabourAdvance.id).filter(LabourAdvance.project_id == project.id),
        ),
        (
            "labour_productivities",
            db.query(LabourProductivity.id).filter(LabourProductivity.project_id == project.id),
        ),
    )
    for label, query in dependency_checks:
        if query.first():
            dependencies.append(label)
    if dependencies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Project cannot be deleted because it is referenced by: "
                + ", ".join(dependencies)
            ),
        )

    project.is_deleted = True
    project.deleted_at = datetime.now(timezone.utc)
    flush_with_conflict_handling(db, entity_name="Project")
    commit_with_conflict_handling(db, entity_name="Project")
