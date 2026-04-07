"""Add RBAC audit logs table

Revision ID: rbac_audit_001
Revises: previous_revision
Create Date: 2026-04-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'rbac_audit_001'
down_revision = '4f1f3d4f3a2b'  # Update this to your latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Create audit_logs table if not exists
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('user_role', sa.String(length=50), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('permission_required', sa.String(length=255), nullable=True),
        sa.Column('permission_granted', sa.Boolean(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('endpoint', sa.String(length=500), nullable=True),
        sa.Column('method', sa.String(length=10), nullable=True),
        sa.Column('previous_state', sa.Text(), nullable=True),
        sa.Column('new_state', sa.Text(), nullable=True),
        sa.Column('changes_summary', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_audit_user_time', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_action_time', 'audit_logs', ['action', 'timestamp'])
    op.create_index('idx_audit_timestamp', 'audit_logs', ['timestamp'])


def downgrade():
    op.drop_index('idx_audit_timestamp', table_name='audit_logs')
    op.drop_index('idx_audit_action_time', table_name='audit_logs')
    op.drop_index('idx_audit_resource', table_name='audit_logs')
    op.drop_index('idx_audit_user_time', table_name='audit_logs')
    op.drop_table('audit_logs')
