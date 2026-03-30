"""Contract model."""

from sqlalchemy import (
    Boolean,
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


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)
    contract_no = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    scope_of_work = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    original_value = Column(Numeric(18, 2), nullable=False, default=0)
    revised_value = Column(Numeric(18, 2), nullable=False, default=0)
    retention_percentage = Column(Numeric(5, 2), nullable=False, default=0)
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
