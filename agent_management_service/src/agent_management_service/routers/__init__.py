"""
Exports the main API routers for the Agent Management Service.
"""

from .agent_routes import router as agent_router
from .health_routes import router as health_router
from .langflow_routes import router as langflow_router
from .version_routes import router as version_router

__all__ = ["agent_router", "version_router", "langflow_router", "health_router"]
