import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import declarative_base

# The single declarative base for all services to use.
Base = declarative_base()


class UUIDMixin:
    """Mixin to provide a UUID primary key for models."""

    id = Column(
        pgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )


class TimestampMixin:
    """Mixin to provide created_at and updated_at columns for models."""

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class OwnershipMixin:
    """Mixin to provide ownership tracking for models."""

    # This assumes ownership is tracked by a UUID referencing auth.users.id
    owner_id = Column(pgUUID(as_uuid=True), nullable=False, index=True)


class MetadataMixin:
    """Mixin to provide a JSON metadata column for models."""

    metadata = Column(JSON, nullable=True, default=dict)
