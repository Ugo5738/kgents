from typing import AsyncGenerator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from auth_service.config import settings
from auth_service.logging_config import logger

# --- 1. Database Engine Configuration ---
# Use create_async_engine for explicit configuration.
# The connection pool is configured for a robust server environment.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.LOGGING_LEVEL.upper() == "DEBUG"),
    pool_size=10,  # Number of connections to keep open.
    max_overflow=5,  # Number of extra connections allowed.
    pool_timeout=30,  # Seconds to wait before giving up on getting a connection.
    pool_recycle=1800,  # Recycle connections every 30 minutes.
    pool_pre_ping=True,  # Check connection health before use.
)

# --- 2. Session Factory ---
# A factory to create new async sessions.
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# --- 3. Declarative Base ---
# All SQLAlchemy models will inherit from this Base.
Base = declarative_base()


# --- 4. Standardized Session Dependency ---
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a transactional, auto-closing database session.

    This standard pattern ensures that:
    1. A new session is created for each request.
    2. Any database errors during the request cause a transaction rollback.
    3. The session is always closed, preventing connection leaks.
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database transaction failed: {e}", exc_info=True)
        await session.rollback()
        raise
    except Exception:
        # Also rollback on non-SQLAlchemy errors
        await session.rollback()
        raise
    finally:
        await session.close()
