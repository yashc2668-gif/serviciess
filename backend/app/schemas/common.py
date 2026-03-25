"""Shared schema types."""

from datetime import datetime

from pydantic import BaseModel


class ORMModel(BaseModel):
    model_config = {"from_attributes": True}


class TimestampedSchema(ORMModel):
    created_at: datetime
