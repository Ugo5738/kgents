from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_management_service.models.base import BaseModel


class AgentVersion(BaseModel):
    """
    Model representing a specific version of an agent.
    
    Each time an agent configuration is modified, a new version is created
    to maintain a history of changes.
    """
    __tablename__ = "agent_versions"

    # Version metadata
    version_number: Mapped[int] = mapped_column(
        Integer, 
        nullable=False,
        index=True,
    )
    
    # Change description
    change_summary: Mapped[str] = mapped_column(
        Text, 
        nullable=True,
    )
    
    # Snapshot of the full agent configuration at this version
    # Storing the complete config allows for easier rollbacks and comparisons
    config_snapshot: Mapped[dict] = mapped_column(
        JSON, 
        nullable=False,
    )
    
    # Link to parent agent
    agent_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent = relationship(
        "Agent", 
        back_populates="versions",
        foreign_keys=[agent_id],
    )
    
    # Ownership - links to auth.users
    # We store this directly for easier querying and to maintain data integrity
    # even if the parent agent is deleted
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        nullable=False,
        index=True,
    )
    
    def __repr__(self) -> str:
        """String representation of the agent version."""
        return f"<AgentVersion #{self.version_number} for agent {self.agent_id}>"
