"""upgrade_audit_logs_to_central_layer

Revision ID: 4f1f3d4f3a2b
Revises: e135ebdf735c
Create Date: 2026-03-24 18:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "4f1f3d4f3a2b"
down_revision: Union[str, None] = "e135ebdf735c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_contract_id", table_name="audit_logs")

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.alter_column(
            "entity_name",
            new_column_name="entity_type",
            existing_type=sa.String(length=100),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "actor_user_id",
            new_column_name="performed_by",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "payload",
            new_column_name="after_data",
            existing_type=sa.JSON(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "created_at",
            new_column_name="performed_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=True,
            existing_server_default=sa.text("CURRENT_TIMESTAMP"),
        )
        batch_op.add_column(sa.Column("before_data", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("request_id", sa.String(length=100), nullable=True))
        batch_op.drop_column("contract_id")

    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"], unique=False)
    op.create_index("ix_audit_logs_performed_by", "audit_logs", ["performed_by"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_performed_at", "audit_logs", ["performed_at"], unique=False)
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_performed_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_performed_by", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs")

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.add_column(
            sa.Column("contract_id", sa.Integer(), nullable=True)
        )
        batch_op.drop_column("request_id")
        batch_op.drop_column("before_data")
        batch_op.alter_column(
            "performed_at",
            new_column_name="created_at",
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=True,
            existing_server_default=sa.text("CURRENT_TIMESTAMP"),
        )
        batch_op.alter_column(
            "after_data",
            new_column_name="payload",
            existing_type=sa.JSON(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "performed_by",
            new_column_name="actor_user_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "entity_type",
            new_column_name="entity_name",
            existing_type=sa.String(length=100),
            existing_nullable=False,
        )
        batch_op.create_foreign_key(
            None,
            "contracts",
            ["contract_id"],
            ["id"],
        )

    op.create_index("ix_audit_logs_contract_id", "audit_logs", ["contract_id"], unique=False)
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)
