"""Work-done schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class WorkDoneOut(BaseModel):
    id: int
    contract_id: int
    measurement_id: int
    measurement_item_id: int
    boq_item_id: int
    recorded_date: date
    previous_quantity: float
    current_quantity: float
    cumulative_quantity: float
    rate: float
    amount: float
    remarks: Optional[str]
    approved_by: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}
