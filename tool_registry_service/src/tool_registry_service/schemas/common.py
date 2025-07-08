"""
Common schema definitions for the Tool Registry Service.

This module defines shared Pydantic schemas used throughout the service,
including pagination, response formats, and base models.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Generic type for paginated responses
T = TypeVar("T")


class Message(BaseModel):
    """Schema for simple message responses."""
    detail: str


class PaginationParams(BaseModel):
    """Schema for pagination request parameters."""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    size: int = Field(default=100, ge=1, le=500, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic schema for paginated responses.
    
    This schema is used for all endpoints that return a paginated list of items.
    It includes metadata about the pagination state and the items themselves.
    """
    # The actual data items
    items: List[T]
    
    # Pagination metadata
    total: int = Field(..., description="Total number of items across all pages")
    page: int = Field(..., description="Current page number (1-indexed)")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
    
    # Navigation links
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    next_page: Optional[int] = Field(None, description="Next page number if available")
    prev_page: Optional[int] = Field(None, description="Previous page number if available")
    
    @field_validator("pages", mode="before")
    def calculate_pages(cls, v: Optional[int], values: Dict[str, Any]) -> int:
        """Calculate total pages if not provided."""
        if v is not None:
            return v
            
        total = values.data.get("total", 0)
        size = values.data.get("size", 1)
        return max(1, (total + size - 1) // size)
        
    @field_validator("has_next", mode="before")
    def calculate_has_next(cls, v: Optional[bool], values: Dict[str, Any]) -> bool:
        """Determine if there's a next page based on current page and total pages."""
        if v is not None:
            return v
            
        page = values.data.get("page", 1)
        pages = values.data.get("pages", 1)
        return page < pages
        
    @field_validator("has_prev", mode="before")
    def calculate_has_prev(cls, v: Optional[bool], values: Dict[str, Any]) -> bool:
        """Determine if there's a previous page based on current page."""
        if v is not None:
            return v
            
        page = values.data.get("page", 1)
        return page > 1
        
    @field_validator("next_page", mode="before")
    def calculate_next_page(cls, v: Optional[int], values: Dict[str, Any]) -> Optional[int]:
        """Calculate the next page number if it exists."""
        if v is not None:
            return v
            
        has_next = values.data.get("has_next", False)
        page = values.data.get("page", 1)
        return page + 1 if has_next else None
        
    @field_validator("prev_page", mode="before")
    def calculate_prev_page(cls, v: Optional[int], values: Dict[str, Any]) -> Optional[int]:
        """Calculate the previous page number if it exists."""
        if v is not None:
            return v
            
        has_prev = values.data.get("has_prev", False)
        page = values.data.get("page", 1)
        return page - 1 if has_prev else None
