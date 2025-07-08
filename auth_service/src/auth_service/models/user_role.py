from sqlalchemy import Column, DateTime, ForeignKey, ForeignKeyConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from shared.models.base import Base, TimestampMixin, UUIDMixin


class UserRole(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_roles"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id = Column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    assigned_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            use_alter=True,  # This creates the constraint after tables are created
            name="fk_user_role_auth_user_id",
        ),
    )

    # Relationships
    # The overlaps parameter is used to acknowledge that these relationships may copy
    # the same columns as other relationships in related models.
    role = relationship(
        "Role",
        back_populates="user_roles",
        overlaps="users,profile_role,profiles",
    )
    user_profile = relationship(
        "Profile",
        back_populates="user_roles",
        overlaps="roles,user_role,roles",
    )

    def __repr__(self):
        return f"<UserRole(user_id='{self.user_id}', role_id='{self.role_id}')>"
