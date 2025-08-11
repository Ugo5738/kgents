"""
CRUD operations for tools.

This module provides database operations for creating, reading,
updating, and deleting tools.
"""

from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..logging_config import logger
from ..models.tool import Tool, ToolCategory
from ..schemas.tool import ToolCreate, ToolSearchParams, ToolUpdate


async def create_tool(db: AsyncSession, tool_data: ToolCreate, owner_id: UUID) -> Tool:
    """
    Create a new tool.

    Args:
        db: Database session
        tool_data: Tool data
        owner_id: Owner's user ID

    Returns:
        Created Tool instance

    Raises:
        HTTPException: If a tool with the same name and version already exists for this owner
    """
    # Check if a tool with the same name and version already exists for this owner
    existing_tool = await db.execute(
        select(Tool).where(
            and_(
                Tool.name == tool_data.name,
                Tool.version == tool_data.version,
                Tool.owner_id == owner_id,
            )
        )
    )
    if existing_tool.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tool '{tool_data.name}' version {tool_data.version} already exists",
        )

    # Validate category_id if provided
    if tool_data.category_id:
        category = await db.execute(
            select(ToolCategory).where(ToolCategory.id == tool_data.category_id)
        )
        if not category.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with ID {tool_data.category_id} not found",
            )

    # Create new tool with owner_id
    tool_dict = tool_data.model_dump(exclude_unset=True)
    # Map schema field 'metadata' to ORM attribute 'metadata_json'
    if "metadata" in tool_dict:
        tool_dict["metadata_json"] = tool_dict.pop("metadata")

    tool = Tool(owner_id=owner_id, **tool_dict)

    db.add(tool)
    await db.commit()
    await db.refresh(tool)

    logger.info(f"Created tool: {tool.name} v{tool.version} (ID: {tool.id})")
    return tool


async def get_tool(
    db: AsyncSession,
    tool_id: UUID,
    check_ownership: bool = True,
    owner_id: Optional[UUID] = None,
) -> Tool:
    """
    Get a tool by ID with optional ownership check.

    Args:
        db: Database session
        tool_id: Tool ID
        check_ownership: Whether to verify the owner_id matches
        owner_id: Owner's user ID (required if check_ownership is True)

    Returns:
        Tool instance

    Raises:
        HTTPException: If the tool is not found or ownership check fails
        ValueError: If check_ownership is True but owner_id is None
    """
    if check_ownership and owner_id is None:
        raise ValueError("owner_id is required when check_ownership is True")

    # Get tool with category relationship loaded
    tool = await db.execute(
        select(Tool).options(joinedload(Tool.category)).where(Tool.id == tool_id)
    )
    tool = tool.unique().scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool with ID {tool_id} not found",
        )

    # Check ownership if required
    if check_ownership and tool.owner_id != owner_id:
        # Allow access to public tools regardless of ownership
        if not tool.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this tool",
            )

    return tool


async def list_tools(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 100,
    search_params: Optional[ToolSearchParams] = None,
    owner_id: Optional[UUID] = None,
    include_all_public: bool = True,
) -> Tuple[List[Tool], int]:
    """
    List tools with pagination and optional filtering.

    Args:
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of items per page
        search_params: Optional search parameters
        owner_id: If provided, includes tools owned by this user
        include_all_public: Whether to include all public tools

    Returns:
        Tuple of (list of Tool instances, total count)
    """
    # Calculate offset for pagination
    offset = (page - 1) * page_size

    # Start building query
    query = select(Tool).options(joinedload(Tool.category))

    # Build ownership/visibility filter
    ownership_filters = []

    # Include tools owned by the user if owner_id is provided
    if owner_id:
        ownership_filters.append(Tool.owner_id == owner_id)

    # Include all public tools if requested
    if include_all_public:
        ownership_filters.append(Tool.is_public == True)

    # Combine ownership filters with OR
    if ownership_filters:
        query = query.where(or_(*ownership_filters))

    # Apply search filters if provided
    if search_params:
        if search_params.query:
            # Full text search on name and description
            search_term = f"%{search_params.query}%"
            query = query.where(
                or_(Tool.name.ilike(search_term), Tool.description.ilike(search_term))
            )

        if search_params.tool_type:
            query = query.where(Tool.tool_type == search_params.tool_type)

        if search_params.category_id:
            query = query.where(Tool.category_id == search_params.category_id)

        if search_params.is_public is not None:
            query = query.where(Tool.is_public == search_params.is_public)

        if search_params.tags:
            # Find tools that have ANY of the specified tags
            for tag in search_params.tags:
                query = query.where(Tool.tags.contains([tag]))

    # Order by updated_at (most recent first), then name
    query = query.order_by(Tool.updated_at.desc(), Tool.name)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.execute(count_query)
    total_count = total_count.scalar_one()

    # Apply pagination
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    tools = result.unique().scalars().all()

    return tools, total_count


