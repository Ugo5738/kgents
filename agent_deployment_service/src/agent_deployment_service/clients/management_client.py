# agent_deployment_service/src/agent_deployment_service/clients/management_client.py
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from ..config import settings
from ..logging_config import logger

# This will be our token cache
m2m_token: str | None = None


async def get_m2m_token() -> str:
    """Gets an M2M token from the auth_service, caching it."""
    global m2m_token
    # In a real app, you'd check token expiration before reusing
    if m2m_token:
        return m2m_token

    auth_url = f"{settings.AUTH_SERVICE_URL}/api/v1/auth/token"
    token_payload = {
        "grant_type": "client_credentials",
        "client_id": settings.DEPLOYMENT_SERVICE_CLIENT_ID,
        "client_secret": settings.DEPLOYMENT_SERVICE_CLIENT_SECRET,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(auth_url, json=token_payload)
            response.raise_for_status()
            m2m_token = response.json()["access_token"]
            return m2m_token
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get M2M token: {e.response.text}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not authenticate with auth service.",
            )


async def get_agent_version_config(agent_id: UUID, version_id: UUID) -> dict:
    """Fetches a specific agent version's config from the agent_management_service."""
    token = await get_m2m_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{settings.AGENT_MANAGEMENT_SERVICE_URL}/api/v1/agents/{agent_id}/versions/{version_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to fetch agent config for version {version_id}: {e.response.text}"
            )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Could not fetch agent configuration: {e.response.json().get('detail')}",
            )
