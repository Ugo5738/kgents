import uuid
from enum import Enum

from sqlalchemy import JSON, Column, DateTime, Enum as SQLAEnum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.agent_management_service.db import Base


class AgentStatus(str, Enum):
    """
    Enum representing the possible statuses of an agent.
    """
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Agent(Base):
    """
    Model representing an agent in the system.
    
    An agent is a configurable AI component that can be created, deployed, and
    managed through the platform. Agents are owned by users and can be in various
    stages of their lifecycle (draft, published, archived).
    """
    __tablename__ = "agents"

    # Primary key with UUID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic agent information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Agent configuration - stored as JSON for flexibility
    # This contains the Langflow configuration
    config = Column(JSON, nullable=False)
    
    # Status tracking
    status = Column(
        SQLAEnum(AgentStatus),
        nullable=False,
        default=AgentStatus.DRAFT,
    )
    
    # Tags for agent categorization 
    tags = Column(JSON, nullable=True)
    
    # Ownership - link to auth.users
    user_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,
    )
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    # Relationships
    # Cascade delete is enabled so that agent versions are deleted when the agent is deleted
    versions = relationship(
        "AgentVersion",
        back_populates="agent",
        cascade="all, delete-orphan",
        order_by="desc(AgentVersion.version_number)",
        # Add primaryjoin to explicitly define this relationship
        primaryjoin="Agent.id == AgentVersion.agent_id",
    )
    
    # Current active version for this agent (if published)
    # Using use_alter and name for the foreign key to defer its creation
    active_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "agent_versions.id", 
            ondelete="SET NULL",
            # These settings tell SQLAlchemy to create this FK constraint after both tables are created
            use_alter=True,
            name="fk_agent_active_version_id"
        ),
        nullable=True,
    )
    active_version = relationship(
        "AgentVersion",
        foreign_keys=[active_version_id],
        # Use post_update to handle circular dependency
        post_update=True,
        # Add primaryjoin to explicitly define this relationship
        primaryjoin="Agent.active_version_id == AgentVersion.id",
    )
    
    def __repr__(self):
        """String representation of the agent."""
        return f"<Agent(id='{self.id}', name='{self.name}', status='{self.status}')>"
