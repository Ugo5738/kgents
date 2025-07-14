from sqlalchemy import Column, DateTime, ForeignKey, PrimaryKeyConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from shared.models.base import Base


class AppClientRole(Base):
    __tablename__ = "app_client_roles"
    __table_args__ = (
        PrimaryKeyConstraint("app_client_id", "role_id", name="app_client_roles_pkey"),
        {"schema": "auth_service_data"},
    )

    app_client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth_service_data.app_clients.id", ondelete="CASCADE"),
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
        return f"<AppClientRole(app_client_id='{self.app_client_id}', role_id='{self.role_id}')>"
