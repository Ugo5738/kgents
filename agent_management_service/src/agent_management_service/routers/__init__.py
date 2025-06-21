from fastapi import APIRouter

from agent_management_service.routers import agent_routes, version_routes, langflow_routes

# Main API router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(
    agent_routes.router,
    prefix="/agents",
    tags=["agents"]
)

api_router.include_router(
    version_routes.router,
    prefix="/agents/{agent_id}/versions",
    tags=["versions"]
)

api_router.include_router(
    langflow_routes.router,
    prefix="/langflow",
    tags=["langflow"]
)

__all__ = ["api_router"]
