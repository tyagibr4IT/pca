"""
API endpoints for managing user-specific permissions.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from app.db.database import get_db
from app.models.models import User, Permission, Role, user_permissions
from app.auth.jwt import get_current_user
from app.auth.rbac import require_permission
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/permissions", tags=["permissions"])


class UserPermissionResponse(BaseModel):
    """Response model for user permissions"""
    user_id: int
    username: str
    role: str
    permissions: List[str]

    class Config:
        orm_mode = True


class GrantPermissionRequest(BaseModel):
    """Request to grant permissions to a user"""
    user_id: int
    permission_names: List[str]


class RevokePermissionRequest(BaseModel):
    """Request to revoke permissions from a user"""
    user_id: int
    permission_names: List[str]


@router.get("/available", response_model=List[dict])
async def list_available_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("permissions.manage"))
):
    """
    List all available permissions in the system.
    Requires: permissions.manage
    """
    result = await db.execute(select(Permission).order_by(Permission.resource, Permission.action))
    permissions = result.scalars().all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "resource": p.resource,
            "action": p.action,
            "description": p.description
        }
        for p in permissions
    ]


@router.get("/user/{user_id}", response_model=UserPermissionResponse)
async def get_user_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("permissions.manage"))
):
    """
    Get all permissions for a specific user (from their role).
    Requires: permissions.manage
    """
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.role_obj).selectinload(Role.permissions)
        )
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get permissions from role
    permission_names = []
    if user.role_obj and user.role_obj.permissions:
        permission_names = [p.name for p in user.role_obj.permissions]
    
    return UserPermissionResponse(
        user_id=user.id,
        username=user.username,
        role=user.role_obj.name if user.role_obj else "member",
        permissions=permission_names
    )


@router.get("/role/{role_name}", response_model=dict)
async def get_role_permissions(
    role_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("permissions.manage"))
):
    """
    Get all permissions for a specific role.
    Requires: permissions.manage
    """
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.name == role_name)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found")
    
    permission_names = [p.name for p in role.permissions] if role.permissions else []
    
    return {
        "role": role.name,
        "description": role.description,
        "is_system": role.is_system,
        "permissions": permission_names,
        "permission_count": len(permission_names)
    }


@router.post("/role/{role_name}/grant")
async def grant_permissions_to_role(
    role_name: str,
    permission_names: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("permissions.manage"))
):
    """
    Grant permissions to a role.
    Requires: permissions.manage
    
    SECURITY: Cannot modify superadmin role
    """
    # Prevent modifying superadmin role
    if role_name == "superadmin":
        raise HTTPException(
            status_code=403,
            detail="Cannot modify superadmin role permissions"
        )
    
    # Get the role
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.name == role_name)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found")
    
    # Get the permissions
    granted = []
    not_found = []
    already_has = []
    
    for perm_name in permission_names:
        perm_result = await db.execute(
            select(Permission).where(Permission.name == perm_name)
        )
        permission = perm_result.scalar_one_or_none()
        
        if not permission:
            not_found.append(perm_name)
            continue
        
        # Check if role already has this permission
        if permission in role.permissions:
            already_has.append(perm_name)
            continue
        
        # Grant permission
        role.permissions.append(permission)
        granted.append(perm_name)
    
    await db.commit()
    
    return {
        "role": role_name,
        "granted": granted,
        "already_has": already_has,
        "not_found": not_found,
        "message": f"Granted {len(granted)} permissions to role '{role_name}'"
    }


@router.post("/role/{role_name}/revoke")
async def revoke_permissions_from_role(
    role_name: str,
    permission_names: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("permissions.manage"))
):
    """
    Revoke permissions from a role.
    Requires: permissions.manage
    
    SECURITY: Cannot modify superadmin role
    """
    # Prevent modifying superadmin role
    if role_name == "superadmin":
        raise HTTPException(
            status_code=403,
            detail="Cannot modify superadmin role permissions"
        )
    
    # Get the role
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.name == role_name)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found")
    
    # Revoke the permissions
    revoked = []
    not_found = []
    did_not_have = []
    
    for perm_name in permission_names:
        perm_result = await db.execute(
            select(Permission).where(Permission.name == perm_name)
        )
        permission = perm_result.scalar_one_or_none()
        
        if not permission:
            not_found.append(perm_name)
            continue
        
        # Check if role has this permission
        if permission not in role.permissions:
            did_not_have.append(perm_name)
            continue
        
        # Revoke permission
        role.permissions.remove(permission)
        revoked.append(perm_name)
    
    await db.commit()
    
    return {
        "role": role_name,
        "revoked": revoked,
        "did_not_have": did_not_have,
        "not_found": not_found,
        "message": f"Revoked {len(revoked)} permissions from role '{role_name}'"
    }


@router.get("/user/{user_id}/effective", response_model=dict)
async def get_user_effective_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("permissions.manage"))
):
    """
    Get effective permissions for a user (role permissions + user-specific overrides).
    Requires: permissions.manage
    """
    # Get user with role and user-specific permissions
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.role_obj).selectinload(Role.permissions),
            selectinload(User.user_permissions)
        )
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get role permissions
    role_permissions = []
    if user.role_obj and user.role_obj.permissions:
        role_permissions = [p.name for p in user.role_obj.permissions]
    
    # Get user-specific permissions
    user_specific = []
    if user.user_permissions:
        user_specific = [p.name for p in user.user_permissions]
    
    # Combine (user-specific permissions are additions to role permissions)
    effective_permissions = list(set(role_permissions + user_specific))
    
    return {
        "user_id": user.id,
        "username": user.username,
        "role": user.role_obj.name if user.role_obj else "member",
        "role_permissions": role_permissions,
        "user_specific_permissions": user_specific,
        "effective_permissions": sorted(effective_permissions),
        "total_permissions": len(effective_permissions)
    }


@router.post("/user/{user_id}/grant")
async def grant_permissions_to_user(
    user_id: int,
    permission_names: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("permissions.manage"))
):
    """
    Grant specific permissions to a user (in addition to their role permissions).
    Requires: permissions.manage
    
    SECURITY: Cannot grant permissions to user ID 1 (system superadmin)
    """
    # Prevent modifying superadmin user
    if user_id == 1:
        raise HTTPException(
            status_code=403,
            detail="Cannot modify permissions for system superadmin (user ID 1)"
        )
    
    # Get the user
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_permissions))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail=f"User ID {user_id} not found")
    
    # Get the permissions
    granted = []
    not_found = []
    already_has = []
    
    for perm_name in permission_names:
        perm_result = await db.execute(
            select(Permission).where(Permission.name == perm_name)
        )
        permission = perm_result.scalar_one_or_none()
        
        if not permission:
            not_found.append(perm_name)
            continue
        
        # Check if user already has this permission
        if permission in user.user_permissions:
            already_has.append(perm_name)
            continue
        
        # Grant permission
        user.user_permissions.append(permission)
        granted.append(perm_name)
    
    await db.commit()
    
    return {
        "user_id": user_id,
        "username": user.username,
        "granted": granted,
        "already_has": already_has,
        "not_found": not_found,
        "message": f"Granted {len(granted)} permissions to user '{user.username}'"
    }


@router.post("/user/{user_id}/revoke")
async def revoke_permissions_from_user(
    user_id: int,
    permission_names: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("permissions.manage"))
):
    """
    Revoke specific permissions from a user.
    Requires: permissions.manage
    
    SECURITY: Cannot revoke permissions from user ID 1 (system superadmin)
    """
    # Prevent modifying superadmin user
    if user_id == 1:
        raise HTTPException(
            status_code=403,
            detail="Cannot modify permissions for system superadmin (user ID 1)"
        )
    
    # Get the user
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_permissions))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail=f"User ID {user_id} not found")
    
    # Revoke the permissions
    revoked = []
    not_found = []
    did_not_have = []
    
    for perm_name in permission_names:
        perm_result = await db.execute(
            select(Permission).where(Permission.name == perm_name)
        )
        permission = perm_result.scalar_one_or_none()
        
        if not permission:
            not_found.append(perm_name)
            continue
        
        # Check if user has this permission
        if permission not in user.user_permissions:
            did_not_have.append(perm_name)
            continue
        
        # Revoke permission
        user.user_permissions.remove(permission)
        revoked.append(perm_name)
    
    await db.commit()
    
    return {
        "user_id": user_id,
        "username": user.username,
        "revoked": revoked,
        "did_not_have": did_not_have,
        "not_found": not_found,
        "message": f"Revoked {len(revoked)} permissions from user '{user.username}'"
    }

