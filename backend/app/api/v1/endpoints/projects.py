"""Project endpoints."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.project_service import (
    create_project,
    delete_project,
    get_project_or_404,
    list_projects,
    list_projects_for_export,
    update_project,
)
from app.utils.csv_export import build_csv_response
from app.utils.pagination import PaginationParams, get_pagination_params
from app.utils.sorting import SortParams, get_sort_params

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=PaginatedResponse[ProjectOut])
def list_all_projects(
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("projects:read")),
):
    return list_projects(
        db,
        current_user=current_user,
        pagination=pagination,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )


@router.get("/export")
def export_projects(
    company_id: int | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    sorting: SortParams = Depends(get_sort_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("projects:read")),
):
    projects = list_projects_for_export(
        db,
        current_user=current_user,
        company_id=company_id,
        status_filter=status_filter,
        search=search,
        sort_by=sorting.sort_by,
        sort_dir=sorting.sort_dir,
    )
    return build_csv_response(
        filename="projects-export",
        headers=[
            "Project",
            "Code",
            "Company",
            "Client",
            "Location",
            "Original Value",
            "Revised Value",
            "Start Date",
            "Expected End Date",
            "Status",
        ],
        rows=[
            [
                project.name,
                project.code,
                project.company.name if project.company else None,
                project.client_name,
                project.location,
                project.original_value,
                project.revised_value,
                project.start_date,
                project.expected_end_date,
                project.status,
            ]
            for project in projects
        ],
    )


@router.post("/", response_model=ProjectOut, status_code=201)
def create_new_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("projects:create")),
):
    return create_project(db, payload, current_user)


@router.get("/{project_id}", response_model=ProjectOut)
def get_single_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("projects:read")),
):
    return get_project_or_404(db, project_id, current_user=current_user)


@router.put("/{project_id}", response_model=ProjectOut)
def update_existing_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("projects:update")),
):
    return update_project(db, project_id, payload, current_user)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("projects:update")),
):
    delete_project(db, project_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
