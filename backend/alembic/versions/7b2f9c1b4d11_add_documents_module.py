"""add_documents_module

Revision ID: 7b2f9c1b4d11
Revises: 4f1f3d4f3a2b
Create Date: 2026-03-24 19:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "7b2f9c1b4d11"
down_revision: Union[str, None] = "4f1f3d4f3a2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=True),
        sa.Column("current_version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("latest_file_name", sa.String(length=255), nullable=False),
        sa.Column("latest_file_path", sa.String(length=500), nullable=False),
        sa.Column("latest_mime_type", sa.String(length=150), nullable=True),
        sa.Column("latest_file_size", sa.Integer(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_id"), "documents", ["id"], unique=False)
    op.create_index(op.f("ix_documents_entity_type"), "documents", ["entity_type"], unique=False)
    op.create_index(op.f("ix_documents_entity_id"), "documents", ["entity_id"], unique=False)
    op.create_index(op.f("ix_documents_created_by"), "documents", ["created_by"], unique=False)

    op.create_table(
        "document_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_version_number"),
    )
    op.create_index(
        op.f("ix_document_versions_id"), "document_versions", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_document_versions_document_id"),
        "document_versions",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_versions_uploaded_by"),
        "document_versions",
        ["uploaded_by"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_document_versions_uploaded_by"), table_name="document_versions")
    op.drop_index(op.f("ix_document_versions_document_id"), table_name="document_versions")
    op.drop_index(op.f("ix_document_versions_id"), table_name="document_versions")
    op.drop_table("document_versions")
    op.drop_index(op.f("ix_documents_created_by"), table_name="documents")
    op.drop_index(op.f("ix_documents_entity_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_entity_type"), table_name="documents")
    op.drop_index(op.f("ix_documents_id"), table_name="documents")
    op.drop_table("documents")
