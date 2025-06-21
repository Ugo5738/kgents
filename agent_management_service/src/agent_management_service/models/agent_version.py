import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.agent_management_service.db import Base


class AgentVersion(Base):
    """
    Model representing a specific version of an agent.

    Each time an agent configuration is modified, a new version is created
    to maintain a history of changes.
    """
    __tablename__ = "agent_versions"

    # Primary key with UUID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Version metadata
    version_number = Column(
        Integer,
        nullable=False,
        index=True,
    )

    # Change description
    change_summary = Column(
        Text,
        nullable=True,
    )

    # Snapshot of the full agent configuration at this version
    # Storing the complete config allows for easier rollbacks and comparisons
    config_snapshot = Column(
        JSON,
        nullable=False,
    )

    # Link to parent agent - using string reference to avoid circular dependency
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"), 
        nullable=False,
        index=True,
    )
    # Using string reference for relationship
    agent = relationship(
        "Agent",
        back_populates="versions",
        foreign_keys=[agent_id],
        # Explicitly use primaryjoin to define the relationship
        primaryjoin="AgentVersion.agent_id == Agent.id", 
    )

    # Ownership - links to auth.users
    # We store this directly for easier querying and to maintain data integrity
    # even if the parent agent is deleted
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

    def __repr__(self):
        """String representation of the agent version."""
        return f"<AgentVersion(id='{self.id}', version_number='{self.version_number}', agent_id='{self.agent_id}')>"
