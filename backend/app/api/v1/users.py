from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User
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
    assigned_client_id: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    tenant_id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str
    assigned_client_id: Optional[int] = None

    class Config:
        orm_mode = True

@router.get("/", response_model=List[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """List all users"""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [
        UserResponse(
            id=u.id,
            tenant_id=u.tenant_id,
            username=u.username,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at.isoformat() if u.created_at else "",
            assigned_client_id=u.assigned_client_id
        )
        for u in users
    ]

@router.post("/", response_model=UserResponse)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_role(["admin"]))):
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
async def update_user(user_id: int, payload: UserUpdate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_role(["admin"]))):
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
        created_at=user.created_at.isoformat() if user.created_at else "",
        assigned_client_id=user.assigned_client_id
    )

@router.delete("/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), current_user: dict = Depends(require_role(["admin"]))):
    """Delete a user"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted successfully"}
