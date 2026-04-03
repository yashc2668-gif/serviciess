"""Document schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, TimestampedSchema

DocumentEntityType = Literal[
    "contract",
    "measurement",
    "ra_bill",
    "payment",
    "vendor",
    "company",
    "labour_attendance",
    "labour_bill",
    "labour_advance",
    "site_expense",
]


class DocumentCreate(BaseModel):
    entity_type: DocumentEntityType
    entity_id: int = Field(..., gt=0)
    title: str = Field(..., min_length=2, max_length=255)
    document_type: str | None = Field(default=None, max_length=100)
    file_name: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1, max_length=500)
    mime_type: str | None = Field(default=None, max_length=150)
    file_size: int | None = Field(default=None, ge=0)
    remarks: str | None = None


class DocumentVersionCreate(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1, max_length=500)
    mime_type: str | None = Field(default=None, max_length=150)
    file_size: int | None = Field(default=None, ge=0)
    remarks: str | None = None


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    document_type: str | None = Field(default=None, max_length=100)
    remarks: str | None = None


class DocumentVersionOut(TimestampedSchema):
    id: int
    document_id: int
    version_number: int
    file_name: str
    file_path: str
    mime_type: str | None = None
    file_size: int | None = None
    remarks: str | None = None
    uploaded_by: int | None = None


class DocumentOut(ORMModel):
    id: int
    entity_type: DocumentEntityType
    entity_id: int
    storage_key: str
    title: str
    document_type: str | None = None
    current_version_number: int
    latest_file_name: str
    latest_file_path: str
    latest_mime_type: str | None = None
    latest_file_size: int | None = None
    remarks: str | None = None
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime | None = None
    versions: list[DocumentVersionOut] = Field(default_factory=list)
