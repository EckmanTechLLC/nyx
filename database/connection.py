import asyncio
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        # Async engine for main operations
        self.async_engine = create_async_engine(
            settings.async_database_url,
            echo=False,  # Disable SQLAlchemy SQL logging to reduce output verbosity
            poolclass=NullPool if settings.debug else None,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        # Sync engine for migrations and setup
        self.sync_engine = create_engine(
            settings.database_url,
            echo=False,  # Disable SQLAlchemy SQL logging to reduce output verbosity
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        # Session factories
        self.async_session_factory = async_sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        self.sync_session_factory = sessionmaker(
            self.sync_engine,
            expire_on_commit=False
        )
        
        # Connection event handlers
        self._setup_connection_events()
    
    def _setup_connection_events(self):
        """Setup connection event handlers for optimization"""
        @event.listens_for(self.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            # This is for PostgreSQL, but we can add connection optimizations here
            pass
        
        @event.listens_for(self.async_engine.sync_engine, "connect")
        def set_async_sqlite_pragma(dbapi_connection, connection_record):
            # PostgreSQL async connection optimizations
            pass
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session with proper cleanup"""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()
    
    def get_sync_session(self) -> Session:
        """Get a synchronous database session"""
        return self.sync_session_factory()
    
    async def create_tables(self):
        """Create all database tables"""
        from database.models import Base
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    
    def create_tables_sync(self):
        """Create all database tables synchronously"""
        from database.models import Base
        Base.metadata.create_all(self.sync_engine)
        logger.info("Database tables created successfully (sync)")
    
    async def drop_tables(self):
        """Drop all database tables - use with caution!"""
        from database.models import Base
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped")
    
    async def close(self):
        """Close all database connections"""
        await self.async_engine.dispose()
        self.sync_engine.dispose()
        logger.info("Database connections closed")
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            from sqlalchemy import text
            async with self.get_async_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager()

# Dependency function for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session"""
    async with db_manager.get_async_session() as session:
        yield session

# Convenience functions
async def get_session() -> AsyncSession:
    """Get an async session for direct use"""
    return db_manager.async_session_factory()

def get_sync_session() -> Session:
    """Get a sync session for direct use"""
    return db_manager.get_sync_session()