"""Inventory transaction ledger model."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    event,
    func,
)
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        CheckConstraint("qty_in >= 0", name="ck_inventory_transactions_qty_in_nonnegative"),
        CheckConstraint("qty_out >= 0", name="ck_inventory_transactions_qty_out_nonnegative"),
        CheckConstraint(
            "balance_after >= 0",
            name="ck_inventory_transactions_balance_after_nonnegative",
        ),
        CheckConstraint(
            "qty_in > 0 OR qty_out > 0",
            name="ck_inventory_transactions_has_quantity_movement",
        ),
        CheckConstraint(
            "NOT (qty_in > 0 AND qty_out > 0)",
            name="ck_inventory_transactions_single_direction",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    transaction_type = Column(String(50), nullable=False, index=True)
    qty_in = Column(Numeric(14, 3), nullable=False, default=0)
    qty_out = Column(Numeric(14, 3), nullable=False, default=0)
    balance_after = Column(Numeric(14, 3), nullable=False, default=0)
    reference_type = Column(String(50), nullable=True, index=True)
    reference_id = Column(Integer, nullable=True, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    material = relationship("Material", backref="inventory_transactions")
    project = relationship("Project", backref="inventory_transactions")


def _raise_append_only_error(_: object, __: object, ___: InventoryTransaction) -> None:
    raise InvalidRequestError("inventory_transactions is append-only and cannot be changed")


event.listens_for(InventoryTransaction, "before_update")(_raise_append_only_error)
event.listens_for(InventoryTransaction, "before_delete")(_raise_append_only_error)
