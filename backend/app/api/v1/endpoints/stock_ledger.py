"""Stock ledger endpoints."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.inventory import InventoryTransactionOut
from app.services.inventory_service import (
    get_inventory_transaction_or_404,
    list_inventory_transactions,
)
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter(prefix="/stock-ledger", tags=["Stock Ledger"])


@router.get("", response_model=PaginatedResponse[InventoryTransactionOut])
@router.get("/", response_model=PaginatedResponse[InventoryTransactionOut], include_in_schema=False)
def list_stock_ledger(
    material_id: int | None = None,
    project_id: int | None = None,
    transaction_type: str | None = None,
    reference_type: str | None = None,
    reference_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("stock_ledger:read")),
):
    return list_inventory_transactions(
        db,
        current_user=current_user,
        pagination=pagination,
        material_id=material_id,
        project_id=project_id,
        transaction_type=transaction_type,
        reference_type=reference_type,
        reference_id=reference_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{transaction_id}", response_model=InventoryTransactionOut)
def get_stock_ledger_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("stock_ledger:read")),
):
    return get_inventory_transaction_or_404(db, transaction_id, current_user=current_user)
