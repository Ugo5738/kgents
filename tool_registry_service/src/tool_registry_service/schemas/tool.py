"""
Tool schemas for the Tool Registry Service.

This module defines Pydantic schemas for API requests and responses
related to tools, tool categories, and tool executions.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tool_registry_service.models.tool import ExecutionEnvironment, ToolType


# Base schemas for tool categories
class ToolCategoryBase(BaseModel):
    """Base schema for tool category data."""

    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    icon: Optional[str] = Field(
        None, description="Icon identifier or URL for the category"
    )
    display_order: int = Field(
        0, description="Display order in UI (lower numbers shown first)"
    )


class ToolCategoryCreate(ToolCategoryBase):
    """Schema for creating a new tool category."""

    pass


class ToolCategoryUpdate(BaseModel):
    """Schema for updating an existing tool category."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Category name"
    )
    description: Optional[str] = Field(None, description="Category description")
    icon: Optional[str] = Field(
        None, description="Icon identifier or URL for the category"
    )
    display_order: Optional[int] = Field(None, description="Display order in UI")


class ToolCategoryResponse(ToolCategoryBase):
    """Schema for tool category responses."""

    id: UUID = Field(..., description="Category unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


# Base schemas for tools
class ToolBase(BaseModel):
    """Base schema for tool data."""

    name: str = Field(..., min_length=1, max_length=100, description="Tool name")
    description: str = Field(..., description="Tool description")
    version: str = Field(
        "1.0.0", pattern=r"^\d+\.\d+\.\d+$", description="Tool version (semver)"
    )

    tool_type: ToolType = Field(..., description="Type of tool")
    requires_auth: bool = Field(
        True, description="Whether the tool requires authentication"
    )
    execution_env: ExecutionEnvironment = Field(
        ExecutionEnvironment.SANDBOX,
        description="Environment where the tool is executed",
    )
    timeout_seconds: int = Field(
        30, ge=1, le=300, description="Maximum execution time in seconds"
    )

    tags: Optional[List[str]] = Field(
        None, description="Tags for categorizing and searching tools"
    )
    category_id: Optional[UUID] = Field(None, description="ID of the tool category")
    is_public: bool = Field(False, description="Whether the tool is public or private")

    memory_mb: Optional[int] = Field(
        None, ge=128, description="Memory requirement in MB"
    )
    cpu_limit: Optional[float] = Field(None, ge=0.1, description="CPU limit in cores")

    examples: Optional[Dict[str, Any]] = Field(
        None, description="Example inputs and outputs"
    )
    documentation_url: Optional[str] = Field(
        None, description="URL to tool documentation"
    )

    schema: Optional[Dict[str, Any]] = Field(
        None, alias="schema", description="JSON Schema for tool inputs/outputs"
    )

    # Add a model_config to allow population by alias
    model_config = ConfigDict(populate_by_name=True)


class ToolCreate(ToolBase):
    """Schema for creating a new tool."""

    implementation: Dict[str, Any] = Field(
        ..., description="Tool implementation (code, spec, etc.)"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional tool metadata"
    )

    @model_validator(mode="after")
    def validate_tool_type_implementation(self) -> "ToolCreate":
        """Validate implementation structure matches the tool_type."""
        tool_type = self.tool_type
        impl = self.implementation

        if tool_type == ToolType.API:
            if "openapi_spec" not in impl:
                raise ValueError(
                    "API tools require an OpenAPI spec in the implementation"
                )

        elif tool_type == ToolType.FUNCTION:
            if "code" not in impl:
                raise ValueError("Function tools require code in the implementation")
            if "function_name" not in impl:
                raise ValueError(
                    "Function tools require a function_name in the implementation"
                )

        elif tool_type == ToolType.LLM:
            if "prompt_template" not in impl:
                raise ValueError(
                    "LLM tools require a prompt_template in the implementation"
                )

        return self


class ToolUpdate(BaseModel):
    """Schema for updating an existing tool."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None)
    version: Optional[str] = Field(None, pattern=r"^\d+\.\d+\.\d+$")

    implementation: Optional[Dict[str, Any]] = Field(None)
    schema: Optional[Dict[str, Any]] = Field(None, alias="schema")

    requires_auth: Optional[bool] = Field(None)
    execution_env: Optional[ExecutionEnvironment] = Field(None)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)

    tags: Optional[List[str]] = Field(None)
    category_id: Optional[UUID] = Field(None)
    is_public: Optional[bool] = Field(None)

    memory_mb: Optional[int] = Field(None, ge=128)
    cpu_limit: Optional[float] = Field(None, ge=0.1)

    examples: Optional[Dict[str, Any]] = Field(None)
    documentation_url: Optional[str] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None)

    is_deprecated: Optional[bool] = Field(None)


class ToolResponse(ToolBase):
    """Schema for tool responses."""

    id: UUID = Field(..., description="Tool unique identifier")
    owner_id: UUID = Field(..., description="ID of the tool owner")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    implementation: Optional[Dict[str, Any]] = Field(
        None, description="Tool implementation details"
    )

    is_approved: bool = Field(
        ..., description="Whether the tool has been approved by admins"
    )
    is_deprecated: bool = Field(..., description="Whether the tool is deprecated")

    metadata: Optional[Dict[str, Any]] = Field(
        {}, description="Additional tool metadata"
    )

    category: Optional[ToolCategoryResponse] = Field(None, description="Tool category")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Schema for tool execution
class ToolExecutionRequest(BaseModel):
    """Schema for requesting tool execution."""

    inputs: Dict[str, Any] = Field(..., description="Tool input parameters")
    agent_id: Optional[UUID] = Field(
        None, description="ID of the agent executing this tool"
    )
    timeout_seconds: Optional[int] = Field(
        None, ge=1, le=300, description="Custom timeout override"
    )


class ToolExecutionResponse(BaseModel):
    """Schema for tool execution responses."""

    id: UUID = Field(..., description="Execution ID")
    tool_id: UUID = Field(..., description="ID of the executed tool")
    user_id: UUID = Field(..., description="ID of the user who executed the tool")
    agent_id: Optional[UUID] = Field(
        None, description="ID of the agent that executed this tool"
    )

    inputs: Dict[str, Any] = Field(..., description="Tool input parameters")
    outputs: Optional[Dict[str, Any]] = Field(None, description="Tool output results")
    error: Optional[str] = Field(None, description="Error message if execution failed")

    duration_ms: Optional[int] = Field(
        None, description="Execution time in milliseconds"
    )
    success: bool = Field(..., description="Whether the execution was successful")
    created_at: datetime = Field(..., description="Execution timestamp")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Schemas for tool search and filtering
class ToolSearchParams(BaseModel):
    """Schema for tool search parameters."""

    query: Optional[str] = Field(None, description="Text search query")
    tool_type: Optional[ToolType] = Field(None, description="Filter by tool type")
    category_id: Optional[UUID] = Field(None, description="Filter by category")
    tags: Optional[List[str]] = Field(None, description="Filter by tags (any match)")
    is_public: Optional[bool] = Field(
        None, description="Filter by public/private status"
    )
    owner_id: Optional[UUID] = Field(None, description="Filter by owner")
