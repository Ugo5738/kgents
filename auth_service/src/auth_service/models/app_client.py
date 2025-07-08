from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from shared.models.base import Base, TimestampMixin, UUIDMixin


class AppClient(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "app_clients"

    client_name = Column(String, unique=True, nullable=False, index=True)
    client_secret_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(String, nullable=True)
    allowed_callback_urls = Column(ARRAY(String), nullable=True)

    # Define many-to-many relationship with Role via AppClientRole
    roles = relationship(
        "Role",
        secondary="app_client_roles",
        lazy="selectin",
        back_populates="app_clients",
        overlaps="app_client_association_objects,role",  # Fix for SQLAlchemy relationship conflict warning
    )

    def __repr__(self):
        return f"<AppClient(client_name='{self.client_name}')>"
