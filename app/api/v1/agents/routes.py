from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.security import get_current_user_id
from app.db.crud_agents import create_agent as crud_create_agent
from app.db.crud_agents import delete_agent as crud_delete_agent
from app.db.crud_agents import get_agent_by_id as crud_get_agent_by_id
from app.db.crud_agents import get_all_agents_by_user as crud_get_all_agents
from app.db.crud_agents import update_agent as crud_update_agent
from app.models.agent import AgentCreate, AgentResponse, AgentUpdate

router = APIRouter()

@router.get("/health", tags=["agents"])
async def agents_health_check() -> dict:
    """Health check for agents router."""
    return {"status": "agents healthy"}

@router.post(
    "/",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["agents"],
)
async def create_agent(
    agent_create: AgentCreate,
    user_id: int = Depends(get_current_user_id),
) -> AgentResponse:
    """Create a new agent for the current user."""
    return await crud_create_agent(user_id, agent_create)

@router.get(
    "/",
    response_model=List[AgentResponse],
    tags=["agents"],
)
async def list_agents(
    user_id: int = Depends(get_current_user_id),
) -> List[AgentResponse]:
    """List all agents belonging to the current user."""
    return await crud_get_all_agents(user_id)

@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    tags=["agents"],
)
async def get_agent(
    agent_id: int,
    user_id: int = Depends(get_current_user_id),
) -> AgentResponse:
    """Retrieve a single agent by ID, enforcing access control."""
    agent = await crud_get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return agent

@router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    tags=["agents"],
)
async def update_agent(
    agent_id: int,
    agent_update: AgentUpdate,
    user_id: int = Depends(get_current_user_id),
) -> AgentResponse:
    """Update an existing agent for the current user."""
    existing = await crud_get_agent_by_id(agent_id)
    if not existing or existing.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found or unauthorized")
    updated = await crud_update_agent(agent_id, agent_update)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent update failed")
    return updated

@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["agents"],
)
async def delete_agent(
    agent_id: int,
    user_id: int = Depends(get_current_user_id),
) -> Response:
    """Delete an existing agent for the current user."""
    existing = await crud_get_agent_by_id(agent_id)
    if not existing or existing.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found or unauthorized")
    await crud_delete_agent(agent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT) 