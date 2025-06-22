from typing import Any, Dict, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from agent_management_service.config import settings
from agent_management_service.crud import agents as agent_crud
from agent_management_service.db import get_db
from agent_management_service.dependencies import get_current_user_id
from agent_management_service.schemas.agent import (
    Agent,
    AgentCreate,
    AgentStatus,
    AgentUpdate,
)

router = APIRouter()


class LangflowFlow(BaseModel):
    """Schema for Langflow flow JSON payload."""

    data: Dict[str, Any] = Field(..., description="Langflow flow configuration")
    name: str = Field(..., description="Flow name")
    description: Optional[str] = Field(None, description="Flow description")
    id: Optional[str] = Field(None, description="Flow ID in Langflow")


class LangflowImportResponse(BaseModel):
    """Response schema for imported Langflow flow."""

    agent_id: UUID = Field(..., description="ID of the created or updated agent")
    name: str = Field(..., description="Name of the agent")
    message: str = Field(..., description="Success message")
    status: str = Field(..., description="Status of the import operation")


async def validate_langflow_instance():
    """
    Check if the configured Langflow instance is reachable.

    Raises:
        HTTPException: If Langflow instance is not configured or unreachable
    """
    if not settings.LANGFLOW_API_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Langflow integration is not configured",
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.LANGFLOW_API_URL.rstrip('/')}/health", timeout=5.0
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Langflow instance is not available",
            )
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to Langflow instance: {str(e)}",
        )


@router.post(
    "/import",
    response_model=LangflowImportResponse,
    summary="Import Langflow flow",
    description="Import a Langflow flow configuration as a new agent or update an existing one.",
)
async def import_langflow_flow(
    flow: LangflowFlow,
    agent_id: Optional[UUID] = Query(
        None, description="ID of an existing agent to update"
    ),
    create_version: bool = Query(
        True,
        description="Whether to create a new version when updating an existing agent",
    ),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Import a Langflow flow configuration as a new agent or update an existing one.

    If agent_id is provided, update that agent. Otherwise, create a new one.
    """
    # Check if Langflow is available
    await validate_langflow_instance()

    # Set up the agent configuration from the flow data
    agent_config = {"langflow_data": flow.data, "source": "langflow_import"}

    if agent_id:
        # Update existing agent
        try:
            agent = await agent_crud.get_agent(db, agent_id, user_id)

            # Prepare update data
            agent_update = AgentUpdate(
                name=flow.name, description=flow.description, config=agent_config
            )

            # Update the agent
            updated_agent = await agent_crud.update_agent(
                db, agent_id, agent_update, user_id, create_version=create_version
            )

            return LangflowImportResponse(
                agent_id=updated_agent.id,
                name=updated_agent.name,
                message="Agent updated successfully from Langflow flow",
                status="success",
            )

        except HTTPException as e:
            if e.status_code == 404:
                # Agent not found, fall through to create a new one
                pass
            else:
                raise

    # Create new agent
    agent_create = AgentCreate(
        name=flow.name,
        description=flow.description or f"Imported from Langflow: {flow.name}",
        config=agent_config,
        status=AgentStatus.DRAFT,
    )

    # Check for name conflicts
    existing_agent = await agent_crud.get_agent_by_name(db, flow.name, user_id)
    if existing_agent:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent with name '{flow.name}' already exists",
        )

    # Create new agent
    new_agent = await agent_crud.create_agent(db, agent_create, user_id)

    return LangflowImportResponse(
        agent_id=new_agent.id,
        name=new_agent.name,
        message="New agent created from Langflow flow",
        status="success",
    )


@router.get(
    "/export/{agent_id}",
    response_model=LangflowFlow,
    summary="Export agent to Langflow",
    description="Export an agent's configuration as a Langflow flow.",
)
async def export_agent_to_langflow(
    agent_id: UUID,
    version_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Export an agent's configuration as a Langflow flow.

    If version_id is provided, export that specific version.
    Otherwise, export the latest version (for draft agents) or
    active version (for published agents).
    """
    # Check if Langflow is available
    await validate_langflow_instance()

    # Get the agent
    agent = await agent_crud.get_agent(db, agent_id, user_id)

    # Determine which configuration to use
    if version_id:
        # Use specific version
        version = await version_crud.get_agent_version(db, version_id, user_id)
        config = version.config_snapshot
    elif agent.active_version_id and agent.status == AgentStatus.PUBLISHED:
        # For published agents, use active version
        version = await version_crud.get_agent_version(
            db, agent.active_version_id, user_id
        )
        config = version.config_snapshot
    else:
        # For draft/other agents, use current config
        config = agent.config

    # Extract Langflow data from config
    flow_data = config.get("langflow_data", {})

    # If no Langflow data is present, return an error
    if not flow_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Agent does not contain valid Langflow configuration",
        )

    return LangflowFlow(
        data=flow_data, name=agent.name, description=agent.description, id=str(agent_id)
    )


@router.post(
    "/sync/{agent_id}",
    response_model=Agent,
    summary="Sync agent with Langflow",
    description="Synchronize an existing agent with Langflow, updating its configuration.",
)
async def sync_agent_with_langflow(
    agent_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Synchronize an existing agent with Langflow, updating its configuration.

    This endpoint is used when changes are made in Langflow and need to be
    saved back to the agent in our system.
    """
    # Check if Langflow is available
    await validate_langflow_instance()

    # Get the agent
    agent = await agent_crud.get_agent(db, agent_id, user_id)

    # Get Langflow flow ID from the agent's config
    flow_id = agent.config.get("langflow_data", {}).get("id")
    if not flow_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Agent does not have an associated Langflow flow ID",
        )

    try:
        # Fetch the latest flow data from Langflow
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.LANGFLOW_API_URL.rstrip('/')}/flows/{flow_id}", timeout=10.0
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to fetch flow from Langflow: HTTP {response.status_code}",
                )

            flow_data = response.json().get("data", {})

            if not flow_data:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Received invalid flow data from Langflow",
                )

            # Update agent's config
            updated_config = agent.config.copy()
            updated_config["langflow_data"] = flow_data
            updated_config["last_synced"] = datetime.utcnow().isoformat()

            # Prepare update data
            agent_update = AgentUpdate(config=updated_config)

            # Update the agent
            updated_agent = await agent_crud.update_agent(
                db, agent_id, agent_update, user_id, create_version=True
            )

            return updated_agent

    except (httpx.ConnectError, httpx.TimeoutException) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Langflow: {str(e)}",
        )


# Import required modules at the end to avoid circular imports
from datetime import datetime

from agent_management_service.crud import versions as version_crud
