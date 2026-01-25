"""add cloud_metrics_cache table

Revision ID: 0003
Revises: 0002
Create Date: 2026-01-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'cloud_metrics_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('metrics_data', JSON, nullable=False),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cloud_metrics_cache_id', 'cloud_metrics_cache', ['id'])
    op.create_index('ix_cloud_metrics_cache_tenant_id', 'cloud_metrics_cache', ['tenant_id'])
    op.create_index('ix_cloud_metrics_cache_provider', 'cloud_metrics_cache', ['provider'])
    op.create_index('ix_cloud_metrics_cache_fetched_at', 'cloud_metrics_cache', ['fetched_at'])

def downgrade():
    op.drop_index('ix_cloud_metrics_cache_fetched_at', table_name='cloud_metrics_cache')
    op.drop_index('ix_cloud_metrics_cache_provider', table_name='cloud_metrics_cache')
    op.drop_index('ix_cloud_metrics_cache_tenant_id', table_name='cloud_metrics_cache')
    op.drop_index('ix_cloud_metrics_cache_id', table_name='cloud_metrics_cache')
    op.drop_table('cloud_metrics_cache')
