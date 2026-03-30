"""Labour attendance item model."""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class LabourAttendanceItem(Base):
    __tablename__ = "labour_attendance_items"
    __table_args__ = (
        UniqueConstraint(
            "attendance_id",
            "labour_id",
            name="uq_labour_attendance_items_attendance_labour",
        ),
        CheckConstraint(
            "attendance_status IN ('present', 'absent', 'half_day', 'leave')",
            name="ck_labour_attendance_items_status_valid",
        ),
        CheckConstraint(
            "present_days >= 0",
            name="ck_labour_attendance_items_present_days_nonnegative",
        ),
        CheckConstraint(
            "overtime_hours >= 0",
            name="ck_labour_attendance_items_overtime_hours_nonnegative",
        ),
        CheckConstraint(
            "wage_rate >= 0",
            name="ck_labour_attendance_items_wage_rate_nonnegative",
        ),
        CheckConstraint(
            "line_amount >= 0",
            name="ck_labour_attendance_items_line_amount_nonnegative",
        ),
        CheckConstraint(
            "attendance_status NOT IN ('absent', 'leave') OR present_days = 0",
            name="ck_labour_attendance_items_absent_leave_present_days_zero",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    attendance_id = Column(
        Integer,
        ForeignKey("labour_attendances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    labour_id = Column(Integer, ForeignKey("labours.id"), nullable=False, index=True)
    attendance_status = Column(String(20), nullable=False, default="present")
    present_days = Column(Numeric(8, 2), nullable=False, default=0)
    overtime_hours = Column(Numeric(8, 2), nullable=False, default=0)
    wage_rate = Column(Numeric(14, 2), nullable=False, default=0)
    line_amount = Column(Numeric(18, 2), nullable=False, default=0)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    attendance = relationship("LabourAttendance", back_populates="items")
    labour = relationship("Labour", backref="attendance_items")
