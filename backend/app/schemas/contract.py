"""Contract schemas."""

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.boq import BOQItemOut
from app.schemas.vendor import VendorOut


class ContractRevisionOut(BaseModel):
    id: int
    revision_no: str
    revised_value: float
    effective_date: Optional[date]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ContractCreate(BaseModel):
    project_id: int
    contract_type: Literal["client_contract", "vendor_contract"] = "vendor_contract"
    client_name: Optional[str] = Field(default=None, max_length=255)
    vendor_id: Optional[int] = None
    contract_no: str = Field(..., min_length=2, max_length=100)
    title: str = Field(..., min_length=2, max_length=255)
    scope_of_work: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    original_value: float = 0
    revised_value: float = 0
    retention_percentage: float = 0
    status: str = "active"


class ContractUpdate(BaseModel):
    lock_version: Optional[int] = Field(default=None, ge=1)
    contract_type: Optional[Literal["client_contract", "vendor_contract"]] = None
    client_name: Optional[str] = Field(default=None, max_length=255)
    vendor_id: Optional[int] = None
    contract_no: Optional[str] = Field(default=None, min_length=2, max_length=100)
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    scope_of_work: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    original_value: Optional[float] = None
    revised_value: Optional[float] = None
    retention_percentage: Optional[float] = None
    status: Optional[str] = None


class ContractWorkOrderDraft(BaseModel):
    issuer_name: str = Field(..., min_length=2, max_length=255)
    issuer_address: Optional[str] = None
    issuer_gst_number: Optional[str] = Field(default=None, max_length=20)
    issuer_contact: Optional[str] = Field(default=None, max_length=255)
    recipient_label: str = Field(..., min_length=2, max_length=40)
    recipient_name: str = Field(..., min_length=2, max_length=255)
    recipient_address: Optional[str] = None
    work_order_no: str = Field(..., min_length=2, max_length=100)
    work_order_date: Optional[date] = None
    project_name: str = Field(..., min_length=2, max_length=300)
    project_location: Optional[str] = Field(default=None, max_length=300)
    title: str = Field(..., min_length=2, max_length=255)
    subject: Optional[str] = Field(default=None, max_length=255)
    scope_of_work: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    original_value: Optional[float] = Field(default=None, ge=0)
    revised_value: Optional[float] = Field(default=None, ge=0)
    retention_percentage: Optional[float] = Field(default=None, ge=0)
    payment_terms: Optional[str] = None
    special_conditions: Optional[str] = None
    signatory_name: Optional[str] = Field(default=None, max_length=255)
    signatory_designation: Optional[str] = Field(default=None, max_length=255)


class ContractWorkOrderPDFRequest(ContractWorkOrderDraft):
    pass


class ContractWorkOrderDraftUpdate(BaseModel):
    work_order_draft: ContractWorkOrderDraft


class ContractOut(BaseModel):
    id: int
    project_id: int
    contract_type: Literal["client_contract", "vendor_contract"]
    client_name: Optional[str]
    vendor_id: int | None
    contract_no: str
    title: str
    scope_of_work: Optional[str]
    work_order_draft: ContractWorkOrderDraft | dict[str, Any] | None = None
    start_date: Optional[date]
    end_date: Optional[date]
    original_value: float
    revised_value: float
    retention_percentage: float
    status: str
    lock_version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ContractDetailOut(ContractOut):
    vendor: VendorOut | None = None
    revisions: list[ContractRevisionOut] = []
    boq_items: list[BOQItemOut] = []
