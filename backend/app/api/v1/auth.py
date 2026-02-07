from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Role
from app.auth.jwt import create_access_token, get_current_user, verify_password, hash_password, decode_token
from app.auth.rbac import get_user_permissions
from pydantic import BaseModel
from typing import Optional, List
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class RefreshRequest(BaseModel):
    refresh_token: str

class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    tenant_id: int = 1
    role: str = "member"

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    tenant_id: int
    is_active: bool
    permissions: List[str] = []

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT token"""
    from sqlalchemy.orm import selectinload
    
    # Find user by username with eagerly loaded role
    result = await db.execute(
        select(User)
        .options(selectinload(User.role_obj))
        .where(User.username == payload.username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Verify password
    if not verify_password(payload.password, user.hashed_password or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Get user role name and permissions
    role_name = user.role_obj.name if user.role_obj else "member"
    permissions = await get_user_permissions(user.id, db)
    
    # Create access token
    token = create_access_token(
        subject=user.username,
        user_id=user.id,
        role=role_name
    )
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": role_name,
            "tenant_id": user.tenant_id,
            "permissions": list(permissions)
        }
    )

@router.post("/register", response_model=UserResponse)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    # Check if username exists
    result = await db.execute(
        select(User).where(User.username == payload.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    result = await db.execute(
        select(User).where(User.email == payload.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Get role_id from role name (default to member)
    role_result = await db.execute(
        select(Role).where(Role.name == payload.role)
    )
    role = role_result.scalar_one_or_none()
    if not role:
        # Default to member role if invalid
        role_result = await db.execute(select(Role).where(Role.name == "member"))
        role = role_result.scalar_one()
    
    # Create new user
    hashed_pwd = hash_password(payload.password)
    new_user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_pwd,
        tenant_id=payload.tenant_id,
        role_id=role.id
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Use the role we already fetched instead of trying to access role_obj
    role_name = role.name
    permissions = await get_user_permissions(new_user.id, db)
    
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        role=role_name,
        tenant_id=new_user.tenant_id,
        is_active=new_user.is_active,
        permissions=list(permissions)
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user information"""
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(User)
        .options(selectinload(User.role_obj))
        .where(User.id == current_user["user_id"])
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    role_name = user.role_obj.name if user.role_obj else "member"
    permissions = await get_user_permissions(user.id, db)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=role_name,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
        permissions=list(permissions)
    )

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user (client should delete token)"""
    return {"message": "Successfully logged out"}

@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(payload: RefreshRequest):
    data = decode_token(payload.refresh_token)
    if not data or data.get("sub") is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    username = data["sub"]
    user_id = data.get("user_id") or 0
    role = data.get("role") or "member"
    token = create_access_token(subject=username, user_id=user_id, role=role)
    return RefreshResponse(access_token=token)