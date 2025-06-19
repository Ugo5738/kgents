# Kgents - Project Structure

## Overview

This repository follows a monorepo architecture for the collection of microservices that comprise the Kgents (Agent-as-a-Service) platform. Each service is designed to be independently deployable and scalable.

## Directory Structure

The directory structure is organized as follows:

```text
/kgents/                                  # Root directory
├── auth_service/                         # Handles users, auth, and API keys.
│   ├── src/
│   ├── tests/
│   ├── alembic/
│   └── README.md
├── agent_management_service/             # Handles CRUD for agent definitions.
│   ├── src/
│   ├── tests/
│   ├── alembic/
│   └── README.md
├── tool_registry_service/                # Manages custom tools.
│   ├── src/
│   ├── tests/
│   ├── alembic/
│   └── README.md
├── agent_deployment_service/             # Orchestrates agent deployment.
│   ├── src/
│   └── README.md
├── agent_runtime_service/                # Generic runtime for deployed agents.
│   ├── src/
│   └── README.md
├── k8s/                                  # Kubernetes manifests (shared across services)
│   ├── auth_service/
│   ├── agent_management_service/
│   └── shared/
├── docs/                                 # General documentation
│   ├── architecture/
│   └── deployment/
├── supabase/                             # Supabase migrations and configuration
└── docker-compose.yml                    # Local development orchestration
```
