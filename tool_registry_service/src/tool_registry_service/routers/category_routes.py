"""
API routes for tool categories.

This module defines FastAPI routes for managing tool categories.
Only admins can create, update, and delete categories.
"""

from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud import tool_categories as crud
from ..db import get_db
from ..dependencies.user_deps import get_current_user_id, require_admin_user
from ..logging_config import logger
from ..schemas.common import Message, PaginatedResponse
from ..schemas.tool import ToolCategoryCreate, ToolCategoryResponse, ToolCategoryUpdate

# All routes in this file are for administrative purposes and are protected.
# The `require_admin_user` dependency is applied to the entire router.
router = APIRouter(
    prefix="/categories",
    tags=["tool categories"],
    dependencies=[Depends(require_admin_user)],
    responses={401: {"model": Message}, 403: {"model": Message}},
)


@router.post(
    "/",
    response_model=ToolCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tool category",
    description="Create a new tool category (admin only)",
)
async def create_category(
    category: ToolCategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new tool category (admin only).
    """

    return await crud.create_tool_category(db, category)


@router.get(
    "/",
    response_model=PaginatedResponse[ToolCategoryResponse],
    summary="List tool categories",
    description="List all tool categories with pagination",
)
async def list_categories(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=500, description="Page size"),
    name: str = Query(None, description="Filter by name (case-insensitive)"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all tool categories with pagination and optional filtering.

    This endpoint is public and doesn't require authentication.
    """
    categories, count = await crud.list_tool_categories(
        db, page=page, page_size=size, name_filter=name
    )

    return PaginatedResponse(
        items=categories,
        total=count,
        page=page,
        size=size,
    )


@router.get(
    "/{category_id}",
    response_model=ToolCategoryResponse,
    summary="Get tool category",
    description="Get a specific tool category by ID",
)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific tool category by ID.

    This endpoint is public and doesn't require authentication.
    """
    return await crud.get_tool_category(db, category_id)


@router.patch(
    "/{category_id}",
    response_model=ToolCategoryResponse,
    summary="Update tool category",
    description="Update an existing tool category (admin only)",
)
async def update_category(
    category_id: UUID,
    category: ToolCategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing tool category (admin only).
    """

    return await crud.update_tool_category(db, category_id, category)


@router.delete(
    "/{category_id}",
    response_model=Message,
    summary="Delete tool category",
    description="Delete a tool category (admin only)",
)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a tool category (admin only).
    """

    await crud.delete_tool_category(db, category_id)

    return Message(detail=f"Tool category {category_id} deleted successfully")
