# agent_deployment_service/src/agent_deployment_service/models/deployment.py
"""
Database models for the Agent Deployment Service.

This module defines the SQLAlchemy models necessary to track agent deployments,
their status, and associated metadata.
"""
from enum import Enum

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLAEnum
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from shared.models.base import Base, TimestampMixin, UUIDMixin


class DeploymentStatus(str, Enum):
    """
    Enum representing the lifecycle status of an agent deployment.
    """

    PENDING = "pending"  # The deployment request has been accepted and is queued.
    DEPLOYING = "deploying"  # The deployment process is actively in progress.
    RUNNING = "running"  # The agent is successfully deployed and operational.
    FAILED = "failed"  # The deployment attempt failed.
    STOPPED = (
        "stopped"  # The agent was successfully deployed but has been manually stopped.
    )


class Deployment(Base, UUIDMixin, TimestampMixin):
    """
    Represents a single deployment instance of an agent version.

    This table is the core of the Agent Deployment Service, tracking each
    deployment from initiation to its final state.
    """

    __tablename__ = "deployments"

    # --- Foreign Keys to other services' data ---
    # These link the deployment back to the specific agent and version it represents.
    # Note: No direct SQLAlchemy relationship is defined here, as these tables
    # exist in different service databases. These are for reference.
    agent_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="The ID of the agent being deployed, from the Agent Management Service.",
    )

    agent_version_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="The specific version of the agent being deployed.",
    )

    user_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="The ID of the user who owns this deployment.",
    )

    # --- Deployment State and Metadata ---
    status = Column(
        SQLAEnum(DeploymentStatus, name="deployment_status_enum", create_type=True),
        nullable=False,
        default=DeploymentStatus.PENDING,
        index=True,
        comment="The current status of the deployment lifecycle.",
    )

    endpoint_url = Column(
        Text,
        nullable=True,
        comment="The URL where the deployed agent can be accessed once it is running.",
    )

    deployment_metadata = Column(
        JSONB,
        nullable=True,
        comment="Platform-specific metadata, e.g., Kubernetes pod name, container ID, etc.",
    )

    error_message = Column(
        Text,
        nullable=True,
        comment="Stores any error messages if the deployment fails.",
    )

    def __repr__(self):
        """String representation of the Deployment model for debugging."""
        return f"<Deployment(id='{self.id}', agent_id='{self.agent_id}', status='{self.status}')>"
