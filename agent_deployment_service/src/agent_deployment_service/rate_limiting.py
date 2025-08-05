import os
from typing import Optional

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from agent_deployment_service.config import settings

from .logging_config import logger

# Default rate limits
DEFAULT_GENERAL_RATE_LIMIT = os.environ.get(
    "AGENT_DEPLOYMENT_SERVICE_GENERAL_RATE_LIMIT", "100/minute"
)
DEFAULT_AGENT_CREATE_RATE_LIMIT = os.environ.get(
    "AGENT_DEPLOYMENT_SERVICE_AGENT_CREATE_RATE_LIMIT", "10/minute"
)
DEFAULT_AGENT_UPDATE_RATE_LIMIT = os.environ.get(
    "AGENT_DEPLOYMENT_SERVICE_AGENT_UPDATE_RATE_LIMIT", "20/minute"
)
DEFAULT_VERSION_CREATE_RATE_LIMIT = os.environ.get(
    "AGENT_DEPLOYMENT_SERVICE_VERSION_CREATE_RATE_LIMIT", "30/minute"
)
DEFAULT_LANGFLOW_IMPORT_RATE_LIMIT = os.environ.get(
    "AGENT_DEPLOYMENT_SERVICE_LANGFLOW_IMPORT_RATE_LIMIT", "5/minute"
)

# Determine if we're in test mode by checking if pytest is running
# This is a safer approach than relying on environment variables
import sys

IS_TEST_MODE = "pytest" in sys.modules


# In test mode, we'll use a no-op limiter to avoid affecting tests
def get_limiter_key(request: Request):
    if IS_TEST_MODE:
        # In test mode, give each request a unique key to effectively disable rate limiting
        import uuid

        return str(uuid.uuid4())
    # In normal mode, use the client IP
    return get_remote_address(request)


# Create a limiter instance
limiter = Limiter(
    key_func=get_limiter_key,
    default_limits=[DEFAULT_GENERAL_RATE_LIMIT],
    strategy="fixed-window",  # "moving-window" is more accurate but more resource-intensive
)

# Create a no-op version of the limit decorator for tests
if IS_TEST_MODE:
    # Store the original limit method
    original_limit = limiter.limit

    # Replace with a version that doesn't actually rate limit in tests
    def noop_limit(limit_string, key_func=None):
        def decorator(func):
            # Just return the original function without rate limiting
            # but mark it so we can verify the decorator was applied in tests
            func.__slowapi_decorated__ = True
            return func

        return decorator

    # Replace the limit method
    limiter.limit = noop_limit
    logger.info("Rate limiting disabled for test environment")

# Define specific rate limits for sensitive endpoints
AGENT_CREATE_LIMIT = DEFAULT_AGENT_CREATE_RATE_LIMIT
AGENT_UPDATE_LIMIT = DEFAULT_AGENT_UPDATE_RATE_LIMIT
VERSION_CREATE_LIMIT = DEFAULT_VERSION_CREATE_RATE_LIMIT
LANGFLOW_IMPORT_LIMIT = DEFAULT_LANGFLOW_IMPORT_RATE_LIMIT


# Custom rate limit exceeded handler
async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Custom handler for rate limit exceeded exceptions"""
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded", "retry_after": exc.retry_after},
    )


def setup_rate_limiting(app):
    """Configure rate limiting for the FastAPI application"""
    # Set the limiter on the app state
    app.state.limiter = limiter

    # Log whether we're in test mode
    if IS_TEST_MODE:
        logger.info("Rate limiting is disabled in test mode")
    else:
        logger.info(
            f"Rate limiting is enabled with the following limits: "
            f"AgentCreate={AGENT_CREATE_LIMIT}, "
            f"AgentUpdate={AGENT_UPDATE_LIMIT}, "
            f"VersionCreate={VERSION_CREATE_LIMIT}, "
            f"LangflowImport={LANGFLOW_IMPORT_LIMIT}"
        )

    # Add rate limiting middleware
    app.add_middleware(SlowAPIMiddleware)

    # Add exception handler for rate limit exceeded
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
