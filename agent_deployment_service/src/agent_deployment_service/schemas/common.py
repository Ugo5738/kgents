# agent_deployment_service/src/agent_deployment_service/schemas/common.py
"""
Common Pydantic schemas used across the Agent Deployment Service.
"""
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

# Generic type for paginated response items
T = TypeVar("T")


class MessageResponse(BaseModel):
    """A standard response for simple messages (e.g., success or error details)."""

    detail: str


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic schema for paginated API responses."""

    items: List[T]
    total: int = Field(..., description="Total number of items available.")
    page: int = Field(..., description="Current page number.")
    size: int = Field(..., description="Number of items per page.")
    pages: int = Field(..., description="Total number of pages.")
    has_next: bool = Field(..., description="Indicates if there is a next page.")
    has_prev: bool = Field(..., description="Indicates if there is a previous page.")
    next_page: Optional[int] = Field(None, description="The number of the next page.")
    prev_page: Optional[int] = Field(
        None, description="The number of the previous page."
    )
