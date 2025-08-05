"""
This package contains reusable dependencies for the Agent Deployment Service.

By importing the main dependency functions here, we provide a stable access point
for our routers, abstracting away the internal module structure (e.g., user_deps.py).
"""

from agent_deployment_service.dependencies.app_deps import get_app_settings
from agent_deployment_service.dependencies.user_deps import (
    get_current_user_id,
    get_current_user_token_data,
)

# List defines the public API of this package.
__all__ = [
    "get_app_settings",
    "get_current_user_id",
    "get_current_user_token_data",
]
