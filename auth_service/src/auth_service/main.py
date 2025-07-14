import datetime
import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from supabase._async.client import AsyncClient as AsyncSupabaseClient

from .bootstrap import bootstrap_admin_and_rbac
from .config import settings
from .db import get_db
from .logging_config import LoggingMiddleware, logger, setup_logging, setup_middleware
from .rate_limiting import rate_limit_exceeded_handler, setup_rate_limiting
from .routers import admin_router, health_router, token_router, user_auth_router
from .supabase_client import close_supabase_clients
from .supabase_client import get_supabase_client as get_general_supabase_client
from .supabase_client import init_supabase_clients


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager with robust initialization.

    Handles startup and shutdown sequences with proper error handling and retry logic.
    Features:
    - Graceful initialization of Supabase clients
    - Resilient database connection for bootstrap process
    - Proper cleanup on application shutdown
    """
    app.logger.info(f"'{settings.PROJECT_NAME}' startup sequence initiated.")
    app.startup_time = time.time()

    # 1. Initialize app-wide resources (like the global Supabase client)
    try:
        await init_supabase_clients()
        logger.info("Supabase clients initialized successfully")
    except Exception as e:
        logger.error(
            f"Failed to initialize Supabase clients: {e.__class__.__name__}: {str(e)}"
        )

    # 2. Run bootstrap process with retry logic
    app.logger.info("Running bootstrap process...")
    try:
        async for session in get_db():
            # Use the session for bootstrap but don't close it here
            # bootstrap_admin_and_rbac manages its own transaction
            await bootstrap_admin_and_rbac(session)
            break
    except Exception as e:
        logger.error(f"Bootstrap process failed: {e}", exc_info=True)

    # Application is now ready to serve requests
    app.logger.info("Application startup complete.")

    # Yield control back to the application
    yield

    # --- Application Shutdown ---
    app.logger.info(f"{settings.PROJECT_NAME} shutdown sequence initiated.")

    # Close Supabase client connections
    try:
        await close_supabase_clients()
        app.logger.info("Supabase clients closed successfully.")
    except Exception as e:
        app.logger.error(f"Error closing Supabase clients: {str(e)}", exc_info=True)

    app.logger.info(f"{settings.PROJECT_NAME} shutdown sequence complete.")


# Configure logging before app initialization
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Authentication and Authorization service for managing users, application clients, roles, and permissions.",
    version="1.0.0",
    root_path=settings.ROOT_PATH,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "User Authentication",
            "description": "Operations for user authentication including login, registration, password management, and profile management.",
        },
        {
            "name": "Token Acquisition",
            "description": "Operations for obtaining authentication tokens for machine-to-machine (M2M) communication.",
        },
        {
            "name": "Admin - App Clients",
            "description": "Administrative operations for managing application clients.",
        },
        {
            "name": "Admin - Roles",
            "description": "Administrative operations for managing roles.",
        },
        {
            "name": "Admin - Permissions",
            "description": "Administrative operations for managing permissions.",
        },
        {
            "name": "Admin - Role Permissions",
            "description": "Administrative operations for assigning permissions to roles.",
        },
        {
            "name": "Admin - User Roles",
            "description": "Administrative operations for assigning roles to users.",
        },
        {
            "name": "Admin - Client Roles",
            "description": "Administrative operations for assigning roles to application clients.",
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


# --- Custom Exception Handlers ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    app.logger.error(f"HTTPException: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    app.logger.warning(f"Validation error for {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


# Use the handler from rate_limiting module
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# --- Include Service-Specific Routers ---
app.include_router(health_router)
app.include_router(user_auth_router)
app.include_router(token_router)
app.include_router(admin_router, prefix="/admin")  # The /admin prefix is applied here

# Add a logger attribute to the app for easy access in routes if needed
app.logger = logging.getLogger("auth_service")
