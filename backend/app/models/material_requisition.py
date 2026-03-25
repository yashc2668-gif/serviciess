"""Material requisition model placeholder."""

from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.base_class import Base


class MaterialRequisition(Base):
    __tablename__ = "material_requisitions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False)
    requisition_no = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
