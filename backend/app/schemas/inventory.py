"""Inventory schemas."""

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
