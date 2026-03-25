"""BOQ item schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BOQItemCreate(BaseModel):
    item_code: Optional[str] = Field(default=None, max_length=50)
    description: str = Field(..., min_length=2)
    unit: str = Field(..., min_length=1, max_length=30)
    quantity: float = 0
    rate: float = 0
    amount: float = 0
    category: Optional[str] = Field(default=None, max_length=100)


class BOQItemUpdate(BaseModel):
    item_code: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    unit: Optional[str] = Field(default=None, max_length=30)
    quantity: Optional[float] = None
    rate: Optional[float] = None
    amount: Optional[float] = None
    category: Optional[str] = Field(default=None, max_length=100)


class BOQItemOut(BaseModel):
    id: int
    contract_id: int
    item_code: Optional[str]
    description: str
    unit: str
    quantity: float
    rate: float
    amount: float
    category: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
