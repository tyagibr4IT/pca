"""
JWT token management and password hashing utilities.

This module provides JSON Web Token (JWT) creation, validation, and password
hashing/verification using industry-standard libraries (python-jose for JWT,
bcrypt for password hashing).

Security Features:
- HS256 algorithm for JWT signing (configurable to RS256)
- Bcrypt password hashing with automatic salting
- Token expiration validation
- Role-based access control via token claims

Configuration:
    JWT_SECRET: Secret key from environment (MUST be changed in production)
    JWT_ALGORITHM: Signing algorithm (default: HS256)
    JWT_EXPIRE_MINUTES: Token validity period (default: 60 minutes)

Author: Cloud Optimizer Team
Version: 2.0.0
Last Modified: 2026-01-25
"""

from datetime import datetime, timedelta
from typing import Optional, List, Set
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import bcrypt
from fastapi import Depends
from app.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db

# HTTP Bearer token extractor for FastAPI dependency injection
security = HTTPBearer()

def create_access_token(subject: str, user_id: int, role: str, scopes: list = None, expires_minutes: int = None):
    """
    Create a JWT access token with user claims.
    
    Generates a signed JWT token containing user identity, role, and expiration.
    The token is signed using the JWT_SECRET from configuration and includes
    standard claims (sub, exp) plus custom claims (user_id, role, scopes).
    
    Args:
        subject (str): Username or email (JWT 'sub' claim)
        user_id (int): Database user ID for quick lookups
        role (str): User role ("super_admin", "admin", "member")
        scopes (list, optional): Permission scopes (future use). Defaults to [].
        expires_minutes (int, optional): Token validity in minutes.
                                        Defaults to JWT_EXPIRE_MINUTES from config.
    
    Returns:
        str: Encoded JWT token string
    
    Token Structure:
        {
            "sub": "alice",                  # Username (subject)
            "user_id": 42,                   # Database ID
            "role": "admin",                 # Authorization role
            "scopes": [],                    # Permission scopes
            "exp": 1738234567                # Expiration (Unix timestamp)
        }
    
    Security:
        - Token is signed but NOT encrypted (don't put sensitive data in claims)
        - Client can decode payload (but cannot modify without invalidating signature)
        - Always validate token server-side before trusting claims
    
    Example:
        token = create_access_token(
            subject="alice",
            user_id=42,
            role="admin",
            expires_minutes=120
        )
        # Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    """
    # Calculate expiration time from now + configured minutes
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES)
    to_encode = {
        "sub": subject,
        "user_id": user_id,
        "role": role,
        "scopes": scopes or [],
        "exp": expire
    }
    encoded = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded

def decode_token(token: str):
    """
    Decode and validate a JWT token.
    
    Verifies the token signature using JWT_SECRET and decodes the payload.
    Returns None if token is invalid, expired, or signature verification fails.
    
    Args:
        token (str): JWT token string to decode
    
    Returns:
        dict: Token payload if valid, containing:
            - sub (str): Username
            - user_id (int): Database user ID
            - role (str): User role
            - scopes (list): Permission scopes
            - exp (int): Expiration timestamp
        None: If token is invalid, expired, or tampered
    
    Validation:
        - Signature verification using JWT_SECRET
        - Expiration time check (exp claim)
        - Algorithm validation (must match JWT_ALGORITHM)
    
    Example:
        payload = decode_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        if payload:
            user_id = payload["user_id"]
            role = payload["role"]
        else:
            # Token invalid or expired
            raise HTTPException(401, "Invalid token")
    """
    try:
        # Verify signature and decode payload
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        # Token is invalid, expired, or signature verification failed
        return None

def require_role(allowed: list):
    async def _dep(current: dict = Depends(get_current_user)):
        role = current.get("role")
        if role not in allowed:
            raise HTTPException(status_code=403, detail="Forbidden: insufficient role")
        return current
    return _dep

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    FastAPI dependency to extract and validate current authenticated user from JWT.
    
    This dependency function is injected into protected API endpoints to authenticate
    requests. It extracts the JWT token from the Authorization header, validates it,
    and returns the user information.
    
    Args:
        credentials (HTTPAuthorizationCredentials): Automatically extracted by FastAPI
                                                   from "Authorization: Bearer <token>" header
    
    Returns:
        dict: Current user information:
            - username (str): User's username
            - user_id (int): Database user ID
            - role (str): User's authorization role
    
    Raises:
        HTTPException(401): If token is missing, invalid, expired, or malformed
    
    Usage in API endpoints:
        @router.get("/protected")
        async def protected_endpoint(
            current_user: dict = Depends(get_current_user)
        ):
            username = current_user["username"]
            role = current_user["role"]
            return {"message": f"Hello {username}"}
    
    Request Example:
        GET /api/protected
        Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    # Check if token is valid
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user info from token claims
    username: str = payload.get("sub")
    user_id: int = payload.get("user_id")
    role: str = payload.get("role")
    
    # Validate required claims are present
    if username is None or user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "username": username,
        "user_id": user_id,
        "role": role
    }


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a bcrypt hash.
    
    Uses constant-time comparison via bcrypt.checkpw to prevent timing attacks.
    
    Args:
        plain_password (str): User-provided password to verify
        hashed_password (str): Stored bcrypt hash from database
    
    Returns:
        bool: True if password matches hash, False otherwise
    
    Security:
        - Bcrypt automatically handles salt extraction from hash
        - Constant-time comparison prevents timing attacks
        - Slow hashing (intentional) prevents brute-force attacks
    
    Example:
        stored_hash = "$2b$12$KIXxLVJ5q7dR8YnJ8lL9meX..."
        if verify_password("secret123", stored_hash):
            print("Password correct")
        else:
            print("Password incorrect")
    """
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        # Invalid salt format (corrupted or non-bcrypt hash)
        return False

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with automatic salt generation.
    
    Creates a bcrypt hash with automatic random salt. The salt is embedded
    in the returned hash string, so no separate storage is needed.
    
    Args:
        password (str): Plain text password to hash
    
    Returns:
        str: Bcrypt hash string (includes algorithm, cost, salt, and hash)
             Format: "$2b$12$salt..hash.."
    
    Security:
        - Automatic random salt generation (unique per password)
        - Default cost factor: 12 rounds (2^12 iterations)
        - Slow hashing prevents brute-force attacks
        - Future-proof (can increase cost factor for stronger security)
    
    Example:
        hashed = hash_password("secret123")
        # Returns: "$2b$12$KIXxLVJ5q7dR8YnJ8lL9meX..."
        
        # Store hashed in database
        user.hashed_password = hashed
    """
    # Generate random salt (unique for each password)
    salt = bcrypt.gensalt()
    # Hash password with salt and return as UTF-8 string
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')