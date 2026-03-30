"""Inventory schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import TimestampedSchema


class InventoryItemCreate(BaseModel):
    name: str


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None


class InventoryItemOut(TimestampedSchema):
    id: int
    name: str


class InventoryTransactionOut(BaseModel):
    id: int
    material_id: int
    project_id: Optional[int]
    transaction_type: str
    qty_in: float
    qty_out: float
    balance_after: float
    reference_type: Optional[str]
    reference_id: Optional[int]
    transaction_date: date
    remarks: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
