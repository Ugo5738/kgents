"""
Database utilities for testing.

This module provides helper functions for database operations in tests.
"""

import asyncio
import contextlib
from typing import AsyncGenerator, List, Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tool_registry_service.models import base


async def create_db_objects(session: AsyncSession, objects: List[base.Base]) -> None:
    """
    Create multiple database objects in a single transaction.
    
    Args:
        session: Database session
        objects: List of database model instances to create
    """
    for obj in objects:
        session.add(obj)
    await session.commit()


async def get_by_id(
    session: AsyncSession, model: Type[base.Base], id: str
) -> Optional[base.Base]:
    """
    Get a database object by ID.
    
    Args:
        session: Database session
        model: Model class
        id: Object ID
        
    Returns:
        Optional[base.Base]: Retrieved object or None if not found
    """
    result = await session.execute(select(model).filter(model.id == id))
    return result.scalars().first()


@contextlib.asynccontextmanager
async def run_in_transaction(
    session: AsyncSession,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Run operations in a transaction with automatic rollback.
    
    This is useful for test setups where you want to create data
    but not have it affect other tests.
    
    Args:
        session: Database session
        
    Yields:
        AsyncSession: Session for use within the transaction
    """
    # Start a nested transaction
    transaction = await session.begin_nested()
    try:
        yield session
    finally:
        # Always roll back the transaction
        await transaction.rollback()


async def cleanup_table(session: AsyncSession, model: Type[base.Base]) -> None:
    """
    Delete all records from a table.
    
    Args:
        session: Database session
        model: Model class to clean up
    """
    await session.execute(model.__table__.delete())
    await session.commit()
