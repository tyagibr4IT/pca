"""
Initialize database with default users and roles.

This script creates:
1. Default tenant
2. Superadmin user (username: superadmin, password: superadmin123)
3. Default roles (superadmin, admin, member)
4. Default permissions
5. Assigns all permissions to superadmin role

Run this script after running alembic migrations on a fresh database.

Usage:
    python init_db.py
"""

import asyncio
import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/pca")

async def init_database():
    engine = create_async_engine(DATABASE_URL, future=True)
    
    try:
        async with engine.begin() as conn:
            print("🔍 Checking database state...")
            
            # Check if tenant exists
            tenant_result = await conn.execute(text("SELECT id FROM tenants WHERE id = 1"))
            tenant = tenant_result.fetchone()
            
            if not tenant:
                print("📦 Creating default tenant...")
                await conn.execute(text(
                    "INSERT INTO tenants (id, name, metadata) VALUES (1, 'Default Tenant', '{}'::jsonb)"
                ))
            else:
                print("✅ Default tenant already exists")
            
            # Check if roles exist
            role_result = await conn.execute(text("SELECT COUNT(*) FROM roles"))
            role_count = role_result.scalar()
            
            if role_count == 0:
                print("👥 Creating default roles...")
                await conn.execute(text("""
                    INSERT INTO roles (name, description) VALUES
                    ('superadmin', 'Super Administrator with full system access'),
                    ('admin', 'Administrator with management capabilities'),
                    ('member', 'Regular user with basic access')
                    ON CONFLICT (name) DO NOTHING
                """))
            else:
                print(f"✅ Roles already exist ({role_count} roles found)")
            
            # Check if permissions exist
            perm_result = await conn.execute(text("SELECT COUNT(*) FROM permissions"))
            perm_count = perm_result.scalar()
            
            if perm_count == 0:
                print("🔐 Creating default permissions...")
                permissions = [
                    ('users.view', 'View users'),
                    ('users.create', 'Create users'),
                    ('users.edit', 'Edit users'),
                    ('users.delete', 'Delete users'),
                    ('users.manage_roles', 'Manage user roles'),
                    ('clients.view', 'View clients'),
                    ('clients.create', 'Create clients'),
                    ('clients.edit', 'Edit clients'),
                    ('clients.delete', 'Delete clients'),
                    ('clients.assign', 'Assign clients to users'),
                    ('metrics.view', 'View metrics'),
                    ('metrics.export', 'Export metrics'),
                    ('chat.access', 'Access chat feature'),
                    ('chat.history', 'View chat history'),
                    ('reports.view', 'View reports'),
                    ('reports.export', 'Export reports'),
                    ('settings.view', 'View settings'),
                    ('settings.edit', 'Edit settings'),
                    ('audit.view', 'View audit logs'),
                    ('dashboard.view', 'View dashboard'),
                    ('dashboard.edit', 'Edit dashboard'),
                    ('api.access', 'Access API'),
                    ('system.manage', 'Manage system'),
                    ('notifications.manage', 'Manage notifications'),
                    ('permissions.manage', 'Manage permissions')
                ]
                
                for code, desc in permissions:
                    await conn.execute(text(
                        "INSERT INTO permissions (code, description) VALUES (:code, :desc) ON CONFLICT (code) DO NOTHING"
                    ), {"code": code, "desc": desc})
            else:
                print(f"✅ Permissions already exist ({perm_count} permissions found)")
            
            # Assign all permissions to superadmin role
            superadmin_perms = await conn.execute(text(
                "SELECT COUNT(*) FROM role_permissions rp JOIN roles r ON rp.role_id = r.id WHERE r.name = 'superadmin'"
            ))
            superadmin_perm_count = superadmin_perms.scalar()
            
            if superadmin_perm_count == 0:
                print("🔑 Assigning all permissions to superadmin role...")
                await conn.execute(text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT r.id, p.id
                    FROM roles r
                    CROSS JOIN permissions p
                    WHERE r.name = 'superadmin'
                    ON CONFLICT DO NOTHING
                """))
            else:
                print(f"✅ Superadmin role already has permissions ({superadmin_perm_count} permissions)")
            
            # Check if superadmin user exists
            user_result = await conn.execute(text("SELECT id FROM users WHERE username = 'superadmin'"))
            user = user_result.fetchone()
            
            if not user:
                print("👤 Creating superadmin user...")
                # Hash password: superadmin123
                hashed_pwd = bcrypt.hashpw("superadmin123".encode(), bcrypt.gensalt()).decode()
                
                # Get superadmin role ID
                role_result = await conn.execute(text("SELECT id FROM roles WHERE name = 'superadmin'"))
                role_id = role_result.scalar()
                
                await conn.execute(text("""
                    INSERT INTO users (tenant_id, username, email, hashed_password, role_id, is_active, status)
                    VALUES (1, 'superadmin', 'superadmin@example.com', :pwd, :role_id, true, 'active')
                """), {"pwd": hashed_pwd, "role_id": role_id})
                print("✅ Superadmin user created (username: superadmin, password: superadmin123)")
            else:
                print("✅ Superadmin user already exists")
                # Update password in case it needs to be reset
                hashed_pwd = bcrypt.hashpw("superadmin123".encode(), bcrypt.gensalt()).decode()
                await conn.execute(text(
                    "UPDATE users SET hashed_password = :pwd WHERE username = 'superadmin'"
                ), {"pwd": hashed_pwd})
                print("🔄 Superadmin password reset to: superadmin123")
            
            print("\n✨ Database initialization complete!")
            print("\n📝 Login credentials:")
            print("   Username: superadmin")
            print("   Password: superadmin123")
            print("\n🌐 Access the application at: http://localhost:3001")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_database())
