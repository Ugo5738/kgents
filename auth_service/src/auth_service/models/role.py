from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from shared.models.base import Base, TimestampMixin, UUIDMixin


class Role(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "roles"

    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)

    # Relationships
    # Properly define overlaps to address all relationship conflicts
    users = relationship(
        "Profile",
        secondary="user_roles",
        back_populates="roles",
        overlaps="user_roles,role,user_profile",
    )

    user_roles = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
        overlaps="users,profile_role,profile,user_profile",
    )

    app_clients = relationship(
        "AppClient",
        secondary="app_client_roles",
        lazy="selectin",
        back_populates="roles",  # Matches the back_populates in AppClient.roles
        overlaps="app_client,role",  # Fix for SQLAlchemy relationship conflict warning
    )
    app_client_association_objects = relationship(
        "AppClientRole", back_populates="role", overlaps="app_clients"
    )
    permissions = relationship("Permission", secondary="role_permissions")

    def __repr__(self):
        return f"<Role(id='{self.id}', name='{self.name}')>"
