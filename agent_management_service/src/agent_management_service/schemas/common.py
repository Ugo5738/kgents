from enum import Enum
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


class Status(str, Enum):
    """Status enum for API responses."""
    SUCCESS = "success"
    ERROR = "error"


class StatusMessage(BaseModel):
    """Generic status message response model."""
    status: Status = Field(default=Status.SUCCESS)
    message: str


# Generic type for paginated response items
T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response with metadata."""
    items: List[T]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool = Field(description="Whether there are more pages available")
    has_prev: bool = Field(description="Whether there are previous pages available")
    next_page: Optional[int] = Field(description="Next page number if available")
    prev_page: Optional[int] = Field(description="Previous page number if available")
