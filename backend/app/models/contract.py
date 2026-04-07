"""Contract model."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True, index=True)
    # Work Order Type: "incoming" (Client → Marco) | "outgoing" (Marco → Subcontractor)
    wo_type = Column(
        String(20),
        nullable=False,
        default="outgoing",
        comment="incoming | outgoing",
    )
    
    # Work Order Number (unique identifier)
    wo_number = Column(String(100), nullable=True, unique=True, index=True)
    
    # INCOMING WO Fields (Client → Marco)
    client_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    client_name = Column(String(255), nullable=True)
    client_po_number = Column(String(100), nullable=True)
    client_payment_terms = Column(String(255), nullable=True)
    
    # OUTGOING WO Fields (Marco → Subcontractor)
    contractor_category = Column(String(50), nullable=True)  # civil, electrical, plumbing
    work_scope_summary = Column(Text, nullable=True)
    contract_no = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    scope_of_work = Column(Text, nullable=True)
    work_order_draft = Column(JSON, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    # Financial Fields
    original_value = Column(Numeric(18, 2), nullable=False, default=0)
    revised_value = Column(Numeric(18, 2), nullable=False, default=0)
    retention_percentage = Column(Numeric(5, 2), nullable=False, default=0)
    advance_percentage = Column(Numeric(5, 2), nullable=False, default=0)
    security_deposit = Column(Numeric(18, 2), nullable=False, default=0)
    billing_cycle = Column(String(50), nullable=False, default="monthly")  # monthly | fortnightly | milestone
    # Approval Workflow
    approval_status = Column(
        String(20),
        nullable=False,
        default="draft",
        comment="draft | pending | approved | rejected",
    )
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Legacy status (for backward compatibility)
    status = Column(
        String(30),
        nullable=False,
        default="active",
        comment="draft | active | completed | terminated | on_hold",
    )
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lock_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": lock_version}

    project = relationship("Project", back_populates="contracts")
    vendor = relationship("Vendor", back_populates="contracts")
    client = relationship("Company", foreign_keys=[client_id])
    approver = relationship("User", foreign_keys=[approved_by])
    revisions = relationship(
        "ContractRevision",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractRevision.id.desc()",
    )
    boq_items = relationship(
        "BOQItem",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="BOQItem.id.asc()",
    )
    bbs_entries = relationship(
        "BarBendingSchedule",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="BarBendingSchedule.id.desc()",
    )
    measurements = relationship(
        "Measurement",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="Measurement.id.desc()",
    )
    work_done_entries = relationship(
        "WorkDoneItem",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="WorkDoneItem.id.asc()",
    )
    ra_bills = relationship(
        "RABill",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="RABill.bill_no.asc(), RABill.id.asc()",
    )
    secured_advances = relationship(
        "SecuredAdvance",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="SecuredAdvance.id.asc()",
    )
    payments = relationship(
        "Payment",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="Payment.id.asc()",
    )
