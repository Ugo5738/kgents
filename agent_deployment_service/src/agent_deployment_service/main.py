import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from .config import settings
from .logging_config import setup_logging, setup_middleware
from .rate_limiting import rate_limit_exceeded_handler, setup_rate_limiting
from .routers import deployment_router, health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager with robust initialization.

    Handles startup and shutdown sequences with proper error handling and retry logic.
    """
    app.logger.info(f"'{settings.PROJECT_NAME}' startup sequence initiated.")
    app.startup_time = time.time()

    # Yield control back to the application
    yield

    # --- Application Shutdown ---
    app.logger.info(f"'{settings.PROJECT_NAME}' shutdown sequence initiated.")


# Configure logging before app initialization
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Service for deploying and managing the lifecycle of AI agents.",
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
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True},
)

# Initialize application logger
app.logger = logging.getLogger(settings.PROJECT_NAME)

# Setup middleware - MUST be done before application starts
setup_middleware(app)

# Setup rate limiting
setup_rate_limiting(app)


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


# Use the handler from rate_limiting module
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# --- Include API routers - all protected by default ---
app.include_router(deployment_router)
app.include_router(health_router)

# Add a logger attribute to the app for easy access in routes if needed
app.logger = logging.getLogger("agent_deployment_service")
