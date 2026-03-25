"""Project endpoints."""

from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.project_service import (
    create_project,
    delete_project,
    get_project_or_404,
    list_projects,
    update_project,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=List[ProjectOut])
def list_all_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("projects:read")),
):
    return list_projects(db, skip=skip, limit=limit)


@router.post("/", response_model=ProjectOut, status_code=201)
def create_new_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("projects:create")),
):
    return create_project(db, payload)


@router.get("/{project_id}", response_model=ProjectOut)
def get_single_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("projects:read")),
):
    return get_project_or_404(db, project_id)


@router.put("/{project_id}", response_model=ProjectOut)
def update_existing_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("projects:update")),
):
    return update_project(db, project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("projects:update")),
):
    delete_project(db, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
