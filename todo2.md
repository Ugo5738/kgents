# Project Todo List: Kgents (Agent-as-a-Service) Platform

This plan refactors the Kgents platform into a scalable, multi-service architecture, following the framework's principles. Each service will be built and deployed independently.

## Phase 1: Foundational `auth_service`

> **Goal:** Create the central authentication and authorization service, acting as the security backbone for the entire platform.

1.  **Initialize Service Structure & Configuration:**

    - Create directories: `auth_service/`, `auth_service/src/`, `auth_service/tests/`, `auth_service/alembic/`.
    - Create config files: `pyproject.toml`, `pytest.ini`, `gitignore`, `.dockerignore`, `pre-commit-config.yaml`.
    - Create environment files: `.env.example`, `.env.dev`, `.env.test`, `.env.prod`.
    - Create documentation stub: `auth_service/README.md` to document its purpose, API, and setup.

2.  **Setup Python Project with Poetry:**

    - Inside `auth_service/`, run `poetry new src`.
    - Configure `auth_service/pyproject.toml` with dependencies: `fastapi`, `uvicorn`, `pydantic-settings`, `sqlalchemy`, `psycopg3`, `passlib[bcrypt]`, `python-jose[cryptography]`, `supabase[async]`, `alembic`.
    - Add dev dependencies: `pytest`, `pytest-asyncio`, `httpx`.
    - Create a `auth_service/pytest.ini` file to configure test paths.
    - Run `poetry install` to generate `poetry.lock`.

3.  **Define Database Schema & Migrations:**

    - Create `auth_service/src/models.py` defining SQLAlchemy models for profiles, api_keys, app_clients, roles, permissions, all junction tables (user_roles, app_client_roles, role_permissions). `profiles` should link to `auth.users` via a foreign key.
    - Initialize Alembic in `auth_service/`: `alembic init alembic`.
    - Configure `auth_service/alembic.ini` and `auth_service/alembic/env.py` to connect to the Supabase database.
    - Generate the initial migration: `alembic revision --autogenerate -m "Initial user service schema"`.
    - Apply the migration: `alembic upgrade head`.

4.  **Implement Core Service Logic:**

    - Create `auth_service/src/main.py` with the FastAPI app instance, CORS, and rate limiting.
    - Implement a health check endpoint `/health`.
    - Implement auth_service/src/security.py with functions for:
      - Password hashing (passlib).
      - Human user JWT creation/validation (proxied via Supabase).
      - M2M JWT creation/validation (python-jose) for app_clients.
      - Client secret hashing and verification.
    - Set up Supabase client initialization in `auth_service/src/supabase_client.py`.

5.  **Build API Endpoints:**

    - **User Auth:** Create routes for `POST /auth/register` and `POST /auth/login` that proxy requests to Supabase.
    - **M2M Auth**: POST `/auth/token` for app_clients.
    - **Profile Management:** Create `GET /users/me` and `PUT /users/me` endpoints for users to manage their own profiles (protected by JWT).
    - **API Keys:** Implement endpoints for users to generate and revoke their own API keys (`POST /users/me/api-keys`, `GET /users/me/api-keys`, `DELETE /users/me/api-keys/{key_id}`).
    - **Admin RBAC:** Create admin-only endpoints for managing clients, roles, permissions and assignments (e.g., `POST /admin/roles`).

6.  **Write Tests:**
    - Create `auth_service/tests/` directory.
    - Write unit tests for security functions (hashing, JWT creation).
    - Write integration tests for all API endpoints, mocking Supabase calls where necessary.

---

## Phase 2: Agent & Tool Management Services

> **Goal:** Create the core services for managing agent definitions and custom tools. These services will be protected by the `auth_service`.

1.  **Initialize `agent_management_service` (2.1):**

    - Create directory: `agent_management_service/`.
    - Set up the project structure similarly to `auth_service` (Poetry, Dockerfile, `src`, `tests`).
    - Define SQLAlchemy models for agents (linking to `user_id`) and set up Alembic migrations.
    - Implement CRUD API endpoints for agents (`/agents`).

