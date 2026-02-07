"""Add user_permissions table

Revision ID: 0008_user_permissions
Revises: 0007_add_rbac
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_permissions table for user-specific permission overrides
    op.create_table(
        'user_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create unique index on user_id and permission_id
    op.create_index('ix_user_permission_unique', 'user_permissions', ['user_id', 'permission_id'], unique=True)
    op.create_index('ix_user_permissions_user_id', 'user_permissions', ['user_id'])


def downgrade():
    op.drop_index('ix_user_permissions_user_id', table_name='user_permissions')
    op.drop_index('ix_user_permission_unique', table_name='user_permissions')
    op.drop_table('user_permissions')
