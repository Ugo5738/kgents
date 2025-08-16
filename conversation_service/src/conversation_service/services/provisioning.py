from __future__ import annotations

import json
import time
from typing import Any, Optional
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session_factory
from ..logging_config import logger
from ..models import Conversation


async def provision_flow_if_missing(conversation_id: str, hint: str) -> Optional[str]:
    """
    Ensure the conversation has a bound flow_id in metadata.
    - If already bound, return it.
    - Else if DEFAULT_FLOW_ID is configured, bind and return it.
    - Else attempt remote provisioning via Agent Runtime Service and bind the result.
    Returns the flow_id if available, else None.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:  # type: AsyncSession
        conv = await session.get(Conversation, UUID(conversation_id))
        if not conv:
            logger.warning("Conversation not found for provisioning: %s", conversation_id)
            return None

        meta: dict[str, Any] = conv.metadata_json or {}
        flow_id = meta.get("flow_id")
        if isinstance(flow_id, str) and flow_id:
            return flow_id

        # Use configured default if present
        if settings.DEFAULT_FLOW_ID:
            meta["flow_id"] = settings.DEFAULT_FLOW_ID
            conv.metadata_json = meta
            await session.commit()
            return settings.DEFAULT_FLOW_ID

        # Try remote provisioning via Agent Runtime Service
        new_flow_id = await _provision_via_runtime_service(hint)
        if new_flow_id:
            meta["flow_id"] = new_flow_id
            conv.metadata_json = meta
            await session.commit()
            return new_flow_id

        return None


_M2M_TOKEN: Optional[str] = None
_M2M_TOKEN_EXPIRES_AT: float = 0.0


async def _get_m2m_token() -> Optional[str]:
    """
    Obtain an M2M access token from the Auth Service using client credentials.
    Caches the token in-memory until shortly before expiry.
    """
    global _M2M_TOKEN, _M2M_TOKEN_EXPIRES_AT

    now = time.time()
    if _M2M_TOKEN and now < (_M2M_TOKEN_EXPIRES_AT - 5):
        return _M2M_TOKEN

    client_id = settings.CLIENT_ID
    client_secret = settings.CLIENT_SECRET
    if not client_id or not client_secret:
        logger.debug("M2M credentials not configured; skipping Authorization header")
        return None

    token_url = f"{settings.AUTH_SERVICE_URL.rstrip('/')}/auth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(token_url, json=payload)
            if 200 <= resp.status_code < 300:
                data = resp.json()
                token = data.get("access_token")
                expires_in = data.get("expires_in") or 900
                if isinstance(token, str) and token:
                    _M2M_TOKEN = token
                    # Refresh a little early
                    _M2M_TOKEN_EXPIRES_AT = time.time() + int(expires_in) - 30
                    return _M2M_TOKEN
                logger.warning("Auth token response missing access_token")
            else:
                logger.warning("Auth token request failed %s: %s", resp.status_code, resp.text[:300])
    except Exception as e:
        logger.debug("Auth token request error: %s", e)

    return None


async def _provision_via_runtime_service(hint: str) -> Optional[str]:
    """
    Provision/select a flow from natural language via the Agent Runtime Service only.
    Returns flow_id on success, None otherwise.
    """
    candidates: list[tuple[str, str, dict[str, Any]]] = []

    # Preferred: Agent Runtime Service
    if getattr(settings, "AGENT_RUNTIME_SERVICE_URL", None):
        base = settings.AGENT_RUNTIME_SERVICE_URL.rstrip("/")
        if base.endswith("/api") or base.endswith("/api/v1"):
            url = f"{base}/agents/provision"
        else:
            url = f"{base}/api/v1/agents/provision"
        candidates.append(("POST", url, {"description": hint}))

    if not candidates:
        logger.info("Agent Runtime Service URL not configured; skipping provisioning")
        return None

    headers: dict[str, str] = {}
    # Attach M2M Authorization header if available
    try:
        token = await _get_m2m_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    except Exception as e:
        logger.debug("M2M token acquisition failed: %s", e)

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        for method, url, payload in candidates:
            try:
                resp = await client.request(method, url, json=payload)
                if 200 <= resp.status_code < 300:
                    try:
                        data = resp.json()
                    except Exception:
                        data = {}
                    flow_id = _extract_flow_id(data)
                    if flow_id:
                        return flow_id
                    # If unknown schema, try to parse text
                    if isinstance(data, (dict, list)):
                        logger.debug("Provisioning response schema not recognized: %s", json.dumps(data)[:500])
                else:
                    logger.debug("Provisioning attempt failed %s: %s", url, resp.text[:300])
            except Exception as e:
                logger.debug("Provisioning attempt error %s: %s", url, e)

    return None


def _extract_flow_id(data: Any) -> Optional[str]:
    if isinstance(data, dict):
        # Common keys
        for key in ("flow_id", "flowId", "id", "uuid"):
            if key in data and isinstance(data[key], (str, int)):
                return str(data[key])
        # Nested structures e.g., {"deployment": {"flow_id": "..."}}
        deployment = data.get("deployment")
        if isinstance(deployment, dict):
            for key in ("flow_id", "flowId", "id", "uuid"):
                if key in deployment and isinstance(deployment[key], (str, int)):
                    return str(deployment[key])
    return None
