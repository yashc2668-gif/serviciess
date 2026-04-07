"""Bar bending schedule endpoints."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.schemas.bbs import BBSCreate, BBSOut, BBSUpdate
from app.schemas.common import PaginatedResponse
from app.services.bbs_service import (
    create_bbs_entry,
    delete_bbs_entry,
    get_bbs_or_404,
    list_bbs_entries,
    update_bbs_entry,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/bbs", tags=["BBS"])


@router.post("/", response_model=BBSOut, status_code=201)
def create_new_bbs_entry(
    payload: BBSCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_permissions("bbs:create")),
):
    return create_bbs_entry(db, payload)


@router.get("/", response_model=PaginatedResponse[BBSOut])
def list_all_bbs_entries(
    project_id: int | None = None,
    contract_id: int | None = None,
    drawing_no: str | None = None,
    search: str | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    _: object = Depends(require_permissions("bbs:read")),
):
    return list_bbs_entries(
        db,
        pagination=pagination,
        project_id=project_id,
        contract_id=contract_id,
        drawing_no=drawing_no,
        search=search,
    )


@router.get("/{bbs_id}", response_model=BBSOut)
def get_single_bbs_entry(
    bbs_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_permissions("bbs:read")),
):
    return get_bbs_or_404(db, bbs_id)


@router.put("/{bbs_id}", response_model=BBSOut)
def update_existing_bbs_entry(
    bbs_id: int,
    payload: BBSUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_permissions("bbs:update")),
):
    return update_bbs_entry(db, bbs_id, payload)


@router.delete("/{bbs_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_bbs_entry(
    bbs_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_permissions("bbs:update")),
):
    delete_bbs_entry(db, bbs_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
