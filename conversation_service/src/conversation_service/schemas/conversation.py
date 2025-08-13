from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationBase(BaseModel):
    title: str = Field(..., max_length=255)
    metadata_json: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        serialization_alias="metadata",
        validation_alias="metadata",
    )


class ConversationCreate(ConversationBase):
    owner_id: UUID


class ConversationRead(ConversationBase):
    id: UUID
    status: str

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant|system)$")
    content: str
    metadata_json: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        serialization_alias="metadata",
        validation_alias="metadata",
    )


class MessageCreate(MessageBase):
    pass


class MessageRead(MessageBase):
    id: UUID

    class Config:
        from_attributes = True
