# Agent Runtime Service (ARS)

## Overview

The Agent Runtime Service owns runtime provider integrations (e.g., Langflow) and all agent provisioning. It exposes a stable API used by the Conversation Service to resolve a runnable flow for a natural-language description. ADS (Agent Deployment Service) no longer handles provisioning.

## Key Capabilities

- Runtime provider integration (Langflow) with token bootstrap via `auto_login`.
- Provisioning API to discover/select a suitable flow for a task description.
- JWT-secured endpoints that accept either USER or M2M tokens.

## API

Base path is controlled by `AGENT_RUNTIME_SERVICE_ROOT_PATH` (default `/api/v1`).

- POST `{ROOT_PATH}/agents/provision`
  - Auth: Bearer JWT (USER or M2M)
  - Request body:
    ```json
    {
      "description": "summarize financial documents",
      "project_hint": "optional workspace hint"
    }
    ```
  - Response body:
    ```json
    {
      "flow_id": "<langflow-flow-id>",
      "matched": true,
      "source": "discovery",
      "note": null
    }
    ```
- GET `/health`
  - Liveness/readiness probe.

See implementation in `src/agent_runtime_service/routers/provisioning_routes.py` and schemas in `src/agent_runtime_service/schemas/provision_schemas.py`.

## Security

All APIs require a Bearer token parsed via `shared.security.jwt` with service-specific settings.
- USER JWT: `AGENT_RUNTIME_SERVICE_USER_JWT_*`
- M2M JWT: `AGENT_RUNTIME_SERVICE_M2M_JWT_*`

Dependency: `get_current_user_token_data()` in `dependencies/user_deps.py` validates either token type and returns claims.

## Configuration

Environment variables (see `src/agent_runtime_service/config.py`). Defaults shown where applicable:

- Service
  - `AGENT_RUNTIME_SERVICE_ENVIRONMENT=development`
  - `AGENT_RUNTIME_SERVICE_LOGGING_LEVEL=INFO`
  - `AGENT_RUNTIME_SERVICE_ROOT_PATH=/api/v1`
  - `AGENT_RUNTIME_SERVICE_CORS_ALLOW_ORIGINS=["*"]`
- JWT (M2M)
  - `AGENT_RUNTIME_SERVICE_M2M_JWT_SECRET_KEY`
  - `AGENT_RUNTIME_SERVICE_M2M_JWT_ALGORITHM=HS256`
  - `AGENT_RUNTIME_SERVICE_M2M_JWT_ISSUER`
  - `AGENT_RUNTIME_SERVICE_M2M_JWT_AUDIENCE`
- JWT (USER)
  - `AGENT_RUNTIME_SERVICE_USER_JWT_SECRET_KEY`
  - `AGENT_RUNTIME_SERVICE_USER_JWT_ALGORITHM=HS256`
  - `AGENT_RUNTIME_SERVICE_USER_JWT_ISSUER`
  - `AGENT_RUNTIME_SERVICE_USER_JWT_AUDIENCE`
- Providers
  - `AGENT_RUNTIME_SERVICE_LANGFLOW_API_URL=http://langflow_ide:7860`

## Local Development

- Use `docker-compose.dev.yml` in `agent_runtime_service/` or the root Compose to run ARS alongside Langflow IDE and other services.
- Ensure the JWT settings align with your `auth_service` configuration for local development.

## Provisioning Ownership

Provisioning is exclusively handled by ARS. Conversation Service calls ARS to resolve a `flow_id`. Agent Deployment Service (ADS) is not consulted and provides no provisioning endpoints.
