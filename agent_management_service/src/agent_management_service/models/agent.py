from enum import Enum
from uuid import UUID

from sqlalchemy import JSON, Enum as SQLAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_management_service.models.base import BaseModel


class AgentStatus(str, Enum):
    """
    Enum representing the possible statuses of an agent.
    """
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Agent(BaseModel):
    """
    Model representing an agent in the system.
    
    An agent is a configurable AI component that can be created, deployed, and
    managed through the platform. Agents are owned by users and can be in various
    stages of their lifecycle (draft, published, archived).
    """
    __tablename__ = "agents"

    # Basic agent information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Agent configuration - stored as JSON for flexibility
    # This contains the Langflow configuration
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Status tracking
    status: Mapped[AgentStatus] = mapped_column(
        SQLAEnum(AgentStatus),
        nullable=False,
        default=AgentStatus.DRAFT,
    )
    
    # Tags for agent categorization 
    tags: Mapped[list] = mapped_column(JSON, nullable=True)
    
    # Ownership - link to auth.users
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        nullable=False,
        index=True,
    )
    
    # Relationships
    # Cascade delete is enabled so that agent versions are deleted when the agent is deleted
    versions = relationship(
        "AgentVersion",
        back_populates="agent",
        cascade="all, delete-orphan",
        order_by="desc(AgentVersion.version_number)",
    )
    
    # Current active version for this agent (if published)
    active_version_id = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("agent_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    active_version = relationship(
        "AgentVersion",
        foreign_keys=[active_version_id],
        post_update=True,
    )
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"<Agent {self.name} ({self.status.value})>"
