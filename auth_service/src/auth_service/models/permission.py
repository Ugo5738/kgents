from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from shared.models.base import Base, TimestampMixin, UUIDMixin


class Permission(Base):
    __tablename__ = "permissions"

    name = Column(
        String, unique=True, nullable=False, index=True
    )  # e.g., "users:create", "posts:read"
    description = Column(String, nullable=True)

    def __repr__(self):
        return f"<Permission(name='{self.name}')>"
