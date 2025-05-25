from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.security import get_current_user_id
from app.db.crud_tools import create_tool as crud_create_tool
from app.db.crud_tools import delete_tool as crud_delete_tool
from app.db.crud_tools import get_all_tools_by_user as crud_get_all_tools
from app.db.crud_tools import get_tool_by_id as crud_get_tool_by_id
from app.db.crud_tools import update_tool as crud_update_tool
from app.models.tool import ToolCreate, ToolResponse, ToolUpdate

router = APIRouter()

@router.get("/health", tags=["tools"])
async def tools_health_check() -> dict:
    """Health check for tools router."""
    return {"status": "tools healthy"}

@router.post(
    "/",
    response_model=ToolResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["tools"],
)
async def create_tool(
    tool_create: ToolCreate,
    user_id: int = Depends(get_current_user_id),
) -> ToolResponse:
    """Create a new tool for the current user."""
    return await crud_create_tool(user_id, tool_create)

@router.get(
    "/",
    response_model=List[ToolResponse],
    tags=["tools"],
)
async def list_tools(
    user_id: int = Depends(get_current_user_id),
) -> List[ToolResponse]:
    """List all tools belonging to the current user."""
    return await crud_get_all_tools(user_id)

@router.get(
    "/{tool_id}",
    response_model=ToolResponse,
    tags=["tools"],
)
async def get_tool(
    tool_id: int,
    user_id: int = Depends(get_current_user_id),
) -> ToolResponse:
    """Retrieve a single tool by ID, enforcing access control."""
    tool = await crud_get_tool_by_id(tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    if tool.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return tool

@router.put(
    "/{tool_id}",
    response_model=ToolResponse,
    tags=["tools"],
)
async def update_tool(
    tool_id: int,
    tool_update: ToolUpdate,
    user_id: int = Depends(get_current_user_id),
) -> ToolResponse:
    """Update an existing tool for the current user."""
    existing = await crud_get_tool_by_id(tool_id)
    if not existing or existing.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found or unauthorized")
    updated = await crud_update_tool(tool_id, tool_update)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool update failed")
    return updated

@router.delete(
    "/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["tools"],
)
async def delete_tool(
    tool_id: int,
    user_id: int = Depends(get_current_user_id),
) -> Response:
    """Delete an existing tool for the current user."""
    existing = await crud_get_tool_by_id(tool_id)
    if not existing or existing.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found or unauthorized")
    await crud_delete_tool(tool_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT) 