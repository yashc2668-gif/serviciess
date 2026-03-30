"""Material stock adjustment endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.material_stock_adjustment import (
    MaterialStockAdjustmentCreate,
    MaterialStockAdjustmentOut,
    MaterialStockAdjustmentUpdate,
)
from app.services.material_stock_adjustment_service import (
    create_material_stock_adjustment,
    get_material_stock_adjustment_or_404,
    list_material_stock_adjustments,
    update_material_stock_adjustment,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(
    prefix="/material-stock-adjustments",
    tags=["Material Stock Adjustments"],
)


@router.get("/", response_model=PaginatedResponse[MaterialStockAdjustmentOut])
def list_all_material_stock_adjustments(
    project_id: int | None = None,
    status: str | None = None,
    adjusted_by: int | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("material_stock_adjustments:read")),
):
    return list_material_stock_adjustments(
        db,
        current_user=current_user,
        pagination=pagination,
        project_id=project_id,
        status_filter=status,
        adjusted_by=adjusted_by,
    )


@router.post("/", response_model=MaterialStockAdjustmentOut, status_code=201)
def create_new_material_stock_adjustment(
    payload: MaterialStockAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("stock:adjust")),
):
    return create_material_stock_adjustment(db, payload, current_user)


@router.get("/{adjustment_id}", response_model=MaterialStockAdjustmentOut)
def get_single_material_stock_adjustment(
    adjustment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("material_stock_adjustments:read")),
):
    return get_material_stock_adjustment_or_404(db, adjustment_id)


@router.put("/{adjustment_id}", response_model=MaterialStockAdjustmentOut)
def update_existing_material_stock_adjustment(
    adjustment_id: int,
    payload: MaterialStockAdjustmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("stock:adjust")),
):
    return update_material_stock_adjustment(db, adjustment_id, payload, current_user)
