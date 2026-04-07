"""merge custom material with contract work order

Revision ID: b2e8fa5ae2dd
Revises: add_custom_material_to_req, b8f3d2a4c1e9
Create Date: 2026-04-06 20:10:58.155794
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'b2e8fa5ae2dd'
down_revision: Union[str, None] = ('add_custom_material_to_req', 'b8f3d2a4c1e9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
