"""Material issue endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.material_issue import MaterialIssueCreate, MaterialIssueOut, MaterialIssueUpdate
from app.services.material_issue_service import (
    create_material_issue,
    get_material_issue_or_404,
    list_material_issues,
    update_material_issue,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/material-issues", tags=["Material Issues"])


@router.get("", response_model=PaginatedResponse[MaterialIssueOut])
@router.get("/", response_model=PaginatedResponse[MaterialIssueOut], include_in_schema=False)
def list_all_material_issues(
    project_id: int | None = None,
    contract_id: int | None = None,
    status: str | None = None,
    issued_by: int | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("material_issues:read")),
):
    return list_material_issues(
        db,
        current_user=current_user,
        pagination=pagination,
        project_id=project_id,
        contract_id=contract_id,
        status_filter=status,
        issued_by=issued_by,
    )


@router.post("", response_model=MaterialIssueOut, status_code=201)
@router.post(
    "/",
    response_model=MaterialIssueOut,
    status_code=201,
    include_in_schema=False,
)
def create_new_material_issue(
    payload: MaterialIssueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("stock:issue")),
):
    return create_material_issue(db, payload, current_user)


@router.get("/{issue_id}", response_model=MaterialIssueOut)
def get_single_material_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("material_issues:read")),
):
    return get_material_issue_or_404(db, issue_id)


@router.put("/{issue_id}", response_model=MaterialIssueOut)
def update_existing_material_issue(
    issue_id: int,
    payload: MaterialIssueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("stock:issue")),
):
    return update_material_issue(db, issue_id, payload, current_user)
