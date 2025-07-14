# auth_service/src/auth_service/models/profile.py

from sqlalchemy import Boolean, Column, ForeignKeyConstraint, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from shared.models.base import Base, TimestampMixin

# Define a placeholder for Supabase's auth.users table.
# This makes SQLAlchemy's metadata aware of the table and its schema
# without trying to create or manage it. This resolves the NoReferencedTableError.
auth_users_table = Table(
    "users",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    schema="auth",
    extend_existing=True,
)


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    # Add foreign key constraint with use_alter and post_create
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
            use_alter=True,
            name="fk_profile_auth_user_id",
        ),
        {"schema": "auth_service_data"},
    )

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String, nullable=False, index=True, unique=True)
    username = Column(String, unique=True, nullable=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # This relationship is correct and defines the many-to-many link.
    roles = relationship(
        "Role",
        secondary="auth_service_data.user_roles",  # Schema-qualify the secondary table
        back_populates="users",
    )

    def __repr__(self):
        return f"<Profile(user_id='{self.user_id}', username='{self.username}')>"
