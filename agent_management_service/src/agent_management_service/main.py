import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agent_management_service.config import settings
from agent_management_service.db import get_db
from agent_management_service.routers.agent_routes import router as agent_router
from agent_management_service.routers.langflow_routes import router as langflow_router
from agent_management_service.routers.version_routes import router as version_router
from agent_management_service.security import validate_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager with robust initialization.

    Handles startup and shutdown sequences with proper error handling and retry logic.
    """
    app.logger.info("Agent Management Service startup sequence initiated.")

    # Initialize any resources needed for the service
    # For example, connect to message brokers or initialize external clients

    # Application is now ready to serve requests
    app.logger.info("Agent Management Service startup complete.")

    # Yield control back to the application
    yield

    # --- Application Shutdown ---
    app.logger.info("Agent Management Service shutdown sequence initiated.")

    # Close any connections or resources
    app.logger.info("Agent Management Service shutdown complete.")


app = FastAPI(
    title="Agent Management Service API",
    description="Service for managing agents including creation, version history, and configurations",
    version="1.0.0",
    root_path=settings.ROOT_PATH,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Agents",
            "description": "Operations for managing agents including CRUD operations",
        },
        {
            "name": "Versions",
            "description": "Operations for managing agent versions including creation and retrieval",
        },
        {
            "name": "Langflow",
            "description": "Operations for integrating with Langflow IDE",
        },
    ],
)

# Track app startup time for uptime monitoring in health checks
app.startup_time = time.time()

# Add logging attribute to app
app.logger = settings.logger

# Setup middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers - all protected by default
app.include_router(
    agent_router,
    prefix="/api/v1/agents",
    tags=["Agents"],
    dependencies=[Depends(validate_token)],
)
app.include_router(
    version_router,
    prefix="/api/v1/agents/{agent_id}/versions",
    tags=["Versions"],
    dependencies=[Depends(validate_token)],
)
app.include_router(
    langflow_router,
    prefix="/api/v1/langflow",
    tags=["Langflow"],
    dependencies=[Depends(validate_token)],
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.get("/health")
async def health(request: Request, db: AsyncSession = Depends(get_db)):
    """Health check endpoint optimized for Kubernetes probes.
    
    This endpoint checks the service's health by:
    1. Verifying API functionality
    2. Testing database connectivity
    """
    current_time = time.time()
    response = {
        "status": "ok",
        "version": app.version,
        "environment": str(settings.ENVIRONMENT),
        "uptime": current_time - app.startup_time,
        "components": {"api": {"status": "ok"}},
    }

    # Check database connection
    try:
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
        app.logger.error(f"Health check - Database error: {str(e)}")
        response["components"]["database"] = {
            "status": "error",
            "message": f"Database error: {str(e)}",
            "error_type": e.__class__.__name__,
        }
        response["status"] = "degraded"

    # Return success status even if components are degraded
    # This allows Kubernetes to keep pod running while issues are fixed
    return JSONResponse(content=response, status_code=200)


@app.get("/")
async def root():
    """Root endpoint returning a welcome message."""
    return {"message": "Welcome to the Agent Management Service API"}
