import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from .config import settings
from .logging_config import setup_logging, setup_middleware
from .routers import conversations_router, health_router, ws_router


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
    description=(
        "Real-time conversation service with WebSocket streaming, "
        "multi-agent orchestration hooks, and Langflow runtime integration."
    ),
    version="0.1.0",
    root_path=settings.ROOT_PATH,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Health", "description": "Service health endpoints"},
        {"name": "Conversations", "description": "Conversation CRUD and messages"},
        {"name": "WebSocket", "description": "Real-time conversation streaming"},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True},
)

# Initialize application logger
app.logger = logging.getLogger("conversation_service")

# Setup middleware
setup_middleware(app)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# Note: rate limiting hooks could be added here if SlowAPI is configured globally.
app.add_exception_handler(RateLimitExceeded, lambda r, e: JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"}))

# Routers
app.include_router(health_router)
app.include_router(conversations_router)
app.include_router(ws_router)
