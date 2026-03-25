"""Document metadata and entity linkage model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="contract | measurement | ra_bill | payment",
    )
    entity_id = Column(Integer, nullable=False, index=True)
    storage_key = Column(String(36), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    document_type = Column(String(100), nullable=True)
    current_version_number = Column(Integer, nullable=False, default=1)
    latest_file_name = Column(String(255), nullable=False)
    latest_file_path = Column(String(500), nullable=False)
    latest_mime_type = Column(String(150), nullable=True)
    latest_file_size = Column(Integer, nullable=True)
    remarks = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number.asc()",
    )
