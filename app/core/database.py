"""
Database connection and session management for the Veterinary Clinic Backend.
Uses SQLAlchemy 2.0 with async support and Supabase PostgreSQL.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import MetaData
from typing import AsyncGenerator
import logging

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# SQLAlchemy Base
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()

# Async engine configuration
if "sqlite" in settings.DATABASE_URL:
    # SQLite configuration (for testing)
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,  # Log SQL queries in debug mode
        poolclass=NullPool,  # SQLite doesn't support connection pooling
    )
else:
    # PostgreSQL configuration (for production)
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,  # Log SQL queries in debug mode
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,  # Validate connections before use
        pool_recycle=3600,  # Recycle connections every hour
    )

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    Yields:
        AsyncSession: Database session for dependency injection
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.
    This should be called during application startup in development only.
    In production, use Alembic migrations instead.
    """
    settings = get_settings()

    # Only auto-create tables in development
    if settings.ENVIRONMENT == "development":
        try:
            async with engine.begin() as conn:
                # Import all models to ensure they're registered (order matters for foreign keys)
                from app.models import user, pet, clinic, appointment, communication

                # Create all tables if they don't exist
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created successfully (development mode)")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    else:
        logger.info(
            f"Skipping auto table creation in {settings.ENVIRONMENT} environment. Use Alembic migrations."
        )


async def ensure_tables_exist() -> bool:
    """
    Check if required tables exist in the database.

    Returns:
        bool: True if tables exist, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            # Try to query the users table as a basic check
            from app.models.user import User
            from sqlalchemy import text

            await session.execute(text("SELECT 1 FROM users LIMIT 1"))
            return True
    except Exception:
        return False


async def close_db() -> None:
    """
    Close database connections.
    This should be called during application shutdown.
    """
    try:
        await engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Failed to close database connections: {e}")
        raise


class DatabaseHealthCheck:
    """Database health check utility."""

    @staticmethod
    async def check_connection() -> bool:
        """
        Check if database connection is healthy.

        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import text

                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @staticmethod
    async def get_connection_info() -> dict:
        """
        Get database connection information.

        Returns:
            dict: Connection information and statistics
        """
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import text

                result = await session.execute(
                    text(
                        """
                    SELECT 
                        version() as version,
                        current_database() as database,
                        current_user as user,
                        inet_server_addr() as server_addr,
                        inet_server_port() as server_port
                """
                    )
                )
                row = result.fetchone()

                return {
                    "status": "healthy",
                    "version": row.version if row else "unknown",
                    "database": row.database if row else "unknown",
                    "user": row.user if row else "unknown",
                    "server_addr": row.server_addr if row else "unknown",
                    "server_port": row.server_port if row else "unknown",
                    "pool_size": engine.pool.size(),
                    "checked_out": engine.pool.checkedout(),
                    "overflow": engine.pool.overflow(),
                }
        except Exception as e:
            logger.error(f"Failed to get database connection info: {e}")
            return {"status": "unhealthy", "error": str(e)}
