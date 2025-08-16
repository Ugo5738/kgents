from __future__ import annotations

import asyncio
import json
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from shared.security.jwt import AuthError, decode_any, parse_bearer
from ..config import settings

ws_router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        # Map conversation_id -> list of websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, conversation_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.setdefault(conversation_id, []).append(websocket)

    def disconnect(self, conversation_id: str, websocket: WebSocket) -> None:
        if conversation_id in self.active_connections:
            try:
                self.active_connections[conversation_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]

    async def send_text(self, conversation_id: str, message: str) -> None:
        for ws in list(self.active_connections.get(conversation_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                # Drop broken connections
                self.disconnect(conversation_id, ws)


_manager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    return _manager


@ws_router.websocket("/conversations/{conversation_id}")
async def conversation_websocket(websocket: WebSocket, conversation_id: str):
    # Enforce JWT auth before accepting the connection
    token = parse_bearer(websocket.headers, websocket.query_params)
    if not token:
        await websocket.close(code=1008)
        return
    try:
        claims = decode_any(
            token,
            user_cfg={
                "secret": settings.USER_JWT_SECRET_KEY,
                "algorithm": settings.USER_JWT_ALGORITHM,
                "issuer": settings.USER_JWT_ISSUER,
                "audience": settings.USER_JWT_AUDIENCE,
            },
            m2m_cfg={
                "secret": settings.M2M_JWT_SECRET_KEY,
                "algorithm": settings.M2M_JWT_ALGORITHM,
                "issuer": settings.M2M_JWT_ISSUER,
                "audience": settings.M2M_JWT_AUDIENCE,
            },
        )
        # Optionally: validate conversation access from claims here
    except AuthError:
        await websocket.close(code=1008)
        return

    await _manager.connect(conversation_id, websocket)
    try:
        await _manager.send_text(conversation_id, json.dumps({"type": "connected"}))
        while True:
            # For now, we echo back what we receive. In the future, handle client events.
            data = await websocket.receive_text()
            await _manager.send_text(
                conversation_id, json.dumps({"type": "echo", "content": data})
            )
    except WebSocketDisconnect:
        _manager.disconnect(conversation_id, websocket)
    except Exception:
        _manager.disconnect(conversation_id, websocket)
        # Swallow other exceptions to avoid crashing the server
        await asyncio.sleep(0)
