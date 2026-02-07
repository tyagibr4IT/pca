# RBAC (Role-Based Access Control) Implementation Guide

## 🎯 Overview

This document provides a complete guide to the Role-Based Access Control system implemented in the Cloud Optimizer platform.

## 📊 System Architecture

### Database Schema

```
roles
├── id (Primary Key)
├── name (unique: superadmin, admin, member)
├── description
├── is_system (boolean)
└── created_at

permissions
├── id (Primary Key)
├── name (unique: e.g., "users.view")
├── resource (e.g., "users")
├── action (e.g., "view")
├── description
└── created_at

role_permissions (Association Table)
├── role_id (Foreign Key → roles.id)
└── permission_id (Foreign Key → permissions.id)

users
├── id (Primary Key)
├── role_id (Foreign Key → roles.id)
└── ... (other user fields)
```

### Permission Format

Permissions follow the pattern: `{resource}.{action}`

Examples:
- `users.view` - View users list
- `users.create` - Create new users
- `clients.edit` - Edit client configurations
- `metrics.view` - Access metrics dashboard

## 🔐 Roles and Permissions

### Default Roles

#### 1. **Superadmin** (24 permissions)
Full system access with all permissions:

**Users Management:**
- users.view
- users.create
- users.edit
- users.delete
- users.manage_roles

**Clients Management:**
- clients.view
- clients.create
- clients.edit
- clients.delete
- clients.assign

**Metrics:**
- metrics.view
- metrics.export

**Chat:**
- chat.access
- chat.history.view
- chat.history.delete

**System:**
- system.settings.view
- system.settings.edit
- system.logs.view

**Resources:**
- resources.view
- resources.create
- resources.edit
- resources.delete
- resources.export
- resources.import

#### 2. **Admin** (20 permissions)
Administrative access with restrictions:

**Excluded permissions:**
- users.delete
- users.manage_roles
- system.settings.edit
- resources.delete

#### 3. **Member** (7 permissions)
Basic read-only access:

**Allowed permissions:**
- users.view
- clients.view
- metrics.view
- chat.access
- chat.history.view
- resources.view
- system.settings.view

## 🛠️ Backend Implementation

### Files Modified/Created

#### 1. `backend/app/auth/permissions.py` (NEW)
Defines all permissions and role mappings:

```python
class Permission(str, Enum):
    # Users
    USERS_VIEW = "users.view"
    USERS_CREATE = "users.create"
    # ... all 24 permissions

DEFAULT_ROLE_PERMISSIONS = {
    "superadmin": [all 24 permissions],
    "admin": [20 permissions],
    "member": [7 permissions]
}
```

#### 2. `backend/app/auth/rbac.py` (NEW)
Permission checking utilities:

```python
# Get user permissions from database
async def get_user_permissions(user_id, db) -> Set[str]

# Check if user has permission
async def has_permission(user, permission, db) -> bool

# FastAPI dependency decorators
def require_permission(permission: str) -> Callable
def require_any_permission(permissions: List[str]) -> Callable
def require_all_permissions(permissions: List[str]) -> Callable
```

#### 3. `backend/app/models/models.py` (UPDATED)
Added RBAC models:

```python
# Many-to-many association
role_permissions = Table('role_permissions', ...)

# Role model
class Role(Base):
    __tablename__ = "roles"
    id, name, description, is_system, created_at
    permissions = relationship("Permission", secondary=role_permissions)

# Permission model
class Permission(Base):
    __tablename__ = "permissions"
    id, name, resource, action, description, created_at

# User model updated
class User(Base):
    role_id = Column(Integer, ForeignKey("roles.id"))  # Changed from role (String)
    role_obj = relationship("Role")
```

#### 4. `backend/alembic/versions/0007_add_rbac.py` (NEW)
Database migration that:
- Creates roles, permissions, role_permissions tables
- Seeds 3 roles and 24 permissions
- Migrates existing users from role string to role_id
- Successfully applied ✅

#### 5. `backend/app/api/v1/auth.py` (UPDATED)
Authentication endpoints now return permissions:

```python
@router.post("/login")
async def login(...):
    permissions = await get_user_permissions(user.id, db)
    return {
        "user": {
            ...,
            "permissions": list(permissions)
        }
    }
```

#### 6. `backend/app/api/v1/users.py` (UPDATED)
All endpoints use permission checks:

