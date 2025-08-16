# agent_runtime_service/src/agent_runtime_service/routers/provisioning_routes.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from ..config import settings
from ..dependencies.user_deps import get_current_user_token_data
from ..logging_config import logger
from ..schemas.provision_schemas import ProvisionRequest, ProvisionResponse

router = APIRouter(
    prefix="/agents",
    tags=["Runtime Provisioning"],
    dependencies=[Depends(get_current_user_token_data)],
)


async def _get_langflow_token(client: httpx.AsyncClient) -> Optional[str]:
    try:
        resp = await client.get(f"{settings.LANGFLOW_API_URL.rstrip('/')}/api/v1/auto_login", timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token")
            if isinstance(token, str) and token:
                return token
            logger.warning("Langflow auto_login did not return access_token")
            return None
        logger.warning("Langflow auto_login failed: %s", resp.status_code)
        return None
    except Exception as e:
        logger.warning("Langflow auto_login error: %s", e)
        return None


def _extract_flows_schema(data: Any) -> List[Dict[str, Any]]:
    """Normalize various list-like flow payloads to a list of dicts.
    Accepts shapes like {flows:[...]}, {items:[...]}, {data:[...]}, list, or {result:[...]}."""
    candidates: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        for key in ("flows", "items", "data", "nodes"):
            val = data.get(key)
            if isinstance(val, list) and val and isinstance(val[0], dict):
                candidates = val  # type: ignore[assignment]
                break
        if not candidates and isinstance(data.get("result"), list):
            result = data["result"]
            if result and isinstance(result[0], dict):
                candidates = result  # type: ignore[assignment]
    elif isinstance(data, list):
        if data and isinstance(data[0], dict):
            candidates = data  # type: ignore[assignment]
    return candidates


def _extract_name_and_id(flow: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    name = None
    for nk in ("name", "title", "label"):
        if isinstance(flow.get(nk), str):
            name = flow[nk]
            break
    fid = None
    for ik in ("id", "uuid", "flow_id", "_id"):
        if flow.get(ik) is not None:
            fid = str(flow[ik])
            break
    return name, fid


def _select_flow_id(flows: List[Dict[str, Any]], description: str) -> Optional[str]:
    if not flows:
        return None
    # Simple heuristic: pick the first whose name appears to match description tokens
    desc = description.lower()
    scored: List[Tuple[int, str]] = []
    for f in flows:
        name, fid = _extract_name_and_id(f)
        if not fid:
            continue
        score = 0
        if name:
            nlow = name.lower()
            # naive scoring
            for token in desc.split():
                if len(token) >= 3 and token in nlow:
                    score += 1
        scored.append((score, fid))
    if not scored:
        # fallback: first with any id
        for f in flows:
            _, fid = _extract_name_and_id(f)
            if fid:
                return fid
        return None
    # choose highest score, then preserve original order by max
    scored.sort(key=lambda t: t[0], reverse=True)
    return scored[0][1]


@router.post(
    "/provision",
    response_model=ProvisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Provision or select a Langflow flow by natural language description",
    description=(
        "Returns a flow_id from Langflow by discovering available flows and applying "
        "a simple heuristic based on the provided description."
    ),
)
async def provision_flow(payload: ProvisionRequest) -> ProvisionResponse:
    # Authenticate to Langflow API
    async with httpx.AsyncClient() as client:
        token = await _get_langflow_token(client)
        if not token:
            raise HTTPException(status_code=503, detail="Langflow authentication unavailable")
        headers = {"Authorization": f"Bearer {token}"}

    base = settings.LANGFLOW_API_URL.rstrip("/")
    urls = [
        f"{base}/api/v1/flows",
        f"{base}/api/v1/flow",
        f"{base}/api/v1/projects/default/flows",
    ]

    flows: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
        for url in urls:
            try:
                resp = await client.get(url)
                if 200 <= resp.status_code < 300:
                    data = resp.json()
                    flows = _extract_flows_schema(data)
                    if flows:
                        break
            except Exception as e:
                logger.debug("Langflow discovery error %s: %s", url, e)
                continue

    if not flows:
        raise HTTPException(status_code=404, detail="No flows discovered in Langflow")

    flow_id = _select_flow_id(flows, payload.description)
    if not flow_id:
        raise HTTPException(status_code=404, detail="Unable to select a suitable flow")

    return ProvisionResponse(flow_id=flow_id, matched=True, source="discovery")
