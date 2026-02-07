"""
RBAC (Role-Based Access Control) permission checking utilities.

This module provides permission checking functions and FastAPI dependencies
for implementing fine-grained access control based on database-stored permissions.
"""

from typing import List, Set
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.auth.jwt import get_current_user


async def get_user_permissions(user_id: int, db: AsyncSession) -> Set[str]:
    """
    Get all permissions for a user based on their role.
    
    Queries the database to fetch the user's role and all associated permissions.
    Returns a set of permission strings for fast membership checking.
    
    Args:
        user_id (int): Database user ID
        db (AsyncSession): Database session
    
    Returns:
        Set[str]: Set of permission strings (e.g., {'users.view', 'clients.create'})
    
    Example:
        permissions = await get_user_permissions(42, db)
        if 'users.create' in permissions:
            # User can create users
    """
    from app.models.models import User, Role, Permission, role_permissions
    from sqlalchemy.orm import selectinload
    
    # Query user with eagerly loaded role and permissions
    result = await db.execute(
        select(User)
        .options(selectinload(User.role_obj).selectinload(Role.permissions))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.role_obj:
        return set()
    
    # Get permissions from role
    permissions = {perm.name for perm in user.role_obj.permissions}
    return permissions

async def has_permission(user: dict, permission: str, db: AsyncSession) -> bool:
    """
    Check if a user has a specific permission.
    
    Args:
        user (dict): Current user dict from get_current_user()
        permission (str): Permission to check (e.g., 'users.create')
        db (AsyncSession): Database session
    
    Returns:
        bool: True if user has the permission, False otherwise
    
    Example:
        if await has_permission(current_user, 'users.create', db):
            # User can create users
    """
    user_id = user.get("user_id")
    if not user_id:
        return False
    
    permissions = await get_user_permissions(user_id, db)
    return permission in permissions


async def has_any_permission(user: dict, permissions: List[str], db: AsyncSession) -> bool:
    """
    Check if a user has ANY of the specified permissions.
    
    Args:
        user (dict): Current user dict from get_current_user()
        permissions (List[str]): List of permissions to check
        db (AsyncSession): Database session
    
    Returns:
        bool: True if user has at least one permission, False otherwise
    
    Example:
        if await has_any_permission(current_user, ['users.view', 'users.create'], db):
            # User can view OR create users
    """
    user_id = user.get("user_id")
    if not user_id:
        return False
    
    user_permissions = await get_user_permissions(user_id, db)
    return any(perm in user_permissions for perm in permissions)


async def has_all_permissions(user: dict, permissions: List[str], db: AsyncSession) -> bool:
    """
    Check if a user has ALL of the specified permissions.
    
    Args:
        user (dict): Current user dict from get_current_user()
        permissions (List[str]): List of permissions to check
        db (AsyncSession): Database session
    
    Returns:
        bool: True if user has all permissions, False otherwise
    
    Example:
        if await has_all_permissions(current_user, ['users.view', 'users.create'], db):
            # User can BOTH view AND create users
    """
    user_id = user.get("user_id")
    if not user_id:
        return False
    
    user_permissions = await get_user_permissions(user_id, db)
    return all(perm in user_permissions for perm in permissions)


def require_permission(permission: str):
    """
    FastAPI dependency to require a specific permission.
    
    Use as a route dependency to protect endpoints with permission-based access control.
    Raises 403 Forbidden if user lacks the required permission.
    
    Args:
        permission (str): Required permission (e.g., 'users.create')
    
    Returns:
        Callable: Dependency function for FastAPI
    
    Usage:
        @router.post("/users/")
        async def create_user(
            current_user: dict = Depends(require_permission("users.create"))
        ):
            # Only users with 'users.create' permission can access this
            ...
    """
    async def _check_permission(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        if not await has_permission(current_user, permission, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires '{permission}' permission"
            )
        return current_user
    return _check_permission


def require_any_permission(permissions: List[str]):
    """
    FastAPI dependency to require ANY of the specified permissions.
    
    Use when user needs at least one permission from a list.
    Raises 403 Forbidden if user lacks all permissions.
    
    Args:
        permissions (List[str]): List of permissions (user needs at least one)
    
    Returns:
        Callable: Dependency function for FastAPI
    
    Usage:
        @router.get("/users/")
        async def list_users(
            current_user: dict = Depends(require_any_permission(["users.view", "users.edit"]))
        ):
            # Users with 'users.view' OR 'users.edit' can access this
            ...
    """
    async def _check_permissions(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        if not await has_any_permission(current_user, permissions, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires one of {permissions}"
            )
        return current_user
    return _check_permissions


def require_all_permissions(permissions: List[str]):
    """
    FastAPI dependency to require ALL of the specified permissions.
    
    Use when user needs multiple permissions simultaneously.
    Raises 403 Forbidden if user lacks any permission.
    
    Args:
        permissions (List[str]): List of permissions (user needs all)
    
    Returns:
        Callable: Dependency function for FastAPI
    
    Usage:
        @router.put("/users/{user_id}")
        async def update_user(
            current_user: dict = Depends(require_all_permissions(["users.view", "users.edit"]))
        ):
            # Users need BOTH 'users.view' AND 'users.edit' to access this
            ...
    """
    async def _check_permissions(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        if not await has_all_permissions(current_user, permissions, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires all of {permissions}"
            )
        return current_user
    return _check_permissions
