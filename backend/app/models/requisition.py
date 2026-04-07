"""
Material Requisition Model

Workflow:
- DRAFT: Engineer creates requisition
- SUBMITTED: Sent to manager for approval
- APPROVED: Manager approved, ready for store
- ISSUED: Store issued materials
- PARTIAL: Partially issued
- REJECTED: Manager rejected
"""

from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class RequisitionStatus(str, PyEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    ISSUED = "issued"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class RequisitionPriority(str, PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Requisition(Base):
    __tablename__ = "requisitions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Requisition Number (auto-generated)
    req_no = Column(String(50), unique=True, nullable=False, index=True)
    
    # Project & Contract Reference
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True, index=True)
    
    # Requester Info
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    requested_date = Column(Date, nullable=False)
    required_date = Column(Date, nullable=False)
    
    # Status & Priority
    status = Column(
        String(20),
        nullable=False,
        default=RequisitionStatus.DRAFT.value,
    )
    priority = Column(
        String(20),
        nullable=False,
        default=RequisitionPriority.NORMAL.value,
    )
    
    # Approval Workflow
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_date = Column(DateTime(timezone=True), nullable=True)
    approval_remarks = Column(Text, nullable=True)
    
    # Issue Workflow
    issued_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    issued_date = Column(DateTime(timezone=True), nullable=True)
    issue_remarks = Column(Text, nullable=True)
    
    # Purpose/Delivery
    purpose = Column(Text, nullable=True)
    delivery_location = Column(String(255), nullable=True)
    
    # Totals
    total_items = Column(Integer, nullable=False, default=0)
    total_amount = Column(Numeric(18, 2), nullable=False, default=0)
    
    # Soft Delete
    is_deleted = Column(String(1), nullable=False, default="N")
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="requisitions")
    contract = relationship("Contract", back_populates="requisitions")
    requester = relationship("User", foreign_keys=[requested_by], back_populates="requisitions_created")
    approver = relationship("User", foreign_keys=[approved_by])
    issuer = relationship("User", foreign_keys=[issued_by])
    items = relationship(
        "RequisitionItem",
        back_populates="requisition",
        cascade="all, delete-orphan",
        order_by="RequisitionItem.id",
    )


class RequisitionItem(Base):
    __tablename__ = "requisition_items"

    id = Column(Integer, primary_key=True, index=True)
    
    requisition_id = Column(Integer, ForeignKey("requisitions.id"), nullable=False, index=True)
    
    # Material Reference
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=True, index=True)
    
    # Item Details
    item_code = Column(String(50), nullable=True)
    item_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    unit = Column(String(50), nullable=False)
    
    # Quantities
    requested_qty = Column(Numeric(15, 3), nullable=False)
    approved_qty = Column(Numeric(15, 3), nullable=True)
    issued_qty = Column(Numeric(15, 3), nullable=True, default=0)
    
    # Rates & Amounts
    estimated_rate = Column(Numeric(15, 2), nullable=True)
    approved_rate = Column(Numeric(15, 2), nullable=True)
    amount = Column(Numeric(15, 2), nullable=True)
    
    # Remarks
    remarks = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    requisition = relationship("Requisition", back_populates="items")
    material = relationship("Material")
