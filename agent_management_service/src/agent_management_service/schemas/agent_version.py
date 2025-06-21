from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentVersionBase(BaseModel):
    """Base schema for agent version."""
    change_summary: Optional[str] = Field(
        None, 
        description="Summary of changes in this version"
    )
    config_snapshot: Dict[str, Any] = Field(
        ..., 
        description="Complete agent configuration for this version"
    )


class AgentVersionCreate(AgentVersionBase):
    """Schema for manually creating a new agent version."""
    agent_id: UUID = Field(..., description="ID of the parent agent")
    version_number: Optional[int] = Field(
        None, 
        description="Version number (auto-assigned if not provided)"
    )


class AgentVersionUpdate(BaseModel):
    """Schema for updating an agent version."""
    change_summary: Optional[str] = Field(
        None, 
        description="Updated summary of changes"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "change_summary": "Fixed bug in conversation handling"
            }
        }
    )


class AgentVersion(AgentVersionBase):
    """Schema for agent version responses."""
    id: UUID = Field(..., description="Unique identifier for this version")
    version_number: int = Field(..., description="Sequential version number")
    agent_id: UUID = Field(..., description="ID of the parent agent")
    user_id: UUID = Field(..., description="ID of the user who created this version")
    created_at: datetime = Field(..., description="Timestamp when this version was created")
    updated_at: datetime = Field(..., description="Timestamp when this version was last updated")
    
    model_config = ConfigDict(from_attributes=True)
