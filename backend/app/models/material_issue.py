"""Material issue model."""

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class MaterialIssue(Base):
    __tablename__ = "material_issues"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'issued', 'cancelled')",
            name="ck_material_issues_status_valid",
        ),
        CheckConstraint("total_amount >= 0", name="ck_material_issues_total_amount_nonnegative"),
    )

    id = Column(Integer, primary_key=True, index=True)
    issue_no = Column(String(100), nullable=False, unique=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True, index=True)
    issued_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    issue_date = Column(Date, nullable=False, index=True)
    status = Column(
        String(30),
        nullable=False,
        default="issued",
        index=True,
        comment="draft | issued | cancelled",
    )
    site_name = Column(String(255), nullable=True)
    activity_name = Column(String(255), nullable=True)
    remarks = Column(Text, nullable=True)
    total_amount = Column(Numeric(18, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lock_version = Column(Integer, nullable=False, default=1)
    __mapper_args__ = {"version_id_col": lock_version}

    project = relationship("Project", backref="material_issues")
    contract = relationship("Contract", backref="material_issues")
    issuer = relationship("User", backref="material_issues")
    items = relationship(
        "MaterialIssueItem",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="MaterialIssueItem.id.asc()",
    )
