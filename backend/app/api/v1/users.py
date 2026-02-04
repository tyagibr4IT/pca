from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.database import get_db
from app.models.models import User, UserClientPermission
from app.auth.jwt import get_current_user, hash_password, require_role
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/users", tags=["users"])

class UserCreate(BaseModel):
    tenant_id: int
    username: str
    email: str
    role: str = "member"
    password: Optional[str] = None

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    password: Optional[str] = None
    assigned_client_id: Optional[int] = None

class ClientPermissionCreate(BaseModel):
    client_id: int
    permission: str  # viewer / editor / approver

class UserClientPermissionsUpdate(BaseModel):
    permissions: List[ClientPermissionCreate]

class ClientPermissionResponse(BaseModel):
    id: int
    client_id: int
    permission: str
    created_at: str
    
    class Config:
        orm_mode = True

class AssignedClientInfo(BaseModel):
    id: int
    name: str
    permission: str

class UserResponse(BaseModel):
    id: int
    tenant_id: int
    username: str
    email: str
    role: str
    is_active: bool
    status: Optional[str] = "active"
    created_at: str
    assigned_client_id: Optional[int] = None
    assigned_clients: List[AssignedClientInfo] = []

    class Config:
        orm_mode = True

@router.get("/", response_model=List[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """List all users"""
    from app.models.models import Tenant
    from sqlalchemy import func as sql_func
    
    result = await db.execute(select(User))
    users = result.scalars().all()
    
    # Get all user IDs
    user_ids = [u.id for u in users]
    
    # Get only first 3 client permissions for each user (we only show 2 + count)
    if user_ids:
        # Use window function to limit results per user
        from sqlalchemy import func, literal_column
        
        perms_result = await db.execute(
            select(UserClientPermission, Tenant)
            .join(Tenant, UserClientPermission.client_id == Tenant.id)
            .where(UserClientPermission.user_id.in_(user_ids))
            .order_by(UserClientPermission.user_id, Tenant.name)
            .limit(len(user_ids) * 3)  # Max 3 per user
        )
        perms_by_user = {}
        for perm, tenant in perms_result.all():
            if perm.user_id not in perms_by_user:
                perms_by_user[perm.user_id] = []
            # Only take first 3 per user
            if len(perms_by_user[perm.user_id]) < 3:
                perms_by_user[perm.user_id].append(
                    AssignedClientInfo(id=tenant.id, name=tenant.name, permission=perm.permission)
                )
    else:
        perms_by_user = {}
    
    return [
        UserResponse(
            id=u.id,
            tenant_id=u.tenant_id,
            username=u.username,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
            status=u.status or "active",
            created_at=u.created_at.isoformat() if u.created_at else "",
            assigned_client_id=u.assigned_client_id,
            assigned_clients=perms_by_user.get(u.id, [])
        )
        for u in users
    ]

@router.post("/", response_model=UserResponse)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_role(["superadmin", "admin"]))):
    """Create a new user"""
    # In production, hash the password
    user = User(
        tenant_id=payload.tenant_id,
        username=payload.username,
        email=payload.email,
        role=payload.role,
        hashed_password=hash_password(payload.password) if payload.password else None
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        assigned_client_id=user.assigned_client_id
    )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get a specific user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else ""
    )

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, payload: UserUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_role(["superadmin", "admin"]))):
    """Update a user"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if payload.username is not None:
        user.username = payload.username
    if payload.email is not None:
        user.email = payload.email
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.status is not None:
        user.status = payload.status
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    if payload.assigned_client_id is not None:
        user.assigned_client_id = payload.assigned_client_id
    
    await db.commit()
    await db.refresh(user)
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        status=user.status or "active",
        created_at=user.created_at.isoformat() if user.created_at else "",
        assigned_client_id=user.assigned_client_id
    )

@router.delete("/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_role(["superadmin", "admin"]))):
    """Delete a user"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted successfully"}

@router.get("/{user_id}/client-permissions", response_model=List[ClientPermissionResponse])
async def get_user_client_permissions(user_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Get all client permissions for a user"""
    result = await db.execute(select(UserClientPermission).where(UserClientPermission.user_id == user_id))
    permissions = result.scalars().all()
    return [
        ClientPermissionResponse(
            id=p.id,
            client_id=p.client_id,
            permission=p.permission,
            created_at=p.created_at.isoformat() if p.created_at else ""
        )
        for p in permissions
    ]

@router.get("/{user_id}/available-clients")
async def get_available_clients(
    user_id: int,
    filter: str = "all",  # all, assigned, unassigned
    search: str = "",
    cloud_type: str = "",  # aws, azure, gcp
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get clients for assignment with filtering and pagination"""
    from app.models.models import Tenant
    
    # Get user's current permissions
    perm_result = await db.execute(
        select(UserClientPermission.client_id)
        .where(UserClientPermission.user_id == user_id)
    )
    assigned_client_ids = [row[0] for row in perm_result.all()]
    
    # Build base query
    query = select(Tenant)
    
    # Apply search filter
    if search:
        query = query.where(Tenant.name.ilike(f"%{search}%"))
    
    # Apply cloud type filter
    if cloud_type:
        from sqlalchemy import text
        query = query.where(
            text("metadata->>'provider' = :cloud_type")
        ).params(cloud_type=cloud_type)
    
    # Apply assignment filter
    if filter == "assigned":
        if assigned_client_ids:
            query = query.where(Tenant.id.in_(assigned_client_ids))
        else:
            # No assigned clients, return empty result
            query = query.where(Tenant.id == -1)
    elif filter == "unassigned":
        if assigned_client_ids:
            query = query.where(~Tenant.id.in_(assigned_client_ids))
    
    # Get total count
    from sqlalchemy import func as sql_func
    count_query = select(sql_func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.order_by(Tenant.name).limit(limit).offset(offset)
    result = await db.execute(query)
    clients = result.scalars().all()
    
    # Get permissions for assigned clients
    client_ids = [c.id for c in clients]
    if client_ids:
        perm_query = select(UserClientPermission).where(
            UserClientPermission.user_id == user_id,
            UserClientPermission.client_id.in_(client_ids)
        )
        perm_result = await db.execute(perm_query)
        permissions_map = {p.client_id: p.permission for p in perm_result.scalars().all()}
    else:
        permissions_map = {}
    
    return {
        "clients": [
            {
                "id": c.id,
                "name": c.name,
                "provider": c.metadata_json.get("provider", "unknown") if c.metadata_json else "unknown",
                "assigned": c.id in assigned_client_ids,
                "permission": permissions_map.get(c.id, "viewer")
            }
            for c in clients
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.post("/{user_id}/client-permissions")
async def update_user_client_permissions(
    user_id: int,
    payload: UserClientPermissionsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role(["superadmin", "admin"]))
):
    """Update all client permissions for a user (replaces existing permissions)"""
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete existing permissions
    await db.execute(delete(UserClientPermission).where(UserClientPermission.user_id == user_id))
    
    # Add new permissions
    for perm in payload.permissions:
        new_perm = UserClientPermission(
            user_id=user_id,
            client_id=perm.client_id,
            permission=perm.permission
        )
        db.add(new_perm)
    
    await db.commit()
    
    # Return updated permissions
    result = await db.execute(select(UserClientPermission).where(UserClientPermission.user_id == user_id))
    permissions = result.scalars().all()
    return {
        "message": "Client permissions updated successfully",
        "permissions": [
            {
                "id": p.id,
                "client_id": p.client_id,
                "permission": p.permission,
                "created_at": p.created_at.isoformat() if p.created_at else ""
            }
            for p in permissions
        ]
    }
