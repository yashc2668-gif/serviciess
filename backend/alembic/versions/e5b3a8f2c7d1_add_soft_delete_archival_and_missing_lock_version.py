"""add soft-delete, archival, and missing lock_version columns

Revision ID: e5b3a8f2c7d1
Revises: 2a4e7c9b1d0f
Create Date: 2026-03-29 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e5b3a8f2c7d1"
down_revision = "2a4e7c9b1d0f"
branch_labels = None
depends_on = None


# Tables that gained is_deleted + deleted_at columns.
SOFT_DELETE_TABLES = ("projects", "vendors", "contracts", "labours")

# Tables that gained archival columns.
ARCHIVAL_TABLES = ("ra_bills", "payments", "secured_advances")

# Tables that gained lock_version but were missed in the earlier migration.
LOCK_VERSION_TABLES = ("projects", "vendors", "contracts", "labour_contractors")

# Tables that gained company_id (FK → companies.id) column.
COMPANY_SCOPE_TABLES = ("vendors", "labours", "labour_contractors")


def upgrade() -> None:
    false_default = sa.false()

    # --- soft-delete columns ---
    for table_name in SOFT_DELETE_TABLES:
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=false_default),
            )
            batch_op.add_column(
                sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            )
            batch_op.create_index(f"ix_{table_name}_is_deleted", ["is_deleted"])

    # --- archival columns ---
    for table_name in ARCHIVAL_TABLES:
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=false_default),
            )
            batch_op.add_column(
                sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            )
            batch_op.add_column(
                sa.Column("archived_by", sa.Integer(), nullable=True),
            )
            batch_op.add_column(
                sa.Column("archive_batch_id", sa.String(length=64), nullable=True),
            )
            batch_op.create_index(f"ix_{table_name}_is_archived", ["is_archived"])
            batch_op.create_index(f"ix_{table_name}_archive_batch_id", ["archive_batch_id"])

    # Add FK constraints for archived_by outside batch mode (PostgreSQL).
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        for table_name in ARCHIVAL_TABLES:
            op.create_foreign_key(
                f"fk_{table_name}_archived_by_users",
                table_name,
                "users",
                ["archived_by"],
                ["id"],
            )

    # --- missing lock_version columns ---
    for table_name in LOCK_VERSION_TABLES:
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "lock_version",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("1"),
                ),
            )

    # --- company_id scope columns ---
    for table_name in COMPANY_SCOPE_TABLES:
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("company_id", sa.Integer(), nullable=True),
            )
            batch_op.create_index(f"ix_{table_name}_company_id", ["company_id"])

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        for table_name in COMPANY_SCOPE_TABLES:
            op.create_foreign_key(
                f"fk_{table_name}_company_id_companies",
                table_name,
                "companies",
                ["company_id"],
                ["id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        for table_name in reversed(COMPANY_SCOPE_TABLES):
            op.drop_constraint(f"fk_{table_name}_company_id_companies", table_name, type_="foreignkey")

    for table_name in reversed(COMPANY_SCOPE_TABLES):
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_company_id")
            batch_op.drop_column("company_id")

    for table_name in reversed(LOCK_VERSION_TABLES):
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_column("lock_version")

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        for table_name in reversed(ARCHIVAL_TABLES):
            op.drop_constraint(f"fk_{table_name}_archived_by_users", table_name, type_="foreignkey")

    for table_name in reversed(ARCHIVAL_TABLES):
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_archive_batch_id")
            batch_op.drop_index(f"ix_{table_name}_is_archived")
            batch_op.drop_column("archive_batch_id")
            batch_op.drop_column("archived_by")
            batch_op.drop_column("archived_at")
            batch_op.drop_column("is_archived")

    for table_name in reversed(SOFT_DELETE_TABLES):
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_is_deleted")
            batch_op.drop_column("deleted_at")
            batch_op.drop_column("is_deleted")
