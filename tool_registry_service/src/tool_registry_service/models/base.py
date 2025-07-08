"""
Base model definitions for the Tool Registry Service.

This module defines common base models and mixins used throughout the service.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID

from tool_registry_service.db import Base


class UUIDMixin:
    """
    Mixin to provide a UUID primary key for models.
    """
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )


class TimestampMixin:
    """
    Mixin to provide created_at and updated_at columns for models.
    """
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class OwnershipMixin:
    """
    Mixin to provide ownership tracking for models.
    """
    owner_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True
    )


class MetadataMixin:
    """
    Mixin to provide a JSON metadata column for models.
    """
    metadata = Column(
        JSON,
        nullable=True,
        default=dict
    )
