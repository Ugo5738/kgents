# agent_deployment_service/src/agent_deployment_service/routers/__init__.py
"""
Exports the main API routers for the Agent Deployment Service.

This allows the main application to import and include them with a clean path.
- deployment_router: Handles agent deployment and lifecycle management.
- health_router: Handles service health checks.
"""

from .deployment_routes import router as deployment_router
from .health_routes import router as health_router

__all__ = [
    "deployment_router",
    "health_router",
]
