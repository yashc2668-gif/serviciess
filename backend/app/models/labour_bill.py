"""Labour bill model."""

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class LabourBill(Base):
    __tablename__ = "labour_bills"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'paid', 'cancelled')",
            name="ck_labour_bills_status_valid",
        ),
        CheckConstraint("period_end >= period_start", name="ck_labour_bills_period_order"),
        CheckConstraint("gross_amount >= 0", name="ck_labour_bills_gross_amount_nonnegative"),
        CheckConstraint("deductions >= 0", name="ck_labour_bills_deductions_nonnegative"),
        CheckConstraint("net_amount >= 0", name="ck_labour_bills_net_amount_nonnegative"),
        CheckConstraint("net_payable >= 0", name="ck_labour_bills_net_payable_nonnegative"),
        CheckConstraint("deductions <= gross_amount", name="ck_labour_bills_deductions_lte_gross"),
    )

    id = Column(Integer, primary_key=True, index=True)
    bill_no = Column(String(100), nullable=False, unique=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True, index=True)
    contractor_id = Column(
        Integer,
        ForeignKey("labour_contractors.id"),
        nullable=False,
        index=True,
    )
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(
        String(30),
        nullable=False,
        default="draft",
        index=True,
        comment="draft | submitted | approved | paid | cancelled",
    )
    gross_amount = Column(Numeric(18, 2), nullable=False, default=0)
    deductions = Column(Numeric(18, 2), nullable=False, default=0)
    net_amount = Column(Numeric(18, 2), nullable=False, default=0)
    net_payable = Column(Numeric(18, 2), nullable=False, default=0)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lock_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": lock_version}

    project = relationship("Project", backref="labour_bills")
    contract = relationship("Contract", backref="labour_bills")
    contractor = relationship("LabourContractor", backref="labour_bills")
    items = relationship(
        "LabourBillItem",
        back_populates="bill",
        cascade="all, delete-orphan",
        order_by="LabourBillItem.id.asc()",
    )
