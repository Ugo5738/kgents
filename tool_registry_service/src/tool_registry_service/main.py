"""
Tool Registry Service main application entry point.

This module defines the FastAPI application that serves the Tool Registry Service API,
including all routes and dependencies.
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_db
from .logging_config import logger, setup_logging, setup_middleware
from .routers import category_router, execution_router, health_router, tool_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager with robust initialization.

    Handles startup and shutdown sequences with proper error handling.
    Features:
    - Proper resource initialization on startup
    - Clean resource shutdown on application termination
    """
    app.logger.info(f"'{settings.PROJECT_NAME}' startup sequence initiated.")
    app.startup_time = time.time()

    # Add any startup logic here in the future
    # Yield control back to the application
    yield

    # --- Application Shutdown ---
    # Add any shutdown logic here
    app.logger.info(f"'{settings.PROJECT_NAME}' shutdown sequence initiated.")


# Configure logging before app initialization
setup_logging()

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Service for managing and executing tools in the Kgents platform",
    version="1.0.0",
    root_path=settings.ROOT_PATH,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True},
)

# Initialize application logger
app.logger = logging.getLogger(settings.PROJECT_NAME)

# Setup middleware - MUST be done before application starts
setup_middleware(app)


# --- Custom Exception Handlers ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    app.logger.error(f"HTTPException: {exc.status_code} - {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    app.logger.warning(f"Validation error for {request.url.path}: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# --- Service-Specific Routers ---
app.include_router(health_router)
app.include_router(category_router)
app.include_router(tool_router)
app.include_router(execution_router)


@app.get("/", tags=["root"], include_in_schema=False)
async def root():
    """Root endpoint for basic service information."""
    return {"service": settings.PROJECT_NAME, "version": "1.0.0"}
