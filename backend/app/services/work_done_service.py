"""Work-done service helpers."""

from sqlalchemy.orm import Session

from app.models.work_done import WorkDoneItem
from app.utils.pagination import PaginationParams, paginate_query


def list_work_done(
    db: Session,
    contract_id: int | None = None,
    measurement_id: int | None = None,
    *,
    pagination: PaginationParams,
) -> dict[str, object]:
    query = db.query(WorkDoneItem)
    if contract_id is not None:
        query = query.filter(WorkDoneItem.contract_id == contract_id)
    if measurement_id is not None:
        query = query.filter(WorkDoneItem.measurement_id == measurement_id)
    return paginate_query(
        query.order_by(WorkDoneItem.recorded_date.asc(), WorkDoneItem.id.asc()),
        pagination=pagination,
    )
