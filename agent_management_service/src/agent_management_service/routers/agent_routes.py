from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent_management_service.crud import agents as agent_crud
from agent_management_service.db import get_db
from agent_management_service.dependencies import get_current_user_id
from agent_management_service.models.agent import AgentStatus as AgentStatusEnum
from agent_management_service.schemas.agent import (
    Agent, 
    AgentCreate, 
    AgentStatus, 
    AgentUpdate, 
    AgentWithVersions
)
from agent_management_service.schemas.common import PaginatedResponse, StatusMessage

router = APIRouter()


@router.post(
    "/", 
    response_model=Agent, 
    status_code=status.HTTP_201_CREATED,
    summary="Create a new agent",
    description="Create a new agent with the given configuration. The agent will be owned by the current user."
)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Create a new agent."""
    # Check if agent with the same name exists for this user
    existing_agent = await agent_crud.get_agent_by_name(db, agent_data.name, user_id)
    if existing_agent:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent with name '{agent_data.name}' already exists"
        )
    
    return await agent_crud.create_agent(db, agent_data, user_id)


@router.get(
    "/", 
    response_model=PaginatedResponse[Agent],
    summary="List agents",
    description="List all agents owned by the current user with pagination support."
)
async def list_agents(
    status: Optional[AgentStatus] = Query(None, description="Filter by agent status"),
    skip: int = Query(0, ge=0, description="Number of agents to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of agents to return"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """List all agents owned by the current user."""
    agents, total = await agent_crud.get_agents(
        db, 
        user_id, 
        skip=skip, 
        limit=limit,
        status=status
    )
    
    # Calculate pagination metadata
    pages = (total + limit - 1) // limit  # Ceiling division
    page = skip // limit + 1
    
    return PaginatedResponse(
        items=agents,
        total=total,
        page=page,
        size=limit,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1,
        next_page=page + 1 if page < pages else None,
        prev_page=page - 1 if page > 1 else None
    )


@router.get(
    "/{agent_id}", 
    response_model=Agent,
    summary="Get agent",
    description="Get a specific agent by ID."
)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get a specific agent by ID."""
    return await agent_crud.get_agent(db, agent_id, user_id)


@router.get(
    "/{agent_id}/with-versions", 
    response_model=AgentWithVersions,
    summary="Get agent with versions",
    description="Get a specific agent by ID including its version history."
)
async def get_agent_with_versions(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get a specific agent by ID including its version history."""
    return await agent_crud.get_agent(db, agent_id, user_id, with_versions=True)


@router.patch(
    "/{agent_id}", 
    response_model=Agent,
    summary="Update agent",
    description="Update an existing agent's metadata and configuration."
)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    create_version: bool = Query(True, description="Whether to create a new version when updating configuration"),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Update an existing agent."""
    # If name is being updated, check for name conflicts
    if agent_data.name:
        existing_agent = await agent_crud.get_agent_by_name(db, agent_data.name, user_id)
        if existing_agent and existing_agent.id != agent_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Agent with name '{agent_data.name}' already exists"
            )
    
    return await agent_crud.update_agent(
        db, 
        agent_id, 
        agent_data, 
        user_id,
        create_version=create_version
    )


@router.delete(
    "/{agent_id}", 
    response_model=StatusMessage,
    summary="Delete agent",
    description="Delete an agent and all its versions."
)
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Delete an agent and all its versions."""
    await agent_crud.delete_agent(db, agent_id, user_id)
    return StatusMessage(message=f"Agent with ID {agent_id} deleted successfully")


@router.post(
    "/{agent_id}/publish", 
    response_model=Agent,
    summary="Publish agent",
    description="Publish an agent, making it available for deployment. Optionally specify a version to publish."
)
async def publish_agent(
    agent_id: UUID,
    version_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Publish an agent, making it available for deployment."""
    return await agent_crud.publish_agent(db, agent_id, user_id, version_id)


@router.post(
    "/{agent_id}/archive", 
    response_model=Agent,
    summary="Archive agent",
    description="Archive an agent, preventing it from being deployed."
)
async def archive_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
):
    """Archive an agent, preventing it from being deployed."""
    return await agent_crud.archive_agent(db, agent_id, user_id)
