"""
CRUD operations for tools table in Supabase.
"""

from typing import List, Optional

from supabase import Client

from app.db.supabase_client import get_supabase_client
from app.models.tool import ToolCreate, ToolResponse, ToolUpdate


async def create_tool(user_id: int, tool_create: ToolCreate) -> ToolResponse:
    """
    Create a new tool for a given user.
    """
    client: Client = await get_supabase_client()
    tool_data = {
        "user_id": user_id,
        "name": tool_create.name,
        "description": tool_create.description,
        "tool_type": tool_create.tool_type,
        "definition": tool_create.definition,
    }
    response = client.table("tools").insert(tool_data).execute()
    created = response.data[0]
    return ToolResponse(**created)


async def get_tool_by_id(tool_id: int) -> Optional[ToolResponse]:
    """
    Retrieve a tool by its ID.
    """
    client: Client = await get_supabase_client()
    response = client.table("tools").select("*").eq("id", tool_id).execute()
    data = response.data or []
    if not data:
        return None
    return ToolResponse(**data[0])


async def get_all_tools_by_user(user_id: int) -> List[ToolResponse]:
    """
    List all tools belonging to a user.
    """
    client: Client = await get_supabase_client()
    response = client.table("tools").select("*").eq("user_id", user_id).execute()
    return [ToolResponse(**item) for item in response.data or []]


async def update_tool(tool_id: int, tool_update: ToolUpdate) -> Optional[ToolResponse]:
    """
    Update an existing tool's details.
    """
    client: Client = await get_supabase_client()
    update_data = tool_update.model_dump(exclude_unset=True)
    response = client.table("tools").update(update_data).eq("id", tool_id).execute()
    data = response.data or []
    if not data:
        return None
    return ToolResponse(**data[0])


async def delete_tool(tool_id: int) -> None:
    """
    Delete a tool by its ID.
    """
    client: Client = await get_supabase_client()
    client.table("tools").delete().eq("id", tool_id).execute()
