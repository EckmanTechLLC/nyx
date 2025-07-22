"""
Database dependency management for FastAPI.

Provides database session dependencies using NYX's existing database manager.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Import existing database manager
from database.connection import db_manager

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.
    
    Provides proper session lifecycle management with automatic
    commit/rollback handling.
    
    Yields:
        AsyncSession: Database session
    """
    async with db_manager.get_async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # Use db session
            pass
    
    Yields:
        AsyncSession: Database session
    """
    async with get_db_session() as session:
        yield session

async def check_database_health() -> bool:
    """
    Check if database is healthy and accessible.
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        return await db_manager.test_connection()
    except Exception:
        return False