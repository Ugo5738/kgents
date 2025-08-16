 # agent_deployment_service/src/agent_deployment_service/routers/langflow_routes.py
from __future__ import annotations

"""
Deprecated: Provisioning routes were removed from Agent Deployment Service.
Provisioning is exclusively handled by Agent Runtime Service (ARS) at
POST /api/v1/agents/provision.
"""

raise ImportError(
    "agent_deployment_service.routers.langflow_routes has been removed. "
    "Provisioning is now exclusively handled by Agent Runtime Service at "
    "POST /api/v1/agents/provision."
)