```python
@router.post("/")
async def create_user(
    current_user: dict = Depends(require_permission("users.create"))
)

@router.put("/{id}")
async def update_user(
    current_user: dict = Depends(require_permission("users.edit"))
)

@router.delete("/{id}")
async def delete_user(
    current_user: dict = Depends(require_permission("users.delete"))
)
```

#### 7. `backend/app/api/v1/clients.py` (UPDATED)
Client management with permissions:

```python
@router.post("/")
async def create_client(
    current_user: dict = Depends(require_permission("clients.create"))
)

@router.put("/{id}")
async def update_client(
    current_user: dict = Depends(require_permission("clients.edit"))
)

@router.delete("/{id}")
async def delete_client(
    current_user: dict = Depends(require_permission("clients.delete"))
)
```

## 🎨 Frontend Implementation

### Files Modified/Created

#### 1. `frontend/static/js/permissions.js` (NEW)
Permission management utility:

```javascript
// Core functions
hasPermission(permission)           // Check single permission
hasAnyPermission(permissions)       // Check if user has ANY of the permissions
hasAllPermissions(permissions)      // Check if user has ALL permissions

// Initialization
loadUserPermissions()               // Fetch from /api/auth/me
initializePermissions()             // Load and apply restrictions
applyPermissionRestrictions()       // Hide elements without permission

// UI Helpers
showIfHasPermission(elementId, permission)
disableIfNoPermission(elementId, permission)
```

#### 2. HTML Pages Updated

**All pages now include:**
```html
<script src="./js/permissions.js"></script>
```

**Pages updated:**
- admin.html
- clients.html
- dashboard.html
- metrics.html
- chat.html

#### 3. HTML Permission Attributes

Use data attributes to control visibility:

```html
<!-- Single permission -->
<button data-require-permission="users.create">Add User</button>

<!-- Any permission (OR logic) -->
<div data-require-any-permission="users.edit, users.view">...</div>

<!-- All permissions (AND logic) -->
<div data-require-all-permissions="users.edit, system.settings.edit">...</div>
```

#### 4. JavaScript Updates

**admin.js:**
- Initialize permissions on DOMContentLoaded
- Conditionally render action buttons based on permissions
- Hide Add User button if no users.create permission

**clients.js:**
- Initialize permissions on DOMContentLoaded
- Conditionally render Edit/Delete buttons
- Hide Add Client button if no clients.create permission

**dashboard.js:**
- Initialize permissions on page load
- Control navigation menu visibility

#### 5. Navigation Updates

User Management link uses permission check:

```html
<!-- Before -->
<a class="nav-link admin-only" href="./admin.html">User Management</a>

<!-- After -->
<a class="nav-link" href="./admin.html" data-require-permission="users.view">
  User Management
</a>
```

## 🧪 Testing Guide

### 1. Login as Different Roles

**Test Superadmin:**
```bash
# Login with superadmin credentials
# Should see all buttons and menu items
```

**Test Admin:**
```bash
# Login with admin credentials
# Should NOT see:
# - Delete User button
# - Change Role button (users.manage_roles)
# - System Settings Edit
```

**Test Member:**
```bash
# Login with member credentials
# Should ONLY see:
# - View-only access to users, clients, metrics
# - No create/edit/delete buttons
# - No admin navigation links
```

### 2. API Endpoint Testing

**Test Permission Enforcement:**

```bash
# As member, try to create user (should fail with 403)
curl -X POST http://localhost:8001/api/users/ \
  -H "Authorization: Bearer <member_token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "email": "test@example.com", "role": "member"}'

# Expected response: 403 Forbidden
{"detail": "Permission denied. Required permission: users.create"}
```

**Test Permission Response:**

```bash
# Check /me endpoint returns permissions
curl http://localhost:8001/api/auth/me \
  -H "Authorization: Bearer <token>"

# Expected response:
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "permissions": [
    "users.view",
    "users.create",
    "users.edit",
    ...
  ]
}
```

### 3. Frontend Testing

**Test Button Visibility:**
1. Login as member
2. Navigate to admin.html
3. Verify "Add User" button is hidden
4. Verify no Edit/Delete buttons in user table

**Test Navigation:**
1. Login as member
2. Verify "User Management" link is hidden in sidebar
3. Navigate to dashboard.html
4. Verify same link is hidden

**Test Permission Loading:**
1. Open browser console
2. Login
3. Check for "Loaded permissions: [...]" message
4. Verify permissions array matches user role

## 📝 Usage Examples

