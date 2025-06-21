"""
Health check endpoints for the agent_management_service.

These endpoints are used by Kubernetes and other infrastructure
to determine if the service is healthy and ready to receive requests.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from agent_management_service.db import get_db
from agent_management_service.schemas.common import StatusResponse

router = APIRouter(tags=["health"])


@router.get("/liveness", response_model=StatusResponse)
async def liveness_check() -> StatusResponse:
    """
    Liveness probe for Kubernetes.
    
    This endpoint is used to determine if the service is running.
    It should return a 200 OK response if the service is alive.
    """
    return StatusResponse(status="ok", message="Service is alive")


@router.get("/readiness", response_model=StatusResponse)
async def readiness_check(db: AsyncSession = Depends(get_db)) -> StatusResponse:
    """
    Readiness probe for Kubernetes.
    
    This endpoint is used to determine if the service is ready to receive requests.
    It checks if the database connection is working properly.
    """
    try:
        # Test database connection
        query = text("SELECT 1")
        await db.execute(query)
        return StatusResponse(status="ok", message="Service is ready")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service is not ready: {str(e)}"
        )
