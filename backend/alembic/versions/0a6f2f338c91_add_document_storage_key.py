"""add document storage key

Revision ID: 0a6f2f338c91
Revises: 7b2f9c1b4d11
Create Date: 2026-03-25 00:00:00.000000
"""

from __future__ import annotations

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0a6f2f338c91"
down_revision = "7b2f9c1b4d11"
branch_labels = None
depends_on = None


documents_table = sa.table(
    "documents",
    sa.column("id", sa.Integer),
    sa.column("storage_key", sa.String(length=36)),
)


def upgrade() -> None:
    is_sqlite = op.get_bind().dialect.name == "sqlite"
    op.add_column("documents", sa.Column("storage_key", sa.String(length=36), nullable=True))

    connection = op.get_bind()
    existing_ids = [
        row.id
        for row in connection.execute(sa.select(documents_table.c.id))
    ]
    for document_id in existing_ids:
        connection.execute(
            documents_table.update()
            .where(documents_table.c.id == document_id)
            .values(storage_key=str(uuid4()))
        )

    if is_sqlite:
        with op.batch_alter_table("documents") as batch_op:
            batch_op.alter_column("storage_key", existing_type=sa.String(length=36), nullable=False)
    else:
        op.alter_column("documents", "storage_key", nullable=False)
    op.create_index(op.f("ix_documents_storage_key"), "documents", ["storage_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_storage_key"), table_name="documents")
    op.drop_column("documents", "storage_key")
