# tool_registry_service/src/tool_registry_service/models/tool.py
"""
Tool models for the Tool Registry Service.

This module defines SQLAlchemy models for tools, tool categories, and their executions.
"""

from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import relationship

from shared.models.base import (
    Base,
    MetadataMixin,
    OwnershipMixin,
    TimestampMixin,
    UUIDMixin,
)


class ToolType(str, PyEnum):
    """Enum for types of tools available in the registry."""

    API = "api"  # RESTful API tool (OpenAPI spec)
    FUNCTION = "function"  # Python function tool
    LLM = "llm"  # LLM-based tool
    CHAIN = "chain"  # Chain of tools
    EXTERNAL = "external"  # External tool (e.g., from LangChain)
    OTHER = "other"  # Other tool types


class ExecutionEnvironment(str, PyEnum):
    """Enum for execution environments where tools can run."""

    SANDBOX = "sandbox"  # Isolated sandbox environment
    CONTAINER = "container"  # Docker container
    SERVERLESS = "serverless"  # Serverless function (e.g., AWS Lambda)
    LOCAL = "local"  # Local Python environment
    REMOTE = "remote"  # Remote API endpoint


class ToolCategory(Base, UUIDMixin, TimestampMixin):
    """
    Model representing tool categories for organization and filtering.
    """

    __tablename__ = "tool_categories"
    # Constraints
    __table_args__ = (UniqueConstraint("name", name="uq_category_name"),)

    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(255), nullable=True)  # Icon identifier or URL
    display_order = Column(Integer, nullable=False, default=0)  # For UI ordering

    # Relationships
    tools = relationship("Tool", back_populates="category")


class Tool(Base, UUIDMixin, TimestampMixin, OwnershipMixin, MetadataMixin):
    """
    Model representing a tool in the registry.

    A tool can be a function, API, LLM chain, or other component that
    agents can use to perform tasks.
    """

    __tablename__ = "tools"
    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "name", "version", "owner_id", name="uq_tool_name_version_owner"
        ),
    )

    # Basic information
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    version = Column(String(20), nullable=False, default="1.0.0")

    # Tool implementation details
    tool_type = Column(Enum(ToolType), nullable=False, index=True)
    implementation = Column(JSON, nullable=False)  # Contains code, API spec, etc.
    schema = Column(JSON, nullable=True)  # JSON Schema for tool inputs/outputs

    # Security and execution settings
    requires_auth = Column(Boolean, nullable=False, default=True)
    execution_env = Column(
        Enum(ExecutionEnvironment), nullable=False, default=ExecutionEnvironment.SANDBOX
    )
    timeout_seconds = Column(Integer, nullable=False, default=30)

    # Resource requirements and constraints
    memory_mb = Column(Integer, nullable=True)
    cpu_limit = Column(Float, nullable=True)

    # Discoverability and organization
    tags = Column(ARRAY(String), nullable=True)
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tool_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_public = Column(Boolean, nullable=False, default=False)
    is_approved = Column(Boolean, nullable=False, default=False)
    is_deprecated = Column(Boolean, nullable=False, default=False)

    # Documentation and example usage
    examples = Column(JSON, nullable=True)  # Example inputs and outputs
    documentation_url = Column(String(255), nullable=True)

    # Relationships
    category = relationship("ToolCategory", back_populates="tools")


class ToolExecution(Base, UUIDMixin, TimestampMixin):
    """
    Model representing a record of tool execution.

    Each time a tool is executed, this model stores details about the
    execution for monitoring, debugging, and analytics.
    """

    __tablename__ = "tool_executions"

    # References to related entities
    tool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    agent_id = Column(
        UUID(as_uuid=True), nullable=True, index=True
    )  # Optional link to agent

    # Execution details
    inputs = Column(JSON, nullable=True)  # Tool inputs
    outputs = Column(JSON, nullable=True)  # Tool outputs
    error = Column(Text, nullable=True)  # Error message if execution failed

    # Performance metrics
    duration_ms = Column(Integer, nullable=True)  # Execution time in milliseconds
    success = Column(Boolean, nullable=False, default=False)

    # Relationships
    tool = relationship("Tool")
