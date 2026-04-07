"""merge_heads

Revision ID: d5a661c581d6
Revises: rbac_audit_001, b2e8fa5ae2dd
Create Date: 2026-04-07 15:19:59.103548
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'd5a661c581d6'
down_revision: Union[str, None] = ('rbac_audit_001', 'b2e8fa5ae2dd')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
