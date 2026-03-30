"""Labour attendance or muster model."""

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class LabourAttendance(Base):
    __tablename__ = "labour_attendances"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'cancelled')",
            name="ck_labour_attendances_status_valid",
        ),
        CheckConstraint("total_wage >= 0", name="ck_labour_attendances_total_wage_nonnegative"),
    )

    id = Column(Integer, primary_key=True, index=True)
    muster_no = Column(String(100), nullable=False, unique=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    contractor_id = Column(
        Integer,
        ForeignKey("labour_contractors.id"),
        nullable=True,
        index=True,
    )
    date = Column(Date, nullable=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Backward-compatible fields retained for existing integrations.
    attendance_date = Column(Date, nullable=False, index=True)
    marked_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(
        String(30),
        nullable=False,
        default="draft",
        index=True,
        comment="draft | submitted | approved | cancelled",
    )
    remarks = Column(Text, nullable=True)
    total_wage = Column(Numeric(18, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lock_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": lock_version}

    project = relationship("Project", backref="labour_attendances")
    contractor = relationship("LabourContractor", backref="labour_attendances")
    creator = relationship("User", foreign_keys=[created_by], backref="created_labour_attendances")
    marker = relationship("User", foreign_keys=[marked_by], backref="labour_attendances")
    items = relationship(
        "LabourAttendanceItem",
        back_populates="attendance",
        cascade="all, delete-orphan",
        order_by="LabourAttendanceItem.id.asc()",
    )
