# agent_deployment_service/src/agent_deployment_service/schemas/deployment_schemas.py
"""
Pydantic schemas for agent deployment data models.

These schemas define the data structures for API requests and responses
related to agent deployments.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agent_deployment_service.models.deployment import DeploymentStatus


class DeploymentCreate(BaseModel):
    """Schema for creating a new deployment request."""

    agent_id: UUID = Field(..., description="The ID of the agent to deploy.")
    agent_version_id: UUID = Field(
        ..., description="The specific version ID of the agent to deploy."
    )
    deploy_real_agent: bool = Field(
        True,
        description=(
            "If true, deploy with the real Langflow agent Dockerfile template; "
            "otherwise use the lightweight test template."
        ),
    )


class DeploymentUpdate(BaseModel):
    """
    Schema for updating a deployment. Primarily used internally by the orchestration service
    to update status and metadata.
    """

    status: Optional[DeploymentStatus] = Field(
        None, description="The new status of the deployment."
    )
    endpoint_url: Optional[str] = Field(
        None, description="The URL of the running agent service."
    )
    deployment_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Platform-specific metadata (e.g., pod name)."
    )
    error_message: Optional[str] = Field(
        None, description="Error details if the deployment failed."
    )
    deploy_real_agent: Optional[bool] = Field(
        None,
        description=(
            "Optionally toggle to deploy the real Langflow agent template. "
            "If omitted, the existing setting is unchanged."
        ),
    )


class DeploymentResponse(BaseModel):
    """Schema for returning deployment details in API responses."""

    id: UUID
    agent_id: UUID
    agent_version_id: UUID
    user_id: UUID
    status: DeploymentStatus
    endpoint_url: Optional[str] = None
    deployment_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    deploy_real_agent: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeploymentListResponse(BaseModel):
    """Response schema for a list of deployments."""

    items: List[DeploymentResponse]
    total: int
