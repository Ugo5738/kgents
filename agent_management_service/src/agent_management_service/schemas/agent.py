from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentStatus(str, Enum):
    """Possible states for an agent."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AgentBase(BaseModel):
    """Base schema with shared agent attributes."""
    name: str = Field(..., description="Name of the agent", max_length=255)
    description: Optional[str] = Field(None, description="Optional description of the agent")
    tags: Optional[List[str]] = Field(
        default=None, 
        description="Optional tags for categorizing the agent"
    )
    config: Dict[str, Any] = Field(
        ..., 
        description="Langflow configuration for the agent"
    )


class AgentCreate(AgentBase):
    """Schema for creating a new agent."""
    status: AgentStatus = Field(default=AgentStatus.DRAFT, description="Initial status of the agent")


class AgentUpdate(BaseModel):
    """Schema for updating an existing agent."""
    name: Optional[str] = Field(None, description="Updated name of the agent", max_length=255)
    description: Optional[str] = Field(None, description="Updated description of the agent")
    tags: Optional[List[str]] = Field(None, description="Updated tags for categorizing the agent")
    config: Optional[Dict[str, Any]] = Field(None, description="Updated Langflow configuration")
    status: Optional[AgentStatus] = Field(None, description="Updated status of the agent")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Agent Name",
                "description": "This agent has been updated",
                "tags": ["updated", "v2"],
                "status": "published"
            }
        }
    )


class Agent(AgentBase):
    """Schema for agent responses including all fields."""
    id: UUID = Field(..., description="Unique identifier for this agent")
    status: AgentStatus = Field(..., description="Current status of the agent")
    user_id: UUID = Field(..., description="ID of the user who owns this agent")
    created_at: datetime = Field(..., description="Timestamp when the agent was created")
    updated_at: datetime = Field(..., description="Timestamp when the agent was last updated")
    active_version_id: Optional[UUID] = Field(None, description="ID of the currently active version (if published)")
    
    model_config = ConfigDict(from_attributes=True)


class AgentWithVersions(Agent):
    """Schema for agent responses including version history."""
    versions: List["AgentVersion"] = Field(
        default_factory=list, 
        description="Version history of this agent"
    )
    
    model_config = ConfigDict(from_attributes=True)


# Import down here to avoid circular imports
from agent_management_service.schemas.agent_version import AgentVersion  # noqa

# Update the forward ref
AgentWithVersions.model_rebuild()
