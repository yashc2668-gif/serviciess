"""Company model."""

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.db.base_class import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    address = Column(Text, nullable=True)
    gst_number = Column(String(20), nullable=True)
    pan_number = Column(String(15), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    logo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
