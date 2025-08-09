"""
Service layer package.

Keep this package lightweight to avoid importing heavy optional dependencies
like Docker or cloud SDKs during test collection. Import submodules directly
where needed, e.g.:

    from agent_deployment_service.services import orchestration_service
    from agent_deployment_service.services import strategies

This avoids side effects from eager imports in this package __init__.
"""

# Intentionally do not import submodules here to prevent side effects at
# import time (e.g., importing Docker client during test collection).

__all__ = []
