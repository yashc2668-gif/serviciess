"""Work-done endpoints."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions
from app.db.session import get_db
from app.models.user import User
from app.schemas.work_done import WorkDoneOut
from app.services.work_done_service import list_work_done

router = APIRouter(prefix="/work-done", tags=["Work Done"])


@router.get("/", response_model=List[WorkDoneOut])
def list_all_work_done(
    contract_id: int | None = None,
    measurement_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions("work_done:read")),
):
    return list_work_done(db, contract_id=contract_id, measurement_id=measurement_id)
