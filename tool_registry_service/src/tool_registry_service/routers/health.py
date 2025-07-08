"""
Health check endpoints for the Tool Registry Service.

These endpoints provide system health information and operational status
for monitoring and diagnostics.
"""

import logging
import time
from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from tool_registry_service.config import settings
from tool_registry_service.db import get_db

router = APIRouter(
    prefix="/health",
    tags=["health"],
)

logger = logging.getLogger(__name__)

start_time = time.time()


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    version: str
    uptime_seconds: float
    timestamp: datetime


class DatabaseHealthResponse(BaseModel):
    """Schema for database health check response."""

    status: str
    latency_ms: float
    connected: bool
    message: str


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Service health check",
    description="Returns the health status of the Tool Registry Service",
)
async def health_check():
    """
    Simple health check endpoint that returns service status and uptime.
    """
    current_time = time.time()
    uptime = current_time - start_time

    return {
        "status": "healthy",
        "version": settings.VERSION,
        "uptime_seconds": uptime,
        "timestamp": datetime.now(),
    }


@router.get(
    "/db",
    response_model=DatabaseHealthResponse,
    summary="Database health check",
    description="Checks database connectivity and returns health status",
)
async def db_health_check(db: AsyncSession = Depends(get_db)):
    """
    Database health check that tests connectivity and measures latency.
    """
    start = time.time()
    try:
        # Simple query to test database connectivity
        await db.execute(text("SELECT 1"))
        end = time.time()

        return {
            "status": "connected",
            "latency_ms": (end - start) * 1000,  # Convert to milliseconds
            "connected": True,
            "message": "Database connection successful",
        }
    except Exception as e:
        end = time.time()
        logger.error(f"Database health check failed: {str(e)}")

        return {
            "status": "error",
            "latency_ms": (end - start) * 1000,  # Convert to milliseconds
            "connected": False,
            "message": f"Database connection failed: {str(e)}",
        }
