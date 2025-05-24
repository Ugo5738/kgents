from typing import Any, Dict, Optional

from pydantic import BaseModel


class ToolCreate(BaseModel):
    """Schema for creating a new tool."""
    name: str
    description: Optional[str]
    tool_type: str
    definition: Dict[str, Any]


class ToolUpdate(BaseModel):
    """Schema for updating an existing tool."""
    name: Optional[str] = None
    description: Optional[str] = None
    tool_type: Optional[str] = None
    definition: Optional[Dict[str, Any]] = None


class ToolResponse(BaseModel):
    """Schema for tool data returned in responses."""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    tool_type: str
    definition: Dict[str, Any]

    class Config:
        orm_mode = True 