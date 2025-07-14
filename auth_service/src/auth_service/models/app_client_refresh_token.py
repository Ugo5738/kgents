from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from shared.models.base import Base, TimestampMixin, UUIDMixin


class AppClientRefreshToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "app_client_refresh_tokens"
    __table_args__ = {"schema": "auth_service_data"}

    app_client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth_service_data.app_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(
        DateTime(timezone=True), nullable=True
    )  # Timestamp when the token was revoked

    def __repr__(self):
        return f"<AppClientRefreshToken(id='{self.id}', app_client_id='{self.app_client_id}', revoked='{bool(self.revoked_at)}')>"
