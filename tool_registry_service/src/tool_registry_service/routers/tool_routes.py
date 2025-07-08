"""
API routes for tools management.

This module defines FastAPI routes for managing tools in the registry,
including CRUD operations and search functionality.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from tool_registry_service.crud import tools as crud
from tool_registry_service.db import get_db
from tool_registry_service.dependencies.auth import (
    check_admin_role,
    get_current_user_id,
)
from tool_registry_service.models.tool import ExecutionEnvironment, ToolType
from tool_registry_service.schemas.common import Message, PaginatedResponse
from tool_registry_service.schemas.tool import (
    ToolCreate,
    ToolResponse,
    ToolSearchParams,
    ToolUpdate,
)

router = APIRouter(
    prefix="/tools",
    tags=["tools"],
    responses={401: {"model": Message}},
)

logger = logging.getLogger(__name__)


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

    Users can access:
    - Their own tools
    - Public tools
    - Any tool if they're an admin
    """
    # If user is authenticated, check if they're an admin
    is_admin = False
    if user_id:
        try:
            is_admin = await check_admin_role(None)
        except Exception:
            # If check fails, assume not admin
            pass

    # If admin, can access any tool
    if is_admin:
        return await crud.get_tool(db, tool_id, check_ownership=False)

    # Otherwise, get tool with ownership check
    # If tool is public, non-owners can still access it
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
    is_admin: bool = Depends(check_admin_role),
):
    """
    Update an existing tool.

    Users can only update their own tools.
    Admins can update any tool.
    """
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
    is_admin: bool = Depends(check_admin_role),
):
    """
    Delete a tool.

    Users can only delete their own tools.
    Admins can delete any tool.
    """
    await crud.delete_tool(db, tool_id, owner_id=user_id, is_admin=is_admin)

    return Message(detail=f"Tool {tool_id} deleted successfully")


@router.post(
    "/{tool_id}/approve",
    response_model=ToolResponse,
    summary="Approve tool",
    description="Approve or reject a tool (admin only)",
)
async def approve_tool(
    tool_id: UUID,
    approved: bool = Body(..., description="Whether to approve or reject the tool"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    is_admin: bool = Depends(check_admin_role),
):
    """
    Approve or reject a tool (admin only).
    """
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can approve or reject tools",
        )

    return await crud.approve_tool(db, tool_id, approved)
