from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as pgUUID
from sqlalchemy.orm import relationship

from shared.models.base import Base, MetadataMixin, TimestampMixin, UUIDMixin


class Message(UUIDMixin, TimestampMixin, MetadataMixin, Base):
    __tablename__ = "messages"

    conversation_id = Column(
        pgUUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role = Column(String(16), nullable=False, index=True)  # 'user' | 'assistant' | 'system'
    content = Column(Text, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
