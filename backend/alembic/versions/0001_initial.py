"""initial

Revision ID: 0001
Revises: 
Create Date: 2025-11-15

"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('tenants',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'))
    )
    op.create_table('users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('username', sa.String(), nullable=False, unique=True),
        sa.Column('email', sa.String(), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=False, server_default='member'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'))
    )
    op.create_table('current_metrics', 
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', sa.Integer),
        sa.Column('provider', sa.String()),
        sa.Column('resource_type', sa.String()),
        sa.Column('resource_id', sa.String()),
        sa.Column('data', sa.JSON()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'))
    )
    op.create_table('metric_snapshots',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', sa.Integer),
        sa.Column('provider', sa.String()),
        sa.Column('snapshot_time', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('data', sa.JSON())
    )

def downgrade():
    op.drop_table('metric_snapshots')
    op.drop_table('current_metrics')
    op.drop_table('users')
    op.drop_table('tenants')