"""
CRUD operations for agents table in Supabase.
"""

from typing import List, Optional

from supabase import Client

from app.db.supabase_client import get_supabase_client
from app.models.agent import AgentCreate, AgentResponse, AgentUpdate


async def create_agent(user_id: int, agent_create: AgentCreate) -> AgentResponse:
    """
    Create a new agent for a given user.
    """
    client: Client = await get_supabase_client()
    agent_data = {
        "user_id": user_id,
        "name": agent_create.name,
        "description": agent_create.description,
        "langflow_flow_json": agent_create.langflow_flow_json,
    }
    response = client.table("agents").insert(agent_data).execute()
    created = response.data[0]
    return AgentResponse(**created)


async def get_agent_by_id(agent_id: int) -> Optional[AgentResponse]:
    """
    Retrieve an agent by its ID.
    """
    client: Client = await get_supabase_client()
    response = (
        client.table("agents")
        .select("*")
        .eq("id", agent_id)
        .execute()
    )
    data = response.data or []
    if not data:
        return None
    return AgentResponse(**data[0])


async def get_all_agents_by_user(user_id: int) -> List[AgentResponse]:
    """
    List all agents belonging to a user.
    """
    client: Client = await get_supabase_client()
    response = (
        client.table("agents")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return [AgentResponse(**item) for item in response.data or []]


async def update_agent(agent_id: int, agent_update: AgentUpdate) -> Optional[AgentResponse]:
    """
    Update an existing agent's details.
    """
    client: Client = await get_supabase_client()
    update_data = agent_update.dict(exclude_unset=True)
    response = (
        client.table("agents")
        .update(update_data)
        .eq("id", agent_id)
        .execute()
    )
    data = response.data or []
    if not data:
        return None
    return AgentResponse(**data[0])


async def delete_agent(agent_id: int) -> None:
    """
    Delete an agent by its ID.
    """
    client: Client = await get_supabase_client()
    client.table("agents").delete().eq("id", agent_id).execute() 