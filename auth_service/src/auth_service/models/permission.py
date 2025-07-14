from sqlalchemy import Column, String

from shared.models.base import Base, TimestampMixin, UUIDMixin


class Permission(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "permissions"
    __table_args__ = {"schema": "auth_service_data"}

    name = Column(
        String, unique=True, nullable=False, index=True
    )  # e.g., "users:create", "posts:read"
    description = Column(String, nullable=True)

    def __repr__(self):
        return f"<Permission(name='{self.name}')>"
