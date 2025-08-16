from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import httpx
from jose import jwt

try:
    import websockets
except ImportError as e:  # pragma: no cover
    raise SystemExit("Please install websockets: pip install websockets") from e

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None  # type: ignore[assignment]


@dataclass
class Config:
    base_url: str
    ws_url: str
    jwt_token: str


def _http_to_ws(url: str) -> str:
    if url.startswith("https://"):
        return "wss://" + url[len("https://") :]
    if url.startswith("http://"):
        return "ws://" + url[len("http://") :]
    return url


def _load_envs() -> None:
    if load_dotenv is None:
        return
    # Try multiple likely env files in priority order
    script_dir = os.path.abspath(os.path.dirname(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, ".."))
    candidates = [
        os.path.join(repo_root, ".env.dev"),
        os.path.join(repo_root, ".env"),
        os.path.join(repo_root, "conversation_service", ".env.dev"),
        os.path.join(repo_root, "conversation_service", ".env"),
    ]
    for path in candidates:
        if os.path.exists(path):
            load_dotenv(dotenv_path=path, override=False)


def _issue_user_jwt_from_env() -> Optional[str]:
    secret = os.getenv("CONVERSATION_SERVICE_USER_JWT_SECRET_KEY")
    alg = os.getenv("CONVERSATION_SERVICE_USER_JWT_ALGORITHM", "HS256")
    iss = os.getenv("CONVERSATION_SERVICE_USER_JWT_ISSUER", "kgents-auth")
    aud = os.getenv("CONVERSATION_SERVICE_USER_JWT_AUDIENCE", "authenticated")
    if not secret:
        return None
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(uuid4()),
        "iss": iss,
        "aud": aud,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "scope": "user",
    }
    return jwt.encode(payload, secret, algorithm=alg)


def build_config() -> Config:
    _load_envs()

    base_url = os.getenv("CONVERSATION_TEST_BASE_URL", "http://localhost:8005/api/v1").rstrip("/")

    provided_jwt = os.getenv("TEST_JWT")
    token = provided_jwt or _issue_user_jwt_from_env()
    if not token:
        raise SystemExit(
            "No JWT available. Set TEST_JWT or provide CONVERSATION_SERVICE_USER_JWT_SECRET_KEY in a loaded .env file."
        )

    return Config(base_url=base_url, ws_url=_http_to_ws(base_url), jwt_token=token)


async def create_conversation(client: httpx.AsyncClient, base_url: str) -> dict[str, Any]:
    owner_id = str(uuid4())
    payload = {"title": "Test Conversation", "owner_id": owner_id, "metadata": {}}
    r = await client.post(f"{base_url}/conversations/", json=payload)
    r.raise_for_status()
    return r.json()


async def post_user_message(client: httpx.AsyncClient, base_url: str, conversation_id: UUID, content: str) -> dict[str, Any]:
    payload = {"role": "user", "content": content, "metadata": {}}
    r = await client.post(f"{base_url}/conversations/{conversation_id}/messages", json=payload)
    r.raise_for_status()
    return r.json()


async def run_test() -> None:
    cfg = build_config()
    headers = {"Authorization": f"Bearer {cfg.jwt_token}"}

    async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
        conv = await create_conversation(client, cfg.base_url)
        conversation_id = conv["id"]
        print(f"Created conversation: {conversation_id}")

        ws_endpoint = f"{cfg.ws_url}/ws/conversations/{conversation_id}"
        print(f"Connecting WS: {ws_endpoint}")

        async with websockets.connect(ws_endpoint, extra_headers=headers, open_timeout=10) as ws:
            # Receive initial connected event
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            print("WS <-", msg)
            evt = json.loads(msg)
            assert evt.get("type") == "connected", "Expected connected event"

            # Trigger a user message via REST
            print("Posting user message via REST...")
            posted = await post_user_message(client, cfg.base_url, conversation_id, "Hello, world!")
            print("Message created:", posted["id"]) 

            # Expect ack, stream chunks, and complete
            done = False
            while not done:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30)
                except asyncio.TimeoutError:
                    raise SystemExit("Timed out waiting for streaming events")

                print("WS <-", msg)
                evt = json.loads(msg)
                if evt.get("type") == "complete":
                    done = True

    print("Test completed successfully.")


if __name__ == "__main__":
    asyncio.run(run_test())
