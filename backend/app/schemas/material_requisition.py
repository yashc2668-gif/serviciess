"""Material requisition schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MaterialRequisitionItemCreate(BaseModel):
    material_id: int = Field(..., ge=1)
    requested_qty: float = Field(..., gt=0)
    approved_qty: float = Field(default=0, ge=0)
    issued_qty: float = Field(default=0, ge=0)


class MaterialRequisitionItemUpdate(BaseModel):
    id: int = Field(..., ge=1)
    requested_qty: Optional[float] = Field(default=None, gt=0)
    approved_qty: Optional[float] = Field(default=None, ge=0)
    issued_qty: Optional[float] = Field(default=None, ge=0)


class MaterialRequisitionCreate(BaseModel):
    requisition_no: str = Field(..., min_length=1, max_length=100)
    project_id: int = Field(..., ge=1)
    contract_id: Optional[int] = Field(default=None, ge=1)
    requested_by: Optional[int] = Field(default=None, ge=1)
    status: str = Field(default="draft", max_length=30)
    remarks: Optional[str] = None
    items: list[MaterialRequisitionItemCreate] = Field(..., min_length=1)


class MaterialRequisitionUpdate(BaseModel):
    requisition_no: Optional[str] = Field(default=None, min_length=1, max_length=100)
    contract_id: Optional[int] = Field(default=None, ge=1)
    status: Optional[str] = Field(default=None, max_length=30)
    remarks: Optional[str] = None
    items: Optional[list[MaterialRequisitionItemUpdate]] = None


class MaterialRequisitionTransitionRequest(BaseModel):
    remarks: Optional[str] = Field(default=None, max_length=1000)


class MaterialRequisitionApproveRequest(MaterialRequisitionTransitionRequest):
    items: Optional[list[MaterialRequisitionItemUpdate]] = None


class MaterialRequisitionItemOut(BaseModel):
    id: int
    material_id: int
    requested_qty: float
    approved_qty: float
    issued_qty: float
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class MaterialRequisitionOut(BaseModel):
    id: int
    requisition_no: str
    project_id: int
    contract_id: Optional[int]
    requested_by: int
    status: str
    remarks: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    items: list[MaterialRequisitionItemOut]

    model_config = {"from_attributes": True}