2.  **Initialize `tool_registry_service` (2.2):**

    - Create directory: `tool_registry_service/`.
    - Set up the project structure.
    - Define SQLAlchemy models for tools and set up Alembic migrations.
    - Implement CRUD API endpoints for tools (`/tools`).

3.  **Implement JWT Authentication Middleware (2.3):**

    - Create a shared dependency or middleware that other services (`agent_management_service`, `tool_registry_service`) can use.
    - This middleware will call the `auth_service` (or use a shared public key) to validate incoming JWTs and extract the `user_id`.
    - Protect all `agent_management_service` and `tool_registry_service` endpoints with this authentication middleware.

4.  **Write Integration Tests for Cross-Service Auth (2.4):**
    - Write tests that simulate a user logging into `auth_service`, getting a token, and then using that token to access endpoints in the `agent_management_service`.

---

## Phase 3: Deployment & Langflow Integration

> **Goal:** Get the core services and the Langflow IDE running in a containerized environment and establish the workflow for agent creation.

1.  **Finalize Dockerization (3.1):**

    - Create production-ready, multi-stage Dockerfiles for each service.
    - Update `docker-compose.yml` to use the production Dockerfiles and handle environment variables securely.

2.  **Set Up Kubernetes Manifests (3.2):**

    - Create a `k8s/` directory at the project root.
    - For each service, create `deployment.yaml`, `service.yaml`, and `ingress.yaml` files.
    - Create a `k8s/shared/` directory for shared resources like `ClusterIssuer` for TLS certificates.
    - Parameterize image tags and domains for easy configuration in a CI/CD pipeline.

3.  **Build CI/CD Pipeline (3.3):**

    - Create a GitHub Actions workflow (`.github/workflows/deploy.yml`).
    - The workflow should have separate jobs to build and push Docker images for each service that has changed.
    - A final job should apply the Kubernetes manifests to deploy the updated services.

4.  **Integrate Langflow with Backend (3.4):**
    - The `agent_management_service` will be responsible for storing the JSON representation of flows created in the Langflow IDE.
    - The `tool_registry_service` will provide custom tools that can be surfaced within Langflow.
    - This step involves connecting the Langflow frontend's "Export" functionality to the `POST /agents` endpoint.

---

## Phase 4: Advanced Features & Production Readiness

> **Goal:** Implement the remaining features from the PRD and harden the platform for production use.

1.  **Build `agent_deployment_service` (4.1):**

    - This service will listen for "agent published" events (e.g., via a message queue or a direct API call from the `agent_management_service`).
    - It will be responsible for taking an agent's Langflow JSON, packaging it into a runtime container, and deploying it to Kubernetes.

2.  **Build `agent_runtime_service` (4.2):**

    - Develop the generic runtime environment that will execute the deployed agents.
    - This service will handle incoming requests to an agent's endpoint, manage its memory (connecting to Supabase `pgvector`), and execute its logic.

3.  **Implement Natural Language Agent Creation (4.3):**

    - Create a new `nl_agent_service`.
    - This service will have an endpoint that accepts a natural language description, uses an LLM (like GPT-4o) to generate a Langflow JSON structure, and saves it via the `agent_management_service`.

4.  **Harden Security (4.4):**

    - Implement WAF (Web Application Firewall) at the ingress level.
    - Integrate a secure secret management solution (e.g., AWS Secrets Manager, HashiCorp Vault).
    - Conduct a full security review of all services and their dependencies.

5.  **Set Up Observability (4.5):**
    - Integrate LangSmith and/or Langfuse into the `agent_runtime_service` for detailed tracing of agent behavior.
    - Configure Prometheus and Grafana for collecting and visualizing metrics from all services.
    - Ensure all services output structured (JSON) logs for effective aggregation and analysis.
