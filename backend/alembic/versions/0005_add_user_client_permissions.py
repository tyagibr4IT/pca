"""add user client permissions table

Revision ID: 0005
Revises: 0004
Create Date: 2026-01-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_client_permissions table
    op.create_table('user_client_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('permission', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['tenants.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_client_permissions_id', 'user_client_permissions', ['id'], unique=False)
    op.create_index('ix_user_client_permissions_user_id', 'user_client_permissions', ['user_id'], unique=False)
    op.create_index('ix_user_client_permissions_client_id', 'user_client_permissions', ['client_id'], unique=False)
    op.create_index('ix_user_client_unique', 'user_client_permissions', ['user_id', 'client_id'], unique=True)
    
    # Add status column to users table for active/inactive functionality
    op.add_column('users', sa.Column('status', sa.String(), nullable=True))
    op.execute("UPDATE users SET status = 'active' WHERE status IS NULL")


def downgrade():
    op.drop_index('ix_user_client_unique', table_name='user_client_permissions')
    op.drop_index('ix_user_client_permissions_client_id', table_name='user_client_permissions')
    op.drop_index('ix_user_client_permissions_user_id', table_name='user_client_permissions')
    op.drop_index('ix_user_client_permissions_id', table_name='user_client_permissions')
    op.drop_table('user_client_permissions')
    op.drop_column('users', 'status')
