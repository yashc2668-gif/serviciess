"""Financial archival request and response schemas."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class FinancialArchiveRequest(BaseModel):
    fiscal_year_end: date
    include_secured_advances: bool = True


class FinancialArchiveResponse(BaseModel):
    archive_batch_id: str
    fiscal_year_end: date
    archived_at: datetime
    archived_payments: int = Field(default=0, ge=0)
    archived_ra_bills: int = Field(default=0, ge=0)
    archived_secured_advances: int = Field(default=0, ge=0)
