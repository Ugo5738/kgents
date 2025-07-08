import httpx
from fastapi import HTTPException, status

from ..config import settings


async def validate_langflow_instance():
    """
    Check if the configured Langflow instance is reachable.

    Raises:
        HTTPException: If Langflow instance is not configured or unreachable
    """
    if not settings.LANGFLOW_API_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Langflow integration is not configured",
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.LANGFLOW_API_URL.rstrip('/')}/health", timeout=5.0
            )

        response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Langflow instance is not available: {e.__class__.__name__}",
        )
