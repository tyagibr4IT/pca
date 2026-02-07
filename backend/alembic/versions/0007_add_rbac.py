"""add rbac tables and migrate users

Revision ID: 0007
Revises: 0006
Create Date: 2026-02-07 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)
    
    # Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('resource', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_permissions_id'), 'permissions', ['id'], unique=False)
    op.create_index(op.f('ix_permissions_name'), 'permissions', ['name'], unique=True)
    op.create_index(op.f('ix_permissions_resource'), 'permissions', ['resource'], unique=False)
    
    # Create role_permissions association table
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )
    
    # Insert default roles
    roles_table = table('roles',
        column('id', sa.Integer),
        column('name', sa.String),
        column('description', sa.String),
        column('is_system', sa.Boolean),
        column('created_at', sa.DateTime)
    )
    
    op.bulk_insert(roles_table, [
        {'id': 1, 'name': 'superadmin', 'description': 'Super Administrator with full system access', 'is_system': True, 'created_at': datetime.utcnow()},
        {'id': 2, 'name': 'admin', 'description': 'Administrator with management access', 'is_system': True, 'created_at': datetime.utcnow()},
        {'id': 3, 'name': 'member', 'description': 'Member with limited access', 'is_system': True, 'created_at': datetime.utcnow()},
    ])
    
    # Insert all permissions
    permissions_table = table('permissions',
        column('id', sa.Integer),
        column('name', sa.String),
        column('resource', sa.String),
        column('action', sa.String),
        column('description', sa.String),
        column('created_at', sa.DateTime)
    )
    
    permissions = [
        # User permissions
        {'id': 1, 'name': 'users.view', 'resource': 'users', 'action': 'view', 'description': 'View user list and details'},
        {'id': 2, 'name': 'users.create', 'resource': 'users', 'action': 'create', 'description': 'Create new users'},
        {'id': 3, 'name': 'users.edit', 'resource': 'users', 'action': 'edit', 'description': 'Edit user details'},
        {'id': 4, 'name': 'users.delete', 'resource': 'users', 'action': 'delete', 'description': 'Delete users'},
        {'id': 5, 'name': 'users.manage_roles', 'resource': 'users', 'action': 'manage_roles', 'description': 'Assign and change user roles'},
        
        # Client permissions
        {'id': 6, 'name': 'clients.view', 'resource': 'clients', 'action': 'view', 'description': 'View client list and details'},
        {'id': 7, 'name': 'clients.create', 'resource': 'clients', 'action': 'create', 'description': 'Create new clients'},
        {'id': 8, 'name': 'clients.edit', 'resource': 'clients', 'action': 'edit', 'description': 'Edit client details'},
        {'id': 9, 'name': 'clients.delete', 'resource': 'clients', 'action': 'delete', 'description': 'Delete clients'},
        {'id': 10, 'name': 'clients.assign', 'resource': 'clients', 'action': 'assign', 'description': 'Assign clients to users'},
        
        # Metrics permissions
        {'id': 11, 'name': 'metrics.view', 'resource': 'metrics', 'action': 'view', 'description': 'View metrics and dashboards'},
        {'id': 12, 'name': 'metrics.export', 'resource': 'metrics', 'action': 'export', 'description': 'Export metrics data'},
        {'id': 13, 'name': 'metrics.recommendations.view', 'resource': 'metrics', 'action': 'recommendations.view', 'description': 'View cost recommendations'},
        {'id': 14, 'name': 'metrics.recommendations.apply', 'resource': 'metrics', 'action': 'recommendations.apply', 'description': 'Apply recommendations'},
        
        # Chat permissions
        {'id': 15, 'name': 'chat.access', 'resource': 'chat', 'action': 'access', 'description': 'Access AI chat assistant'},
        {'id': 16, 'name': 'chat.history.view', 'resource': 'chat', 'action': 'history.view', 'description': 'View chat history'},
        {'id': 17, 'name': 'chat.history.delete', 'resource': 'chat', 'action': 'history.delete', 'description': 'Delete chat history'},
        
        # System permissions
        {'id': 18, 'name': 'system.settings.view', 'resource': 'system', 'action': 'settings.view', 'description': 'View system settings'},
        {'id': 19, 'name': 'system.settings.edit', 'resource': 'system', 'action': 'settings.edit', 'description': 'Edit system settings'},
        {'id': 20, 'name': 'system.audit_logs.view', 'resource': 'system', 'action': 'audit_logs.view', 'description': 'View audit logs'},
        {'id': 21, 'name': 'system.reports.generate', 'resource': 'system', 'action': 'reports.generate', 'description': 'Generate reports'},
        
        # Resource permissions
        {'id': 22, 'name': 'resources.view', 'resource': 'resources', 'action': 'view', 'description': 'View cloud resources'},
        {'id': 23, 'name': 'resources.manage', 'resource': 'resources', 'action': 'manage', 'description': 'Manage cloud resources'},
        {'id': 24, 'name': 'resources.costs.view', 'resource': 'resources', 'action': 'costs.view', 'description': 'View cost analysis'},
    ]
    
    for perm in permissions:
        perm['created_at'] = datetime.utcnow()
    
    op.bulk_insert(permissions_table, permissions)
    
    # Assign permissions to roles
    role_perms_table = table('role_permissions',
        column('role_id', sa.Integer),
        column('permission_id', sa.Integer),
        column('created_at', sa.DateTime)
    )
    
    # Superadmin - all permissions (1-24)
    superadmin_perms = [{'role_id': 1, 'permission_id': i, 'created_at': datetime.utcnow()} for i in range(1, 25)]
    
    # Admin - all except users.delete, users.manage_roles, system.settings.edit (exclude 4, 5, 19)
    admin_perms = [{'role_id': 2, 'permission_id': i, 'created_at': datetime.utcnow()} 
                   for i in range(1, 25) if i not in [4, 5, 19]]
    
    # Member - view only permissions (1, 6, 11, 13, 15, 16, 22, 24)
    member_perms = [{'role_id': 3, 'permission_id': i, 'created_at': datetime.utcnow()} 
                    for i in [6, 11, 13, 15, 16, 22, 24]]
    
    op.bulk_insert(role_perms_table, superadmin_perms + admin_perms + member_perms)
    
    # Add role_id column to users table
    op.add_column('users', sa.Column('role_id', sa.Integer(), nullable=True))
    
    # Migrate existing role strings to role_ids
    # superadmin -> 1, admin -> 2, member -> 3
    op.execute("""
        UPDATE users SET role_id = 1 WHERE role = 'superadmin';
        UPDATE users SET role_id = 2 WHERE role = 'admin';
        UPDATE users SET role_id = 3 WHERE role = 'member';
        UPDATE users SET role_id = 3 WHERE role_id IS NULL;
    """)
    
    # Make role_id NOT NULL and add foreign key
    op.alter_column('users', 'role_id', nullable=False)
    op.create_foreign_key('fk_users_role_id', 'users', 'roles', ['role_id'], ['id'])
    
    # Drop old role column
    op.drop_column('users', 'role')


def downgrade():
    # Add back role column
    op.add_column('users', sa.Column('role', sa.String(), nullable=True))
    
    # Migrate role_ids back to role strings
    op.execute("""
        UPDATE users SET role = 'superadmin' WHERE role_id = 1;
        UPDATE users SET role = 'admin' WHERE role_id = 2;
        UPDATE users SET role = 'member' WHERE role_id = 3;
    """)
    
    # Drop foreign key and role_id column
    op.drop_constraint('fk_users_role_id', 'users', type_='foreignkey')
    op.drop_column('users', 'role_id')
    
    # Drop RBAC tables
    op.drop_table('role_permissions')
    op.drop_index(op.f('ix_permissions_resource'), table_name='permissions')
    op.drop_index(op.f('ix_permissions_name'), table_name='permissions')
    op.drop_index(op.f('ix_permissions_id'), table_name='permissions')
    op.drop_table('permissions')
    op.drop_index(op.f('ix_roles_name'), table_name='roles')
    op.drop_index(op.f('ix_roles_id'), table_name='roles')
    op.drop_table('roles')
