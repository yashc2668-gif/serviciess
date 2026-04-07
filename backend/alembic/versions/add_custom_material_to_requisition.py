"""Add custom material name to requisition items.

Revision ID: add_custom_material_to_req
Revises: 9f4a1a72d6bc
Create Date: 2026-04-06

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_custom_material_to_req'
down_revision: Union[str, None] = '9f4a1a72d6bc'
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # Make material_id nullable
    op.alter_column('material_requisition_items', 'material_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    
    # Add custom_material_name column
    op.add_column('material_requisition_items',
                  sa.Column('custom_material_name', sa.String(255), nullable=True))
    
    # Drop the unique constraint that requires material_id
    op.drop_constraint('uq_material_requisition_items_requisition_material',
                       'material_requisition_items',
                       type_='unique')


def downgrade() -> None:
    # Remove custom_material_name column
    op.drop_column('material_requisition_items', 'custom_material_name')
    
    # Make material_id non-nullable again
    op.alter_column('material_requisition_items', 'material_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # Recreate the unique constraint
    op.create_unique_constraint('uq_material_requisition_items_requisition_material',
                                'material_requisition_items',
                                ['requisition_id', 'material_id'])
