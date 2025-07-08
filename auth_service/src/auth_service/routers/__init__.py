"""
Exports the main API routers for the Authentication Service.

This allows the main application to import and include them with a clean path.
- user_auth_router: Handles public user-facing auth (login, register).
- token_router: Handles M2M token acquisition.
- admin_router: Aggregates all administrative endpoints.
"""

from .admin_routes import router as admin_router
from .health_routes import router as health_router
from .token_routes import router as token_router
from .user_auth_routes import router as user_auth_router

__all__ = ["admin_router", "health_router", "token_router", "user_auth_router"]
