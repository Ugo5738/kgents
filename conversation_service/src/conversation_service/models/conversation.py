from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from shared.models.base import Base, MetadataMixin, OwnershipMixin, TimestampMixin, UUIDMixin


class Conversation(UUIDMixin, TimestampMixin, OwnershipMixin, MetadataMixin, Base):
    __tablename__ = "conversations"

    title = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True)

    # Relationships
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
