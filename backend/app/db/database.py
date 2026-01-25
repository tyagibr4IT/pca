"""
Database configuration and session management using SQLAlchemy async.

This module initializes the PostgreSQL database connection with async support
and provides session management for FastAPI dependency injection. All database
operations use async/await patterns for optimal performance.

Database Features:
- Async I/O with asyncpg driver (postgresql+asyncpg://)
- Connection pooling (default: 5-20 connections)
- Automatic session cleanup via context managers
- Declarative ORM base for model definitions

Connection String Format:
    postgresql+asyncpg://user:password@host:port/database

Example:
    postgresql+asyncpg://cloudopt:secret@localhost:5432/cloudoptimizer

Usage in API endpoints:
    from app.db.database import get_db
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    
    @router.get("/example")
    async def example(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(User).where(User.id == 1))
        user = result.scalar_one_or_none()
        return {"user": user}

Author: Cloud Optimizer Team
Version: 2.0.0
Last Modified: 2026-01-25
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Database connection URL from environment configuration
DATABASE_URL = settings.DATABASE_URL

# Create async database engine
# - future=True: Enable SQLAlchemy 2.0 style
# - echo=False: Disable SQL query logging (set True for debugging)
engine = create_async_engine(DATABASE_URL, future=True, echo=False)

# Session factory for creating database sessions
# - expire_on_commit=False: Keep objects accessible after commit
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Declarative base for ORM models
# All model classes should inherit from this Base
Base = declarative_base()

async def get_db():
    """
    FastAPI dependency for database session injection.
    
    This async generator function provides database sessions to API endpoints
    via FastAPI's dependency injection system. The session is automatically
    created, yielded to the endpoint, and properly closed after the request
    completes (even if an exception occurs).
    
    Yields:
        AsyncSession: SQLAlchemy async database session
    
    Session Lifecycle:
        1. Request arrives at endpoint
        2. FastAPI calls get_db() to create session
        3. Session is injected into endpoint function
        4. Endpoint executes database queries
        5. Session is automatically closed (via context manager)
    
    Error Handling:
        - If endpoint raises exception, session is rolled back automatically
        - Session cleanup happens in __aexit__ of context manager
        - Connection is returned to pool for reuse
    
    Usage:
        @router.get("/users/{user_id}")
        async def get_user(
            user_id: int,
            db: AsyncSession = Depends(get_db)
        ):
            result = await db.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
    
    Performance:
        - Connection pooling reduces overhead (connections are reused)
        - Async I/O allows handling multiple requests concurrently
        - No blocking on database queries
    """
    async with AsyncSessionLocal() as session:
        yield session