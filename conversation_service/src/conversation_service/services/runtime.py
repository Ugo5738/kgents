from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings
from ..logging_config import logger
from ..routers.ws_router import get_ws_manager


async def get_langflow_token(client: httpx.AsyncClient) -> Optional[str]:
    try:
        resp = await client.get(
            f"{settings.LANGFLOW_RUNTIME_URL}/api/v1/auto_login", timeout=10.0
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("access_token")
        logger.warning("Langflow auto_login failed: %s", resp.status_code)
        return None
    except Exception as e:
        logger.warning("Langflow auto_login error: %s", e)
        return None


async def run_agent_flow(conversation_id: str, user_message: str) -> None:
    """
    Kick off an agent flow run for the given conversation.
    Currently simulates streaming output; replace with actual Langflow run.
    """
    manager = get_ws_manager()

    token: Optional[str] = None
    try:
        async with httpx.AsyncClient() as client:
            token = await get_langflow_token(client)
            if token:
                await manager.send_text(
                    conversation_id,
                    json.dumps({"type": "info", "message": "langflow_authenticated"}),
                )
            else:
                await manager.send_text(
                    conversation_id,
                    json.dumps({"type": "warn", "message": "langflow_auth_failed"}),
                )
    except Exception as e:
        logger.warning("Langflow runtime check failed: %s", e)

    # Try a real run if we have a token; fallback to simulation if anything fails
    if token:
        ok = await _try_real_langflow_run(conversation_id, user_message, token)
        if ok:
            await manager.send_text(conversation_id, json.dumps({"type": "complete"}))
            return

    # Simulated streaming (fallback)
    for chunk in [
        "Thinking...",
        f"Received: {user_message[:60]}",
        "Planning tools...",
        "Generating response...",
        "Done.",
    ]:
        await manager.send_text(
            conversation_id, json.dumps({"type": "stream", "content": chunk})
        )
        await asyncio.sleep(0.3)

    await manager.send_text(conversation_id, json.dumps({"type": "complete"}))


async def _try_real_langflow_run(
    conversation_id: str, user_message: str, token: str
) -> bool:
    """
    Attempt to run a flow on Langflow using common endpoint patterns.
    If any step fails, return False so caller can fallback to simulation.
    """
    manager = get_ws_manager()
    headers = {"Authorization": f"Bearer {token}"}
    base = settings.LANGFLOW_RUNTIME_URL.rstrip("/")

    async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
        # 1) Try to enumerate flows using a few likely endpoints
        flow_id = await _discover_flow_id(client, base)
        if not flow_id:
            await manager.send_text(
                conversation_id,
                json.dumps({"type": "warn", "message": "no_flows_found"}),
            )
            return False

        # 2) Try to run the flow using several common patterns
        candidates = [
            ("POST", f"{base}/api/v1/run/{flow_id}", {"input": user_message}),
            ("POST", f"{base}/api/v1/flows/{flow_id}/run", {"input": user_message}),
            ("POST", f"{base}/api/v1/run", {"flowId": flow_id, "input": user_message}),
        ]

        for method, url, payload in candidates:
            try:
                resp = await client.request(method, url, json=payload)
                if resp.status_code >= 200 and resp.status_code < 300:
                    data = resp.json()
                    # Try common result shapes
                    content = _extract_response_text(data)
                    if content:
                        await manager.send_text(
                            conversation_id,
                            json.dumps({"type": "stream", "content": content}),
                        )
                        return True
                    # If structure unknown, stream entire JSON payload
                    await manager.send_text(
                        conversation_id,
                        json.dumps(
                            {"type": "stream", "content": json.dumps(data)[:2000]}
                        ),
                    )
                    return True
                else:
                    logger.debug("Run attempt failed %s: %s", url, resp.text[:500])
            except Exception as e:
                logger.debug("Run attempt error %s: %s", url, e)

    return False


async def _discover_flow_id(client: httpx.AsyncClient, base: str) -> Optional[str]:
    # Try a few endpoints that might return flows
    urls = [
        f"{base}/api/v1/flows",
        f"{base}/api/v1/flow",
        f"{base}/api/v1/projects/default/flows",
    ]
    for url in urls:
        try:
            resp = await client.get(url)
            if resp.status_code >= 200 and resp.status_code < 300:
                data = resp.json()
                flow_id = _extract_first_flow_id(data)
                if flow_id:
                    return flow_id
        except Exception:
            continue
    return None


def _extract_first_flow_id(data: Any) -> Optional[str]:
    # Heuristics for different schema shapes
    # e.g., {"flows": [{"id": "..."}, ...]}
    # or {"items": [{"uuid": "..."}, ...]}
    candidates: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        for key in ("flows", "items", "data", "nodes"):
            val = data.get(key)
            if isinstance(val, list):
                candidates = val
                break
        if not candidates and isinstance(data.get("result"), list):
            candidates = data["result"]  # type: ignore[index]
    elif isinstance(data, list):
        candidates = data

    for item in candidates:
        if not isinstance(item, dict):
            continue
        for id_key in ("id", "uuid", "flow_id", "_id"):
            if id_key in item:
                return str(item[id_key])
    return None


def _extract_response_text(data: Any) -> Optional[str]:
    # Heuristics to extract user-friendly text from a result
    if isinstance(data, dict):
        for key in ("text", "message", "content", "result"):
            val = data.get(key)
            if isinstance(val, str):
                return val
        # Some endpoints return {"outputs": [{"data": {"text": "..."}}]}
        outputs = data.get("outputs")
        if isinstance(outputs, list) and outputs:
            first = outputs[0]
            if isinstance(first, dict):
                # Look for nested text-like content
                for path in (("data", "text"), ("data", "output")):
                    cur: Any = first
                    ok = True
                    for p in path:
                        if isinstance(cur, dict) and p in cur:
                            cur = cur[p]
                        else:
                            ok = False
                            break
                    if ok and isinstance(cur, str):
                        return cur
    return None
