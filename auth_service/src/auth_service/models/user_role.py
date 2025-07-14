from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from shared.models.base import Base, TimestampMixin, UUIDMixin


class UserRole(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role_assignment"),
        {"schema": "auth_service_data"},
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth_service_data.profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth_service_data.roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<UserRole(user_id='{self.user_id}', role_id='{self.role_id}')>"
