# auth_service/src/auth_service/models/role.py

from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from shared.models.base import Base, TimestampMixin, UUIDMixin


class Role(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "roles"
    __table_args__ = {"schema": "auth_service_data"}

    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)

    # Relationships
    # This relationship is correct and defines the other side of the many-to-many.
    users = relationship(
        "Profile",
        secondary="auth_service_data.user_roles",  # Schema-qualify the secondary table
        back_populates="roles",
    )

    app_clients = relationship(
        "AppClient",
        secondary="auth_service_data.app_client_roles",  # Schema-qualify
        lazy="selectin",
        back_populates="roles",
    )
    permissions = relationship(
        "Permission", secondary="auth_service_data.role_permissions"
    )  # Schema-qualify

    def __repr__(self):
        return f"<Role(id='{self.id}', name='{self.name}')>"
