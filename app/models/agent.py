from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AgentCreate(BaseModel):
    """Schema for creating a new agent."""
    name: str
    description: Optional[str]
    langflow_flow_json: Dict[str, Any]


class AgentUpdate(BaseModel):
    """Schema for updating an existing agent."""
    name: Optional[str]
    description: Optional[str]
    langflow_flow_json: Optional[Dict[str, Any]]


class AgentResponse(BaseModel):
    """Schema for agent data returned in responses."""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    langflow_flow_json: Dict[str, Any]

    class Config:
        orm_mode = True 