async def update_tool(
    db: AsyncSession,
    tool_id: UUID,
    tool_data: ToolUpdate,
    owner_id: UUID,
    is_admin: bool = False,
) -> Tool:
    """
    Update a tool.

    Args:
        db: Database session
        tool_id: Tool ID
        tool_data: Updated tool data
        owner_id: Owner's user ID
        is_admin: Whether the user is an admin (can update any tool)

    Returns:
        Updated Tool instance

    Raises:
        HTTPException: If the tool is not found or user doesn't have permission
    """
    # Get existing tool
    tool = await get_tool(db, tool_id, check_ownership=not is_admin, owner_id=owner_id)

    # If name or version is changing, check for duplicates
    if (tool_data.name is not None and tool_data.name != tool.name) or (
        tool_data.version is not None and tool_data.version != tool.version
    ):

        new_name = tool_data.name or tool.name
        new_version = tool_data.version or tool.version

        duplicate_check = await db.execute(
            select(Tool).where(
                and_(
                    Tool.name == new_name,
                    Tool.version == new_version,
                    Tool.owner_id == owner_id,
                    Tool.id != tool_id,
                )
            )
        )

        if duplicate_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tool '{new_name}' version {new_version} already exists",
            )

    # Check if category_id is valid if provided
    if tool_data.category_id is not None:
        category = await db.execute(
            select(ToolCategory).where(ToolCategory.id == tool_data.category_id)
        )
        if not category.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with ID {tool_data.category_id} not found",
            )

    # Update fields
    update_data = tool_data.model_dump(exclude_unset=True)
    # Map schema field 'metadata' to ORM attribute 'metadata_json'
    if "metadata" in update_data:
        update_data["metadata_json"] = update_data.pop("metadata")

    for key, value in update_data.items():
        setattr(tool, key, value)

    # Save changes
    await db.commit()
    await db.refresh(tool)

    logger.info(f"Updated tool: {tool.name} v{tool.version} (ID: {tool.id})")
    return tool


async def delete_tool(
    db: AsyncSession,
    tool_id: UUID,
    owner_id: UUID,
    is_admin: bool = False,
) -> None:
    """
    Delete a tool.

    Args:
        db: Database session
        tool_id: Tool ID
        owner_id: Owner's user ID
        is_admin: Whether the user is an admin (can delete any tool)

    Raises:
        HTTPException: If the tool is not found or user doesn't have permission
    """
    # Get existing tool with ownership check
    tool = await get_tool(db, tool_id, check_ownership=not is_admin, owner_id=owner_id)

    # Delete tool
    await db.delete(tool)
    await db.commit()

    logger.info(f"Deleted tool: {tool.name} v{tool.version} (ID: {tool.id})")


async def approve_tool(
    db: AsyncSession,
    tool_id: UUID,
    approved: bool = True,
) -> Tool:
    """
    Approve or reject a tool (admin only).

    Args:
        db: Database session
        tool_id: Tool ID
        approved: Whether to approve (True) or reject (False) the tool

    Returns:
        Updated Tool instance

    Raises:
        HTTPException: If the tool is not found
    """
    # Get tool without ownership check (admin function)
    tool = await get_tool(db, tool_id, check_ownership=False)

    # Update approval status
    tool.is_approved = approved

    # Save changes
    await db.commit()
    await db.refresh(tool)

    status_str = "approved" if approved else "rejected"
    logger.info(f"Tool {tool.id} {status_str} by admin")

    return tool
