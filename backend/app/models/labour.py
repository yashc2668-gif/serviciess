"""Labour master model."""

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Labour(Base):
    __tablename__ = "labours"
    __table_args__ = (
        CheckConstraint("daily_rate >= 0", name="ck_labours_daily_rate_nonnegative"),
        CheckConstraint(
            "default_wage_rate >= 0",
            name="ck_labours_default_wage_rate_nonnegative",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    labour_code = Column(String(50), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False, index=True)
    trade = Column(String(100), nullable=True, index=True)
    skill_level = Column(String(50), nullable=True, index=True)
    daily_rate = Column(Numeric(14, 2), nullable=False, default=0)

    # Backward-compatible fields retained for existing integrations.
    skill_type = Column(String(100), nullable=True, index=True)
    default_wage_rate = Column(Numeric(14, 2), nullable=False, default=0)
    unit = Column(String(20), nullable=False, default="day")
    contractor_id = Column(Integer, ForeignKey("labour_contractors.id"), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lock_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": lock_version}

    contractor = relationship("LabourContractor", backref="labours")
