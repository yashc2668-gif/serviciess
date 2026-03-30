"""Labour advance model."""

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class LabourAdvance(Base):
    __tablename__ = "labour_advances"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'closed', 'cancelled')",
            name="ck_labour_advances_status_valid",
        ),
        CheckConstraint("amount > 0", name="ck_labour_advances_amount_positive"),
        CheckConstraint(
            "recovered_amount >= 0",
            name="ck_labour_advances_recovered_amount_nonnegative",
        ),
        CheckConstraint(
            "balance_amount >= 0",
            name="ck_labour_advances_balance_amount_nonnegative",
        ),
        CheckConstraint(
            "recovered_amount <= amount",
            name="ck_labour_advances_recovered_amount_lte_amount",
        ),
        CheckConstraint(
            "balance_amount <= amount",
            name="ck_labour_advances_balance_amount_lte_amount",
        ),
        CheckConstraint(
            "recovered_amount + balance_amount = amount",
            name="ck_labour_advances_balance_matches_amount",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    advance_no = Column(String(100), nullable=False, unique=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    contractor_id = Column(
        Integer,
        ForeignKey("labour_contractors.id"),
        nullable=False,
        index=True,
    )
    advance_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    recovered_amount = Column(Numeric(18, 2), nullable=False, default=0)
    balance_amount = Column(Numeric(18, 2), nullable=False, default=0)
    status = Column(
        String(30),
        nullable=False,
        default="active",
        index=True,
        comment="active | closed | cancelled",
    )
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lock_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": lock_version}

    project = relationship("Project", backref="labour_advances")
    contractor = relationship("LabourContractor", backref="labour_advances")
    recoveries = relationship(
        "LabourAdvanceRecovery",
        back_populates="advance",
        cascade="all, delete-orphan",
        order_by="LabourAdvanceRecovery.id.asc()",
    )
