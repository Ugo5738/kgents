from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from conversation_service.db import get_db
from conversation_service.models import Conversation, Message
from conversation_service.routers.ws_router import get_ws_manager
from conversation_service.schemas.conversation import (
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from conversation_service.services.runtime import run_agent_flow

conversations_router = APIRouter(prefix="/conversations", tags=["Conversations"])


@conversations_router.post("/", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(payload: ConversationCreate, db: AsyncSession = Depends(get_db)):
    conv = Conversation(title=payload.title, owner_id=payload.owner_id, metadata_json=payload.metadata_json)
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return conv


@conversations_router.get("/{conversation_id}", response_model=ConversationRead)
async def get_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@conversations_router.get("/{conversation_id}/messages", response_model=List[MessageRead])
async def list_messages(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    )
    rows = result.scalars().all()
    return list(rows)


@conversations_router.post("/{conversation_id}/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def add_message(
    conversation_id: UUID,
    payload: MessageCreate,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg = Message(conversation_id=conversation_id, role=payload.role, content=payload.content, metadata_json=payload.metadata_json)
    db.add(msg)
    await db.flush()
    await db.refresh(msg)

    # Immediately acknowledge over WebSocket and schedule background run for assistant
    manager = get_ws_manager()
    await manager.send_text(
        str(conversation_id),
        f'{{"type":"ack","message_id":"{msg.id}","role":"{payload.role}"}}',
    )

    if payload.role == "user":
        background.add_task(run_agent_flow, str(conversation_id), payload.content)

    return msg
