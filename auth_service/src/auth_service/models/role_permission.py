from sqlalchemy import Column, DateTime, ForeignKey, PrimaryKeyConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from shared.models.base import Base, TimestampMixin


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth_service_data.roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth_service_data.permissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint("role_id", "permission_id", name="role_permissions_pkey"),
        {"schema": "auth_service_data"},
    )

    def __repr__(self):
        return f"<RolePermission(role_id='{self.role_id}', permission_id='{self.permission_id}')>"
