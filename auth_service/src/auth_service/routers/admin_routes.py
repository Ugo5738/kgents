# auth_service/src/routers/admin_routes.py
from fastapi import APIRouter, Depends

from ..dependencies import require_admin_user
from ._admin_client_role_routes import router as client_role_router
from ._admin_client_routes import router as client_router
from ._admin_permission_routes import router as permission_router
from ._admin_role_permission_routes import router as role_permission_router
from ._admin_role_routes import router as role_router
from ._admin_user_role_routes import router as user_role_router

# This is the main router for all /admin endpoints
# It enforces admin authentication for every route included below.
router = APIRouter(dependencies=[Depends(require_admin_user)])


# Include each sub-router with its own specific prefix
router.include_router(client_router, prefix="/clients", tags=["Admin - App Clients"])
router.include_router(role_router, prefix="/roles", tags=["Admin - Roles"])
router.include_router(
    permission_router, prefix="/permissions", tags=["Admin - Permissions"]
)
router.include_router(user_role_router, prefix="/users", tags=["Admin - User Roles"])
router.include_router(
    client_role_router, prefix="/clients", tags=["Admin - Client Roles"]
)
router.include_router(
    role_permission_router, prefix="/roles", tags=["Admin - Role Permissions"]
)
