from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamp fields to models.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """
    Mixin that adds UUID primary key to models.
    """

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )


class BaseModel(UUIDMixin, TimestampMixin, Base):
    """
    Base model class with UUID primary key and timestamp fields.
    """

    __abstract__ = True
