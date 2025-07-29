# tool_registry_service/src/tool_registry_service/routers/health.py
import datetime
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/liveness", summary="Checks if the service is running")
async def liveness_check():
    """
    Liveness probe for Kubernetes.

    This endpoint is used to determine if the service is running.
    It should return a 200 OK response if the service is alive.
    """
    return {"status": "alive", "service": settings.PROJECT_NAME}


@router.get("/readiness", summary="Checks if the service is ready to accept traffic")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe for Kubernetes.

    This endpoint is used to determine if the service is ready to receive requests.
    It checks if the database connection is working properly.
    """
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_ok = False
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"database": f"error - {e.__class__.__name__}"},
        )

    return {"status": "ready", "dependencies": {"database": "ok"}}


@router.get("/diagnostics", include_in_schema=False)
async def db_diagnostics(db: AsyncSession = Depends(get_db)):
    """
    Provides a comprehensive database diagnostic check. Intended for operators.
    """
    start_time = time.time()
    results = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "tests": {},
        "connection_pool": {},
        "success": False,
    }

    # Test 1: Basic connectivity
    try:
        basic_start = time.time()
        await db.execute(text("SELECT 1"))
        basic_time = time.time() - basic_start
        results["tests"]["basic_connectivity"] = {
            "status": "ok",
            "time_ms": round(basic_time * 1000, 2),
        }
    except Exception as e:
        results["tests"]["basic_connectivity"] = {
            "status": "error",
            "error": f"{e.__class__.__name__}: {str(e)}",
        }
        return results

    # Test 2: Database version
    try:
        result = await db.execute(text("SELECT version()"))
        version = result.scalar_one_or_none()
        results["tests"]["version_check"] = {"status": "ok", "version": version}
    except Exception as e:
        results["tests"]["version_check"] = {
            "status": "error",
            "error": f"{e.__class__.__name__}: {str(e)}",
        }

    # Test 3: Connection pool stats
    try:
        pool = db.bind.pool
        results["connection_pool"] = {
            "class": pool.__class__.__name__,
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }
    except Exception as e:
        results["connection_pool"] = {
            "error": f"Could not retrieve pool stats: {str(e)}"
        }

    results["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
    results["success"] = True
    return results
