"""Financial archival endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.financial_archive import FinancialArchiveRequest, FinancialArchiveResponse
from app.services.financial_archive_service import archive_financial_records

router = APIRouter(prefix="/financial-archives", tags=["Financial Archives"])


@router.post("/fiscal-close", response_model=FinancialArchiveResponse)
def archive_financial_records_for_fiscal_close(
    payload: FinancialArchiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions("payments:release")),
):
    return archive_financial_records(db, payload, current_user)
