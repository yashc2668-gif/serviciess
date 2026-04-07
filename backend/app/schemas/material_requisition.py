"""Material Requisition Schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MaterialRequisitionItemBase(BaseModel):
    material_id: Optional[int] = None
    custom_material_name: Optional[str] = None
    requested_qty: Decimal = Field(gt=0)
    approved_qty: Optional[Decimal] = Field(default=None, ge=0)
    issued_qty: Optional[Decimal] = Field(default=None, ge=0)


class MaterialRequisitionItemCreate(MaterialRequisitionItemBase):
    pass


class MaterialRequisitionItemUpdate(BaseModel):
    material_id: Optional[int] = None
    custom_material_name: Optional[str] = None
    requested_qty: Optional[Decimal] = Field(default=None, gt=0)
    approved_qty: Optional[Decimal] = Field(default=None, ge=0)
    issued_qty: Optional[Decimal] = Field(default=None, ge=0)


class MaterialRequisitionItemOut(MaterialRequisitionItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requisition_id: int
    created_at: datetime
    updated_at: datetime
    # Material details
    material_code: Optional[str] = None
    material_name: Optional[str] = None
    material_unit: Optional[str] = None


class MaterialRequisitionBase(BaseModel):
    project_id: int
    contract_id: Optional[int] = None
    requisition_no: Optional[str] = None
    status: str = "draft"
    remarks: Optional[str] = None


class MaterialRequisitionCreate(BaseModel):
    project_id: int
    contract_id: Optional[int] = None
    remarks: Optional[str] = None
    items: List[MaterialRequisitionItemCreate]


class MaterialRequisitionUpdate(BaseModel):
    project_id: Optional[int] = None
    contract_id: Optional[int] = None
    remarks: Optional[str] = None


class MaterialRequisitionSubmit(BaseModel):
    """Submit requisition for approval."""
    remarks: Optional[str] = None


class MaterialRequisitionApprove(BaseModel):
    """Approve/reject requisition."""
    approved: bool
    remarks: Optional[str] = None
    items: Optional[List[MaterialRequisitionItemUpdate]] = None  # With approved_qty


class MaterialRequisitionIssue(BaseModel):
    """Issue materials from store."""
    remarks: Optional[str] = None
    items: List[MaterialRequisitionItemUpdate]  # With issued_qty


class MaterialRequisitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requisition_no: str
    project_id: int
    contract_id: Optional[int] = None
    requested_by: int
    status: str
    remarks: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Related data
    project_name: Optional[str] = None
    contract_title: Optional[str] = None
    requester_name: Optional[str] = None
    
    # Items
    items: List[MaterialRequisitionItemOut] = []
    
    # Stats
    total_items: int = 0
    total_requested_qty: Decimal = Decimal("0")
    total_approved_qty: Decimal = Decimal("0")
    total_issued_qty: Decimal = Decimal("0")


class MaterialRequisitionListOut(BaseModel):
    """Lightweight list view."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    requisition_no: str
    project_id: int
    contract_id: Optional[int] = None
    requested_by: int
    status: str
    remarks: Optional[str] = None
    created_at: datetime
    
    # Related names
    project_name: Optional[str] = None
    contract_title: Optional[str] = None
    requester_name: Optional[str] = None
    
    # Item count
    item_count: int = 0
