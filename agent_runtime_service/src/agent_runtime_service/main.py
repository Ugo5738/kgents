import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import settings
from .logging_config import setup_logging, setup_middleware
from .routers import health_router, provisioning_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.logger.info(f"'{settings.PROJECT_NAME}' startup sequence initiated.")
    app.startup_time = time.time()
    yield
    app.logger.info(f"'{settings.PROJECT_NAME}' shutdown sequence initiated.")


# Configure logging before app initialization
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Service for runtime provider integrations (e.g., Langflow) and provisioning.",
    version="1.0.0",
    root_path=settings.ROOT_PATH,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Runtime Provisioning",
            "description": "Operations for provisioning/selecting runtime provider artifacts.",
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


# --- Include API routers ---
app.include_router(health_router)
app.include_router(provisioning_router)

# App logger alias
app.logger = logging.getLogger("agent_runtime_service")
