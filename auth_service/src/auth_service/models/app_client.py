from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from shared.models.base import Base, TimestampMixin, UUIDMixin


class AppClient(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "app_clients"
    __table_args__ = {"schema": "auth_service_data"}

    client_name = Column(String, unique=True, nullable=False, index=True)
    client_secret_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(String, nullable=True)
    allowed_callback_urls = Column(ARRAY(String), nullable=True)

    # Define the many-to-many relationship with Role.
    # This is the ONLY relationship needed on this model.
    # The 'back_populates="app_clients"' points to the corresponding property on the Role model.
    roles = relationship(
        "Role",
        secondary="auth_service_data.app_client_roles",
        lazy="selectin",
        back_populates="app_clients",
    )

    def __repr__(self):
        return f"<AppClient(client_name='{self.client_name}')>"
