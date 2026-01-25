"""update user roles to superadmin admin member

Revision ID: 0006
Revises: 0005
Create Date: 2026-01-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    # Update testuser to superadmin
    op.execute("""
        UPDATE users 
        SET role = 'superadmin' 
        WHERE username = 'testuser'
    """)
    
    # Update any 'user' role to 'member'
    op.execute("""
        UPDATE users 
        SET role = 'member' 
        WHERE role = 'user'
    """)


def downgrade():
    # Revert superadmin back to admin
    op.execute("""
        UPDATE users 
        SET role = 'admin' 
        WHERE role = 'superadmin'
    """)
