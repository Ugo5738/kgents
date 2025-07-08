from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


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