### Backend: Protect an Endpoint

```python
from app.auth.rbac import require_permission

@router.post("/resources/")
async def create_resource(
    payload: ResourceCreate,
    current_user: dict = Depends(require_permission("resources.create")),
    db: AsyncSession = Depends(get_db)
):
    # Only users with resources.create permission can access
    resource = Resource(**payload.dict())
    db.add(resource)
    await db.commit()
    return resource
```

### Frontend: Conditional Rendering

**HTML:**
```html
<!-- Button only visible with permission -->
<button 
  id="deleteBtn" 
  class="btn btn-danger"
  data-require-permission="resources.delete">
  Delete Resource
</button>
```

**JavaScript:**
```javascript
// Check permission in code
if (window.PermissionManager.hasPermission('resources.delete')) {
  // Show delete option
  renderDeleteButton();
}

// Check multiple permissions
if (window.PermissionManager.hasAnyPermission(['resources.edit', 'resources.create'])) {
  // Show form
  renderResourceForm();
}
```

## 🔄 Migration Status

**Migration:** `0007_add_rbac.py` ✅ Applied

**Database State:**
- ✅ 3 roles created (superadmin, admin, member)
- ✅ 24 permissions created
- ✅ 51 role-permission mappings created
- ✅ All existing users migrated to role_id system
- ✅ No data loss during migration

## 🚀 Deployment Checklist

- [x] Backend models created
- [x] Migration applied to database
- [x] Permission utilities implemented
- [x] API endpoints protected
- [x] Frontend permission utility created
- [x] All pages updated with permission checks
- [x] Navigation links permission-controlled
- [x] Action buttons conditionally rendered
- [x] Backend container restarted ✅
- [x] Frontend container restarted ✅

## 📚 Next Steps (Phase 6)

To complete the RBAC system, implement Phase 6: Permission Management UI

**TODO:**
1. Create `frontend/static/roles.html` - Role management page
2. Create `frontend/static/js/roles.js` - Role management logic
3. Create `backend/app/api/v1/roles.py` - Role management endpoints:
   - GET /api/roles/ - List roles
   - GET /api/roles/{id} - Get role details
   - PUT /api/roles/{id}/permissions - Update role permissions
   - GET /api/permissions/ - List all available permissions

This will allow superadmins to manage role permissions through the UI.

## 🔍 Troubleshooting

### Issue: Permissions not loading

**Solution:**
```javascript
// Check in browser console
console.log(window.PermissionManager.getUserPermissions());

// Reload permissions
await window.PermissionManager.loadUserPermissions();
```

### Issue: Button still showing without permission

**Solution:**
1. Check if `data-require-permission` attribute is correct
2. Verify permissions.js is loaded before page scripts
3. Check console for permission initialization errors

### Issue: 403 Permission Denied

**Solution:**
1. Check user's role in database:
   ```sql
   SELECT u.username, r.name as role 
   FROM users u 
   JOIN roles r ON u.role_id = r.id;
   ```
2. Check role permissions:
   ```sql
   SELECT r.name, p.name as permission
   FROM roles r
   JOIN role_permissions rp ON r.id = rp.role_id
   JOIN permissions p ON rp.permission_id = p.id
   WHERE r.name = 'admin';
   ```

## 📈 Benefits

1. **Fine-grained Access Control**: Control access at the feature level, not just role level
2. **Flexible Role Management**: Easily add/modify permissions for roles
3. **Security**: Backend enforcement prevents API bypass
4. **User Experience**: Frontend hides unavailable features
5. **Maintainability**: Centralized permission definitions
6. **Scalability**: Easy to add new permissions and roles

## 🎓 Best Practices

1. **Always check permissions on backend** - Frontend checks are for UX only
2. **Use semantic permission names** - `users.create` not `create_user`
3. **Group related permissions** - Use resource prefixes (users.*, clients.*)
4. **Document permission requirements** - Comment which permissions are needed
5. **Test with different roles** - Verify all permission scenarios work

## 📞 Support

For issues or questions about the RBAC system:
1. Check this documentation first
2. Review the implementation files listed above
3. Test with different roles to isolate the issue
4. Check browser console and backend logs for errors

---

**Last Updated:** After Phase 5 completion
**Status:** ✅ Phases 1-5 Complete | Phase 6 Pending
**Database:** PostgreSQL with RBAC tables
**Backend:** FastAPI with permission decorators
**Frontend:** JavaScript permission manager
