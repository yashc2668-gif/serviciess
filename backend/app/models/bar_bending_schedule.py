"""Bar bending schedule model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class BarBendingSchedule(Base):
    __tablename__ = "bar_bending_schedules"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    drawing_no = Column(String(120), nullable=False, index=True)
    member_location = Column(String(255), nullable=False)
    bar_mark = Column(String(80), nullable=False, index=True)
    dia_mm = Column(Numeric(10, 2), nullable=False, default=0)
    cut_length_mm = Column(Numeric(12, 2), nullable=False, default=0)
    shape_code = Column(String(60), nullable=True)
    nos = Column(Integer, nullable=False, default=0)
    unit_weight = Column(Numeric(12, 3), nullable=False, default=0)
    total_weight = Column(Numeric(14, 3), nullable=False, default=0)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lock_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": lock_version}

    contract = relationship("Contract", back_populates="bbs_entries")
