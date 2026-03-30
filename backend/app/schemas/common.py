"""Shared schema types."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field


class ORMModel(BaseModel):
    model_config = {"from_attributes": True}


class TimestampedSchema(ORMModel):
    created_at: datetime


ItemT = TypeVar("ItemT")


class PaginatedResponse(BaseModel, Generic[ItemT]):
    items: list[ItemT] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=1, ge=1)
