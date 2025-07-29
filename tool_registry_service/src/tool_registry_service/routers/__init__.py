"""
Exports the main API routers for the Tool Registry Service.

This allows the main application to import and include them with a clean path.
- tool_router: Handles tools management.
- health_router: Handles health checks.
- execution_router: Handles tool executions.
- category_router: Handles tool categories management.
"""

from .category_routes import router as category_router
from .execution_routes import router as execution_router
from .health_routes import router as health_router
from .tool_routes import router as tool_router

__all__ = ["tool_router", "health_router", "execution_router", "category_router"]
