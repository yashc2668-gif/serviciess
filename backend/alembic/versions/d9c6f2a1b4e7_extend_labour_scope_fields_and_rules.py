"""extend labour scope fields and rules

Revision ID: d9c6f2a1b4e7
Revises: b13d7e4a9c2f
Create Date: 2026-03-26 12:05:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d9c6f2a1b4e7"
down_revision = "b13d7e4a9c2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("labours", schema=None) as batch_op:
        batch_op.add_column(sa.Column("trade", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("skill_level", sa.String(length=50), nullable=True))
        batch_op.add_column(
            sa.Column(
                "daily_rate",
                sa.Numeric(precision=14, scale=2),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.create_index(op.f("ix_labours_trade"), ["trade"], unique=False)
        batch_op.create_index(op.f("ix_labours_skill_level"), ["skill_level"], unique=False)

    op.execute("UPDATE labours SET trade = skill_type WHERE trade IS NULL")
    op.execute("UPDATE labours SET daily_rate = default_wage_rate")

    with op.batch_alter_table("labour_contractors", schema=None) as batch_op:
        batch_op.add_column(sa.Column("contact_person", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("address", sa.Text(), nullable=True))
    op.execute("UPDATE labour_contractors SET contact_person = gang_name WHERE contact_person IS NULL")

    with op.batch_alter_table("labour_attendances", schema=None) as batch_op:
        batch_op.add_column(sa.Column("contractor_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("created_by", sa.Integer(), nullable=True))
        batch_op.create_index(
            op.f("ix_labour_attendances_contractor_id"),
            ["contractor_id"],
            unique=False,
        )
        batch_op.create_index(op.f("ix_labour_attendances_date"), ["date"], unique=False)
        batch_op.create_index(op.f("ix_labour_attendances_created_by"), ["created_by"], unique=False)
        batch_op.create_foreign_key(
            "fk_labour_attendances_contractor_id",
            "labour_contractors",
            ["contractor_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_labour_attendances_created_by",
            "users",
            ["created_by"],
            ["id"],
        )
    op.execute("UPDATE labour_attendances SET date = attendance_date WHERE date IS NULL")
    op.execute("UPDATE labour_attendances SET created_by = marked_by WHERE created_by IS NULL")

    with op.batch_alter_table("labour_attendance_items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "attendance_status",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'present'"),
            )
        )
        batch_op.add_column(sa.Column("remarks", sa.Text(), nullable=True))

    with op.batch_alter_table("labour_productivities", schema=None) as batch_op:
        batch_op.add_column(sa.Column("contract_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("trade", sa.String(length=100), nullable=True))
        batch_op.add_column(
            sa.Column(
                "quantity_done",
                sa.Numeric(precision=14, scale=3),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "labour_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "productivity_value",
                sa.Numeric(precision=14, scale=3),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
        batch_op.create_index(op.f("ix_labour_productivities_contract_id"), ["contract_id"], unique=False)
        batch_op.create_index(op.f("ix_labour_productivities_date"), ["date"], unique=False)
        batch_op.create_index(op.f("ix_labour_productivities_trade"), ["trade"], unique=False)
        batch_op.create_foreign_key(
            "fk_labour_productivities_contract_id",
            "contracts",
            ["contract_id"],
            ["id"],
        )
    op.execute("UPDATE labour_productivities SET date = productivity_date WHERE date IS NULL")
    op.execute("UPDATE labour_productivities SET trade = activity_name WHERE trade IS NULL")
    op.execute("UPDATE labour_productivities SET quantity_done = quantity")
    op.execute("UPDATE labour_productivities SET labour_count = 1 WHERE labour_count = 0")
    op.execute(
        "UPDATE labour_productivities SET productivity_value = quantity_done / labour_count "
        "WHERE labour_count > 0"
    )

    with op.batch_alter_table("labour_bills", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "net_payable",
                sa.Numeric(precision=18, scale=2),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
    op.execute("UPDATE labour_bills SET net_payable = net_amount")


def downgrade() -> None:
    with op.batch_alter_table("labour_bills", schema=None) as batch_op:
        batch_op.drop_column("net_payable")

    with op.batch_alter_table("labour_productivities", schema=None) as batch_op:
        batch_op.drop_constraint("fk_labour_productivities_contract_id", type_="foreignkey")
        batch_op.drop_index(op.f("ix_labour_productivities_trade"))
        batch_op.drop_index(op.f("ix_labour_productivities_date"))
        batch_op.drop_index(op.f("ix_labour_productivities_contract_id"))
        batch_op.drop_column("productivity_value")
        batch_op.drop_column("labour_count")
        batch_op.drop_column("quantity_done")
        batch_op.drop_column("trade")
        batch_op.drop_column("date")
        batch_op.drop_column("contract_id")

    with op.batch_alter_table("labour_attendance_items", schema=None) as batch_op:
        batch_op.drop_column("remarks")
        batch_op.drop_column("attendance_status")

    with op.batch_alter_table("labour_attendances", schema=None) as batch_op:
        batch_op.drop_constraint("fk_labour_attendances_created_by", type_="foreignkey")
        batch_op.drop_constraint("fk_labour_attendances_contractor_id", type_="foreignkey")
        batch_op.drop_index(op.f("ix_labour_attendances_created_by"))
        batch_op.drop_index(op.f("ix_labour_attendances_date"))
        batch_op.drop_index(op.f("ix_labour_attendances_contractor_id"))
        batch_op.drop_column("created_by")
        batch_op.drop_column("date")
        batch_op.drop_column("contractor_id")

    with op.batch_alter_table("labour_contractors", schema=None) as batch_op:
        batch_op.drop_column("address")
        batch_op.drop_column("contact_person")

    with op.batch_alter_table("labours", schema=None) as batch_op:
        batch_op.drop_index(op.f("ix_labours_skill_level"))
        batch_op.drop_index(op.f("ix_labours_trade"))
        batch_op.drop_column("daily_rate")
        batch_op.drop_column("skill_level")
        batch_op.drop_column("trade")
