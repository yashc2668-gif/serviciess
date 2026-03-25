"""Project service helpers."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


def list_projects(db: Session, skip: int = 0, limit: int = 100) -> list[Project]:
    return (
        db.query(Project)
        .order_by(Project.created_at.desc(), Project.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_project_or_404(db: Session, project_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def _ensure_company_exists(db: Session, company_id: int) -> None:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )


def _ensure_unique_code(db: Session, code: str | None, exclude_project_id: int | None = None) -> None:
    if not code:
        return
    query = db.query(Project).filter(Project.code == code)
    if exclude_project_id is not None:
        query = query.filter(Project.id != exclude_project_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project code already exists",
        )


def create_project(db: Session, payload: ProjectCreate) -> Project:
    _ensure_company_exists(db, payload.company_id)
    _ensure_unique_code(db, payload.code)

    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project_id: int, payload: ProjectUpdate) -> Project:
    project = get_project_or_404(db, project_id)
    update_data = payload.model_dump(exclude_unset=True)

    if "company_id" in update_data and update_data["company_id"] is not None:
        _ensure_company_exists(db, update_data["company_id"])
    if "code" in update_data:
        _ensure_unique_code(db, update_data["code"], exclude_project_id=project_id)

    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int) -> None:
    project = get_project_or_404(db, project_id)
    db.delete(project)
    db.commit()
