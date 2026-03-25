"""Project model."""

from sqlalchemy import (
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


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(300), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=True, index=True)
    description = Column(Text, nullable=True)
    client_name = Column(String(255), nullable=True)
    location = Column(String(300), nullable=True)
    original_value = Column(Numeric(18, 2), nullable=False, default=0)
    revised_value = Column(Numeric(18, 2), nullable=False, default=0)
    start_date = Column(Date, nullable=True)
    expected_end_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    status = Column(
        String(30),
        nullable=False,
        default="active",
        comment="active | completed | on_hold | cancelled",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company = relationship("Company", backref="projects")
    contracts = relationship(
        "Contract",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Contract.id.desc()",
    )
