# conversation_service/src/conversation_service/db.py

from typing import AsyncGenerator, Callable, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shared.models.base import Base

from .config import settings
from .logging_config import logger

_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[Callable[..., AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """Returns the SQLAlchemy engine, creating it if it doesn't exist."""
    global _engine
    if _engine is None:
        logger.info(f"Creating new AsyncEngine for {settings.PROJECT_NAME}")
        _engine = create_async_engine(
            str(settings.DATABASE_URL),
            echo=(settings.LOGGING_LEVEL.upper() == "DEBUG"),
            pool_pre_ping=True,
        )
        logger.info("AsyncEngine created successfully")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Returns the session factory, creating it if it doesn't exist."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a transactional, auto-closing database session.
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
        await session.rollback()
        raise
    finally:
        await session.close()
