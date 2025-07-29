"""
CRUD operations for tool categories.

This module provides database operations for creating, reading,
updating, and deleting tool categories.
"""

import logging
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..logging_config import logger
from ..models.tool import ToolCategory
from ..schemas.tool import ToolCategoryCreate, ToolCategoryUpdate


async def create_tool_category(
    db: AsyncSession, category_data: ToolCategoryCreate
) -> ToolCategory:
    """
    Create a new tool category.

    Args:
        db: Database session
        category_data: Tool category data

    Returns:
        Created ToolCategory instance

    Raises:
        HTTPException: If a category with the same name already exists
    """
    # Check if a category with the same name already exists
    existing_category = await db.execute(
        select(ToolCategory).where(
            func.lower(ToolCategory.name) == func.lower(category_data.name)
        )
    )
    if existing_category.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with name '{category_data.name}' already exists",
        )

    # Create new category
    category = ToolCategory(**category_data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)

    logger.info(f"Created tool category: {category.name} (ID: {category.id})")
    return category


async def get_tool_category(db: AsyncSession, category_id: UUID) -> ToolCategory:
    """
    Get a tool category by ID.

    Args:
        db: Database session
        category_id: Tool category ID

    Returns:
        ToolCategory instance

    Raises:
        HTTPException: If the category is not found
    """
    category = await db.execute(
        select(ToolCategory).where(ToolCategory.id == category_id)
    )
    category = category.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool category with ID {category_id} not found",
        )

    return category


async def list_tool_categories(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 100,
    name_filter: Optional[str] = None,
) -> Tuple[List[ToolCategory], int]:
    """
    List tool categories with pagination and optional filtering.

    Args:
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of items per page
        name_filter: Optional filter by name (case-insensitive partial match)

    Returns:
        Tuple of (list of ToolCategory instances, total count)
    """
    # Calculate offset for pagination
    offset = (page - 1) * page_size

    # Build query
    query = select(ToolCategory)

    # Apply name filter if provided
    if name_filter:
        query = query.where(ToolCategory.name.ilike(f"%{name_filter}%"))

    # Order by display_order, then by name
    query = query.order_by(ToolCategory.display_order, ToolCategory.name)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.execute(count_query)
    total_count = total_count.scalar_one()

    # Apply pagination
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    categories = result.scalars().all()

    return categories, total_count


async def update_tool_category(
    db: AsyncSession,
    category_id: UUID,
    category_data: ToolCategoryUpdate,
) -> ToolCategory:
    """
    Update a tool category.

    Args:
        db: Database session
        category_id: Tool category ID
        category_data: Updated tool category data

    Returns:
        Updated ToolCategory instance

    Raises:
        HTTPException: If the category is not found or name is already used
    """
    # Get existing category
    category = await get_tool_category(db, category_id)

    # Check for duplicate name if name is being updated
    if category_data.name is not None and category_data.name != category.name:
        name_check = await db.execute(
            select(ToolCategory).where(
                func.lower(ToolCategory.name) == func.lower(category_data.name)
            )
        )
        if name_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category with name '{category_data.name}' already exists",
            )

    # Update fields
    update_data = category_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    # Save changes
    await db.commit()
    await db.refresh(category)

    logger.info(f"Updated tool category: {category.name} (ID: {category.id})")
    return category


async def delete_tool_category(
    db: AsyncSession,
    category_id: UUID,
) -> None:
    """
    Delete a tool category.

    Args:
        db: Database session
        category_id: Tool category ID

    Raises:
        HTTPException: If the category is not found
    """
    # Get existing category
    category = await get_tool_category(db, category_id)

    # Delete category
    await db.delete(category)
    await db.commit()

    logger.info(f"Deleted tool category: {category.name} (ID: {category.id})")
