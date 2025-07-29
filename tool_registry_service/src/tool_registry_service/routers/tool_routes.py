"""
API routes for tools management.

This module defines FastAPI routes for managing tools in the registry,
including CRUD operations and search functionality.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.schemas.user_schemas import UserTokenData
from tool_registry_service.models.tool import ToolType

from ..crud import tools as crud
from ..db import get_db
from ..dependencies.user_deps import (
    get_current_user_id,
    get_current_user_token_data,
    require_admin_user,
)
from ..logging_config import logger
from ..schemas.common import Message, PaginatedResponse
from ..schemas.tool import ToolCreate, ToolResponse, ToolSearchParams, ToolUpdate

router = APIRouter(
    prefix="/tools",
    tags=["tools"],
)

# This dependency ensures a user is authenticated for all routes in this file.
# Public access is handled by passing an optional user_id to the CRUD layer.
router.dependencies.append(Depends(get_current_user_id))


@router.post(
    "/",
    response_model=ToolResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tool",
    description="Create a new tool in the registry",
)
async def create_tool(
    tool: ToolCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Create a new tool in the registry.

    The authenticated user will be set as the tool owner.
    """
    return await crud.create_tool(db, tool, owner_id=user_id)


@router.get(
    "/",
    response_model=PaginatedResponse[ToolResponse],
    summary="List tools",
    description="List tools with filtering and pagination",
)
async def list_tools(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=500, description="Page size"),
    query: Optional[str] = Query(None, description="Text search query"),
    tool_type: Optional[ToolType] = Query(None, description="Filter by tool type"),
    category_id: Optional[UUID] = Query(None, description="Filter by category ID"),
    public: Optional[bool] = Query(None, description="Filter by public/private status"),
    tags: List[str] = Query(None, description="Filter by tags (comma-separated)"),
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    List tools with filtering and pagination.

    Returns both tools owned by the authenticated user and public tools.
    Unauthenticated requests will only see public tools.
    """
    search_params = ToolSearchParams(
        query=query,
        tool_type=tool_type,
        category_id=category_id,
        is_public=public,
        tags=tags,
    )

    # Include all public tools and tools owned by the current user
    tools, count = await crud.list_tools(
        db,
        page=page,
        page_size=size,
        search_params=search_params,
        owner_id=user_id,
        include_all_public=True,
    )

    return PaginatedResponse(
        items=tools,
        total=count,
        page=page,
        size=size,
    )


@router.get(
    "/my",
    response_model=PaginatedResponse[ToolResponse],
    summary="List my tools",
    description="List tools owned by the authenticated user",
)
async def list_my_tools(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=500, description="Page size"),
    query: Optional[str] = Query(None, description="Text search query"),
    tool_type: Optional[ToolType] = Query(None, description="Filter by tool type"),
    category_id: Optional[UUID] = Query(None, description="Filter by category ID"),
    public: Optional[bool] = Query(None, description="Filter by public/private status"),
    tags: List[str] = Query(None, description="Filter by tags (comma-separated)"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    List tools owned by the authenticated user with filtering and pagination.
    """
    search_params = ToolSearchParams(
        query=query,
        tool_type=tool_type,
        category_id=category_id,
        is_public=public,
        tags=tags,
    )

    # Only include tools owned by the current user, not public tools
    tools, count = await crud.list_tools(
        db,
        page=page,
        page_size=size,
        search_params=search_params,
        owner_id=user_id,
        include_all_public=False,  # Only show user's own tools
    )

    return PaginatedResponse(
        items=tools,
        total=count,
        page=page,
        size=size,
    )


@router.get(
    "/{tool_id}",
    response_model=ToolResponse,
    summary="Get tool",
    description="Get a specific tool by ID",
)
async def get_tool(
    tool_id: UUID = Path(..., description="Tool ID"),
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Get a specific tool by ID.
    Access is granted if the user owns the tool or if the tool is public and approved.
    Admins can access any tool.
    """
    # The CRUD function `get_tool` handles the ownership and public access logic.
    return await crud.get_tool(db, tool_id, owner_id=user_id)


@router.patch(
    "/{tool_id}",
    response_model=ToolResponse,
    summary="Update tool",
    description="Update an existing tool",
)
async def update_tool(
    tool_id: UUID,
    tool: ToolUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    token_data: UserTokenData = Depends(get_current_user_token_data),
):
    """Update a tool. Only the owner or an admin can perform this action."""

    is_admin = "admin" in token_data.roles
    return await crud.update_tool(
        db, tool_id, tool, owner_id=user_id, is_admin=is_admin
    )


@router.delete(
    "/{tool_id}",
    response_model=Message,
    summary="Delete tool",
    description="Delete a tool",
)
async def delete_tool(
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    token_data: UserTokenData = Depends(get_current_user_token_data),
):
    """Delete a tool. Only the owner or an admin can perform this action."""
    is_admin = "admin" in token_data.roles
    await crud.delete_tool(db, tool_id, owner_id=user_id, is_admin=is_admin)
    return Message(detail=f"Tool {tool_id} deleted successfully")


@router.post(
    "/{tool_id}/approve",
    response_model=ToolResponse,
    summary="Approve tool (Admin Only)",
    description="Approve or reject a tool (admin only)",
    dependencies=[Depends(require_admin_user)],  # Add admin check here specifically
)
async def approve_tool(
    tool_id: UUID,
    approved: bool = Body(..., description="Whether to approve or reject the tool"),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a tool's public visibility (admin only)."""
    return await crud.approve_tool(db, tool_id, approved)
