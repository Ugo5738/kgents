# auth_service/src/auth_service/db.py

from typing import AsyncGenerator, Callable, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from auth_service.config import settings
from auth_service.logging_config import logger
from shared.models.base import Base

# Use global variables to hold the lazily-initialized engine and factory
_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[Callable[..., AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """
    Returns the SQLAlchemy engine, creating it if it doesn't exist.
    This lazy initialization ensures it uses the latest settings.
    """
    global _engine
    if _engine is None:
        logger.info(
            f"Creating new AsyncEngine with DATABASE_URL: {settings.DATABASE_URL}"
        )
        _engine = create_async_engine(
            str(settings.DATABASE_URL),
            echo=(settings.LOGGING_LEVEL.upper() == "DEBUG"),
            pool_size=10,  # Number of connections to keep open.
            max_overflow=5,  # Number of extra connections allowed.
            pool_timeout=30,  # Seconds to wait before giving up on getting a connection.
            pool_recycle=1800,  # Recycle connections every 30 minutes.
            pool_pre_ping=True,  # Check connection health before use.
            connect_args={"options": "-c search_path=auth_service_data,public"},
        )
        logger.info("AsyncEngine created successfully")
    return _engine


async def close_engine() -> None:
    """Close the global engine and all its connections."""
    global _engine
    if _engine is not None:
        logger.info("Closing AsyncEngine and all its connections")
        await _engine.dispose()
        _engine = None
        logger.info("AsyncEngine closed successfully")
    else:
        logger.info("No AsyncEngine to close")


def reset_session_factory() -> None:
    """Reset the session factory to force recreation on next access."""
    global _async_session_factory
    if _async_session_factory is not None:
        logger.info("Resetting AsyncSession factory")
        _async_session_factory = None
        logger.info("AsyncSession factory has been reset")
    else:
        logger.info("No AsyncSession factory to reset")


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Returns the session factory, creating it if it doesn't exist.
    """
    global _async_session_factory
    if _async_session_factory is None:
        logger.info("SQLAlchemy session factory not initialized. Creating new factory.")
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _async_session_factory


# --- 4. Standardized Session Dependency ---
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a transactional, auto-closing database session.

    This standard pattern ensures that:
    1. A new session is created for each request.
    2. Any database errors during the request cause a transaction rollback.
    3. The session is always closed, preventing connection leaks.
    """
    factory = get_session_factory()
    session = factory()
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
