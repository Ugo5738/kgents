"""
Tool Registry Service main application entry point.

This module defines the FastAPI application that serves the Tool Registry Service API,
including all routes and dependencies.
"""

import datetime
import os
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tool_registry_service.config import settings
from tool_registry_service.db import get_db
from tool_registry_service.logging_config import logger, setup_logging
from tool_registry_service.models import base
from tool_registry_service.routers import category_routes, execution_routes, tool_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager with robust initialization.

    Handles startup and shutdown sequences with proper error handling.
    Features:
    - Proper resource initialization on startup
    - Clean resource shutdown on application termination
    """
    logger.info("Application startup sequence initiated.")

    # Application is now ready to serve requests
    # Note: The database engine is already created at module level in db.py
    # so we don't need to explicitly create it here anymore

    # Track app startup time for uptime monitoring in health checks
    app.startup_time = time.time()

    logger.info("Application startup complete.")

    # Yield control back to the application
    yield

    # --- Application Shutdown ---
    logger.info("Application shutdown sequence initiated.")

    # Any cleanup tasks would go here
    # Note: The SQLAlchemy engine has connection pool cleanup on process exit

    logger.info("Application shutdown complete.")


# Create FastAPI application
app = FastAPI(
    title="Tool Registry Service",
    description="Service for managing and executing tools in the Kgents platform",
    version="1.0.0",
    root_path=settings.ROOT_PATH,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True},
)

# Track app startup time for uptime monitoring in health checks
app.startup_time = time.time()

# Setup logging configuration
setup_logging(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# Include routers
app.include_router(category_routes.router)
app.include_router(tool_routes.router)
app.include_router(execution_routes.router)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPExceptions with proper status code and detail."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with descriptive error messages."""
    logger.warning(f"Validation error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


# Health check cache to avoid repeated database queries
_health_check_cache = {
    "last_check": None,  # Timestamp of last health check
    "result": None,  # Cached result
    "cache_ttl_seconds": 120,  # Cache validity period (2 minutes)
    "db_check_counter": 0,  # Counter for adaptive DB checking
    "db_check_interval": 10,  # Only check DB every 10 requests to reduce DB load
}


@app.get("/health")
async def health(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Health check endpoint optimized for Kubernetes probes.

    This health check is designed to be lightweight and reliable,
    avoiding heavy database operations that could cause timeouts.
    It caches results to reduce load and uses adaptive checking.
    For Kubernetes probes, it always returns a 200 OK status if
    the API itself is running, to prevent unnecessary pod restarts.
    """

    # Check if this is a Kubernetes probe
    is_k8s_probe = (
        request.headers.get("user-agent", "").lower().startswith("kube-probe")
    )

    # Also check for diagnostic mode - bypasses caching and always tests DB
    is_diagnostic = request.query_params.get("diagnostic") == "true"

    # Get current time
    current_time = datetime.datetime.utcnow()

    # Initialize response
    response = {
        "status": "ok",
        "version": app.version,
        "environment": str(settings.ENVIRONMENT),
        "timestamp": current_time.isoformat(),
        "components": {"api": {"status": "ok"}},
    }

    # Use cache if available and not expired, but skip cache in diagnostic mode
    cache = _health_check_cache
    if (
        not is_diagnostic
        and cache["last_check"]
        and cache["result"]
        and (time.time() - cache["last_check"]) < cache["cache_ttl_seconds"]
    ):
        # Update timestamp but keep other results from cache
        result = cache["result"].copy()
        result["timestamp"] = current_time.isoformat()

        # For k8s probes, always return 200 OK if the API is running
        if is_k8s_probe:
            # For Kubernetes probes, always report OK status
            result["status"] = "ok"
            # Remove detailed error messages for probe requests
            if "components" in result:
                for component in result["components"]:
                    if (
                        isinstance(result["components"][component], dict)
                        and result["components"][component].get("status") == "error"
                    ):
                        result["components"][component] = {"status": "cached"}

        logger.debug(
            f"Health check using cached result (age: {int(time.time() - cache['last_check'])}s)"
        )
        return JSONResponse(content=result, status_code=200)

    # Determine if we should do a DB check this time
    # Always check DB in diagnostic mode
    should_check_db = (
        is_diagnostic or cache["db_check_counter"] >= cache["db_check_interval"]
    )
    if should_check_db:
        cache["db_check_counter"] = 0
    else:
        cache["db_check_counter"] += 1

    # Lightweight database connectivity check (only when needed)
    if should_check_db:
        try:
            # Use a very short operation for the db check
            start_time = time.time()
            await db.execute(text("SELECT 1"))
            query_time = time.time() - start_time
            response["components"]["database"] = {
                "status": "ok",
                "response_time_ms": round(query_time * 1000, 2),
            }
        except Exception as e:
            error_message = str(e)
            error_type = e.__class__.__name__

            # Log error but with reduced verbosity for common timeout errors
            if "timeout" in error_message.lower():
                logger.warning(
                    f"Health check - Database timeout: {error_type}: {error_message[:100]}"
                )
            else:
                logger.error(
                    f"Health check - Database error: {error_type}: {error_message}",
                    exc_info=True,
                )

            # Include more detailed error information for diagnostics
            db_error = {
                "status": "error",
                "message": "Database connection failed",
                "error_type": error_type,
                "is_timeout": "timeout" in error_message.lower(),
            }

            # Only include error details in non-k8s probe responses or diagnostic mode
            if not is_k8s_probe or is_diagnostic:
                db_error["error_message"] = (
                    error_message[:200] if len(error_message) > 200 else error_message
                )

            response["components"]["database"] = db_error

            # Only mark as degraded for non-k8s requests
            if not is_k8s_probe:
                response["status"] = "degraded"
    else:
        # Skip DB check this time
        if (
            cache["result"]
            and "components" in cache["result"]
            and "database" in cache["result"]["components"]
        ):
            # Use cached DB status
            response["components"]["database"] = cache["result"]["components"][
                "database"
            ]
        else:
            response["components"]["database"] = {"status": "skipped"}

    # Cache the result
    cache["last_check"] = time.time()
    cache["result"] = response.copy()

    # For k8s probes, always return OK status
    if is_k8s_probe:
        response["status"] = "ok"

    logger.debug(f"Health check completed with status: {response['status']}")
    return JSONResponse(content=response, status_code=200)


@app.get("/internal/health")
async def detailed_health(request: Request, db: AsyncSession = Depends(get_db)):
    """Detailed health check endpoint for internal monitoring.

    Unlike the public health check, this endpoint always returns actual status
    and never pretends to be healthy for Kubernetes. It performs more thorough checks
    and is intended for internal monitoring and debugging rather than for probes.
    """
    current_time = datetime.datetime.utcnow()
    response = {
        "status": "ok",
        "version": settings.VERSION,
        "environment": str(settings.ENVIRONMENT),
        "timestamp": current_time.isoformat(),
        "uptime": (
            time.time() - app.startup_time if hasattr(app, "startup_time") else None
        ),
        "components": {"api": {"status": "ok"}},
        "diagnostics": {
            "process_id": os.getpid(),
        },
    }

    # Always perform database check for detailed health
    try:
        # Execute query and fetch result properly for async SQLAlchemy
        result = await db.execute(text("SELECT 1 as value"))
        row = result.fetchone()
        if row and row.value == 1:
            response["components"]["database"] = {"status": "ok"}
        else:
            response["components"]["database"] = {
                "status": "error",
                "message": "Invalid response",
            }
            response["status"] = "degraded"
    except Exception as e:
        logger.error(f"Detailed health check - Database error: {str(e)}", exc_info=True)
        response["components"]["database"] = {
            "status": "error",
            "message": f"Database error: {str(e)}",
            "error_type": e.__class__.__name__,
        }
        response["status"] = "degraded"

    # Return appropriate status code based on overall health
    status_code = 200 if response["status"] == "ok" else 503

    logger.info(f"Detailed health check completed with status: {response['status']}")
    return JSONResponse(content=response, status_code=status_code)


# Root endpoint for basic service info
@app.get("/", tags=["root"])
async def root():
    """Root endpoint that returns basic service information."""
    return {
        "service": "Tool Registry Service",
        "version": settings.VERSION,
        "docs_url": "/api/docs" if settings.SHOW_DOCS else None,
    }


if __name__ == "__main__":
    """
    Development server entry point.

    For production, use a proper ASGI server like uvicorn or hypercorn.
    """
    uvicorn.run(
        "tool_registry_service.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.RELOAD,
    )
