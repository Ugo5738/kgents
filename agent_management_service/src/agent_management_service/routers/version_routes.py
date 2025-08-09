from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent_management_service.schemas.agent_version import (
    AgentVersion,
    AgentVersionCreate,
    AgentVersionUpdate,
)
from agent_management_service.schemas.common import PaginatedResponse

from ..crud import agents as agent_crud
from ..crud import versions as version_crud
from ..db import get_db
from ..dependencies import get_current_user_id, get_current_user_token_data

router = APIRouter(
    prefix="/versions",
    tags=["Versions"],
)


@router.post(
    "/",
    response_model=AgentVersion,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new agent version",
    description="Create a new version for the specified agent.",
)
async def create_agent_version(
    user_id: UUID = Depends(get_current_user_id),
    agent_id: UUID = Path(..., description="ID of the agent"),
    version_data: AgentVersionCreate = None,
    db: AsyncSession = Depends(get_db),
):
    """Create a new version for the specified agent."""
    # If no version data provided, create one with minimal information
    if version_data is None:
        # Get the agent to access its current config
        agent = await agent_crud.get_agent(db, agent_id, user_id)

        # Create minimal version data
        version_data = AgentVersionCreate(
            agent_id=agent_id,
            config_snapshot=agent.config,
            change_summary="Manual version creation",
        )
    else:
        # Override agent_id from path parameter if provided in body
        version_data.agent_id = agent_id

    return await version_crud.create_agent_version(db, version_data, user_id)


@router.get(
    "/",
    response_model=PaginatedResponse[AgentVersion],
    summary="List agent versions",
    description="List all versions of the specified agent with pagination support.",
)
async def list_agent_versions(
    user_id: UUID = Depends(get_current_user_id),
    agent_id: UUID = Path(..., description="ID of the agent"),
    skip: int = Query(0, ge=0, description="Number of versions to skip"),
    limit: int = Query(
        100, ge=1, le=100, description="Maximum number of versions to return"
    ),
    db: AsyncSession = Depends(get_db),
):
    """List all versions of the specified agent."""
    versions, total = await version_crud.get_agent_versions(
        db, agent_id, user_id, skip=skip, limit=limit
    )

    # Calculate pagination metadata
    pages = (total + limit - 1) // limit  # Ceiling division
    page = skip // limit + 1

    return PaginatedResponse(
        items=versions,
        total=total,
        page=page,
        size=limit,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1,
        next_page=page + 1 if page < pages else None,
        prev_page=page - 1 if page > 1 else None,
    )


@router.get(
    "/latest",
    response_model=AgentVersion,
    summary="Get latest agent version",
    description="Get the latest version of the specified agent.",
)
async def get_latest_agent_version(
    user_id: UUID = Depends(get_current_user_id),
    agent_id: UUID = Path(..., description="ID of the agent"),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest version of the specified agent."""
    version = await version_crud.get_latest_agent_version(db, agent_id, user_id)
    if not version:
        return {"detail": "No versions found for this agent"}
    return version


@router.get(
    "/{version_id}",
    response_model=AgentVersion,
    summary="Get agent version",
    description="Get a specific version of the agent by its ID.",
)
async def get_agent_version(
    token_data=Depends(get_current_user_token_data),
    agent_id: UUID = Path(..., description="ID of the agent"),
    version_id: UUID = Path(..., description="ID of the version"),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific version of the agent by its ID."""

    # Check if the caller is a service with the system:agents:read permission
    is_service_call = "system:agents:read" in token_data.permissions

    # The user_id is the 'sub' claim, which could be a user's UUID or a client's UUID
    caller_id = token_data.user_id

    version = await version_crud.get_agent_version(
        db, version_id, user_id=caller_id, bypass_ownership_check=is_service_call
    )
    return version


@router.patch(
    "/{version_id}",
    response_model=AgentVersion,
    summary="Update agent version",
    description="Update metadata for a specific version of the agent.",
)
async def update_agent_version(
    version_data: AgentVersionUpdate,
    user_id: UUID = Depends(get_current_user_id),
    agent_id: UUID = Path(..., description="ID of the agent"),
    version_id: UUID = Path(..., description="ID of the version"),
    db: AsyncSession = Depends(get_db),
):
    """Update metadata for a specific version of the agent."""
    # Note: agent_id is not used in the query directly but is needed for the path
    version = await version_crud.update_agent_version(
        db, version_id, version_data, user_id
    )
    return version
