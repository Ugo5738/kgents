# Project Todo List: Agent-as-a-Service Platform

This document outlines the step-by-step plan for developing and deploying the AaaS platform. Follow the vibe coding principles outlined in `./.cursor/rules.md`.

## Phase 1: Foundation & Core Services (MVP)

### 1.1. Project Setup & Initial Environment

- [x] **Initialize Git Repository:**
  - `git init` in project root.
  - **Cursor AI:** Ask Cursor: "Generate a comprehensive `.gitignore` for a Python FastAPI project with a frontend, including common AI/LLM-related temporary files and environment variables."
  - **Cursor AI:** Ask Cursor: "Generate a README.md for an Agent-as-a-Service platform. Include sections for project overview, tech stack (Langflow, FastAPI, Supabase, Docker, Kubernetes/Serverless), key features (visual agent builder, multi-agent support, natural language agent creation), and setup instructions."
  - **Cursor AI:** Create `./.cursor/rules/rules.mdc` (content provided in PRD section above).
  - **Vibe Code:** `git add . && git commit -m "Initial project setup and Cursor rules"`
- [x] **Clone Core Open-Source Repositories (for future modifications & context):**
  - **Action:** Create a `vendor/` directory in your project root to store these.
  - **Cursor AI:** Ask Cursor: "Generate git clone commands for the latest stable versions of `langflow-ai/langflow`, `langchain-ai/langchain`, `joaomdmoura/crewai`, and `microsoft/autogen` into the `vendor/` directory."
    ```bash
    git clone https://github.com/langflow-ai/langflow.git vendor/langflow
    git clone https://github.com/langchain-ai/langchain.git vendor/langchain
    git clone https://github.com/joaomdmoura/crewai.git vendor/crewai
    git clone https://github.com/microsoft/autogen.git vendor/autogen
    ```
  - **Vibe Code:** `git add vendor/ && git commit -m "Cloned core open-source repositories for future reference and modification"`
- [x] **Python Environment & Poetry Setup:**
  - Install Poetry: `pip install poetry`
  - `poetry init --no-interaction`
  - **Cursor AI:** Ask Cursor: "Add `fastapi`, `uvicorn`, `python-multipart`, `sqlalchemy`, `psycopg2-binary`, `supabase-py`, `langchain`, `langchain-community`, `langchain-openai`, `langsmith`, `langfuse`, `pydantic`, `python-dotenv`, `uvloop`, `httptools`, `fastapi-users`, `fastapi-jwt-auth`, `fastapi-limiter`, `fastapi-pagination`, `fastapi-mail`, `fastapi-cache`, `alembic`, `ruff`, `pytest` to `pyproject.toml` as dependencies. Split our dev-dependencies where necessary"
  - `poetry install --no-interaction --no-root`
  - **Vibe Code:** `git add pyproject.toml poetry.lock && git commit -m "Setup Poetry and initial dependencies"`
- [x] **Supabase Project & Schema Setup:**
  - **External:** Create a new Supabase project. Enable `pgvector` extension.
  - **Cursor AI:** Ask Cursor: "Generate the SQL schema for `users`, `agents`, `tools`, and `agent_memories` tables, including RLS policies, as defined in `prd.md`. Save this to `supabase_schema.sql`."
  - **External:** Run `supabase_schema.sql` in Supabase SQL Editor.
  - **Cursor AI:** Ask Cursor: "Create `.env.example` with placeholders for `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `JWT_SECRET_KEY`, `FIRST_SUPERUSER_EMAIL`, `FIRST_SUPERUSER_PASSWORD`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`, `MAIL_PORT`, `MAIL_SERVER`, `MAIL_TLS`, `MAIL_SSL`, `USE_CREDENTIALS`, `VALIDATE_CERTS`."
  - Create your actual `.env` file and fill in credentials. Do **NOT** commit `.env`.
  - **Vibe Code:** `git add supabase_schema.sql .env.example && git commit -m "Add Supabase schema and env example"`

### 1.2. User Management Microservice (User Service)

- [x] **FastAPI Core Setup:**
  - **Cursor AI:** Ask Cursor: "Create `main.py` in the root. It should set up FastAPI, include lifespan context managers for startup/shutdown, and include API routers for `auth`, `agents`, `tools`, `nl_agents`, and `run` (which will be created later). Add a simple root endpoint `/`."
  - **Cursor AI:** Ask Cursor: "Create the directory structure: `app/api/v1/`, `app/models/`, `app/db/`, `app/core/`, `app/services/`, `tests/`."
- [x] **Supabase Client & CRUD:**
  - **Cursor AI:** Ask Cursor: "Create `app/db/supabase_client.py` to initialize the Supabase client using environment variables. Include an async function to get the client instance."
  - **Cursor AI:** Ask Cursor: "Create `app/db/crud_users.py` with async CRUD operations for the `users` table, including password hashing (using `passlib[bcrypt]`) for registration and verification for login. Follow RORO pattern."
  - **Vibe Code:** `git add app/db/supabase_client.py app/db/crud_users.py && git commit -m "Supabase client and user CRUD operations"`
- [x] **User Models & Authentication:**
  - **Cursor AI:** Ask Cursor: "Create `app/models/user.py` with Pydantic models for `UserCreate`, `UserLogin`, `UserResponse`, and `Token`. Use `fastapi-users` models as a reference."
  - **Cursor AI:** Ask Cursor: "Create `app/core/security.py` for JWT token generation and verification using `fastapi-jwt-auth`. Include functions for password hashing and verification."
  - **Cursor AI:** Ask Cursor: "Create `app/api/v1/auth/routes.py` with FastAPI routes for `/register` (POST) and `/login` (POST). Use `fastapi-users` and `fastapi-jwt-auth` for user management and authentication. Implement rate limiting using `fastapi-limiter`. Add a CAPTCHA placeholder for now."
  - **Cursor AI:** Ask Cursor: "Create `app/api/v1/auth/__init__.py` to import and expose the `router` from `routes.py`."
  - **Vibe Code:** `git add app/models/user.py app/core/security.py app/api/v1/auth/routes.py app/api/v1/auth/__init__.py && git commit -m "Implement user models and authentication routes"`
- [x] **Tests for User Service:**
  - **Cursor AI:** Ask Cursor: "Write high-level integration tests for user registration and login in `tests/test_auth.py`. Simulate a user registering, then logging in with the correct credentials, and attempting to access a protected route with the token." Use `pytest` and `httpx`."
  - **Vibe Code:** Run tests: `poetry run pytest tests/test_auth.py`. Ensure all pass. `git add tests/test_auth.py && git commit -m "Add integration tests for user authentication"`

### 1.3. Agent Management Microservice (Agent Management Service)

- [x] **Agent Models & CRUD:**
  - **Cursor AI:** Ask Cursor: "Create `app/models/agent.py` with Pydantic models for `AgentCreate`, `AgentUpdate`, and `AgentResponse`. Include `langflow_flow_json` as JSONB type."
  - **Cursor AI:** Ask Cursor: "Create `app/db/crud_agents.py` with async CRUD functions for the `agents` table (create, get_by_id, get_all_by_user, update, delete). Ensure RLS is respected."
  - **Vibe Code:** `git add app/models/agent.py app/db/crud_agents.py && git commit -m "Agent models and CRUD operations"`
- [x] **Agent API Endpoints:**
  - **Cursor AI:** Ask Cursor: "Create `app/api/v1/agents/routes.py` with FastAPI routes for `/agents` (POST to create, GET to list user's agents) and `/agents/{agent_id}` (GET, PUT, DELETE). All routes must be protected by JWT authentication and enforce RLS."
  - **Cursor AI:** Ask Cursor: "Create `app/api/v1/agents/__init__.py` to import and expose the `router` from `routes.py`."
  - **Vibe Code:** `git add app/api/v1/agents/routes.py app/api/v1/agents/__init__.py && git commit -m "Implement agent management API endpoints"`
- [x] **Tests for Agent Management Service:**
  - **Cursor AI:** Ask Cursor: "Write high-level integration tests for agent creation, listing, retrieval, update, and deletion in `tests/test_agents.py`. Ensure tests cover RLS and authentication."
  - **Vibe Code:** Run tests. `git add tests/test_agents.py && git commit -m "Add integration tests for agent management"`

### 1.4. Tool Registry Microservice (Tool Registry Service)

- [x] **Tool Models & CRUD:**
  - **Cursor AI:** Ask Cursor: "Create `app/models/tool.py` with Pydantic models for `ToolCreate` (`user_id`, `name`, `description`, `tool_type`, `definition`), `ToolResponse`. `definition` should be JSONB."
  - **Cursor AI:** Ask Cursor: "Create `app/db/crud_tools.py` with async CRUD functions for the `tools` table. Ensure RLS is respected."
  - **Vibe Code:** `git add app/models/tool.py app/db/crud_tools.py && git commit -m "Tool models and CRUD operations"`
- [x] **Tool API Endpoints:**
  - **Cursor AI:** Ask Cursor: "Create `app/api/v1/tools/routes.py` with FastAPI routes for `/tools` (POST to create, GET to list user's tools) and `/tools/{tool_id}` (GET, PUT, DELETE). All routes must be protected by JWT authentication and enforce RLS."
  - **Cursor AI:** Ask Cursor: "Create `app/api/v1/tools/__init__.py` to import and expose the `router` from `routes.py`."
  - **Vibe Code:** `git add app/api/v1/tools/routes.py app/api/v1/tools/__init__.py && git commit -m "Implement tool registry API endpoints"`
- [x] **Tests for Tool Registry Service:**
  - **Cursor AI:** Ask Cursor: "Write high-level integration tests for tool creation, listing, retrieval, update, and deletion in `tests/test_tools.py`. Ensure tests cover RLS and authentication."
  - **Vibe Code:** Run tests. `git add tests/test_tools.py && git commit -m "Add integration tests for tool registry"`

## Phase 2: Langflow Integration & Agent Deployment

### 2.1. Dockerization of Microservices

- [x] **Dockerfiles for Individual Services**

  - Create `app/api/v1/auth/Dockerfile` that:
    - Uses a `python:3.12-slim` base
    - Installs dependencies via Poetry or pip
    - Copies project code
    - Sets CMD to run Uvicorn on port 8000
  - Create `app/api/v1/agents/Dockerfile` (same pattern)
  - Create `app/api/v1/tools/Dockerfile`
  - Create `app/api/v1/nl_agents/Dockerfile`
  - Create `app/api/v1/run/Dockerfile`

- [x] **Write `docker-compose.yml`**

  - It should include each microservice:
    - `supabase_db` (PostgreSQL + pgvector for local Supabase emulation)
    - `supabase_api` (PostgREST or Supabase CLI)
    - `auth_service` (build: `app/api/v1/auth`, ports: 8001:8000)
    - `agents_service` (build: `app/api/v1/agents`, ports: 8002:8000)
    - `tools_service` (build: `app/api/v1/tools`, ports: 8003:8000)
    - `nl_agents_service` (build: `app/api/v1/nl_agents`, ports: 8004:8000)
    - `run_service` (build: `app/api/v1/run`, ports: 8005:8000)
    - `langflow_ide` (official image: `langflowai/langflow:latest`, ports: 7860:7860)
  - Configure `env_file` + necessary `environment` in each
  - (Optional) mount local code for hot-reload

- [ ] **Local Supabase API Layer**

  - Add a PostgREST or Supabase CLI container so `supabase-py` talks to a REST endpoint

- [ ] **Bring up & verify**
  - Run `docker compose up --build`
  - Hit `/docs`, `/register`, `/agents`, etc. to confirm each service
  - Commit your compose file:
    ```bash
    git add docker-compose.yml
    git commit -m "Add docker-compose for local development"
    ```

### 2.2. Agent Deployment Service

- [ ] **Deployment Orchestration Logic:**
  - **Cursor AI:** Ask Cursor: "Create `app/services/agent_deployer.py`. This module will contain functions to:
    - Generate a Dockerfile for a specific Langflow agent flow (based on `langflow_flow_json`).
    - Build the Docker image.
    - Push the image to a container registry (placeholder for now).
    - Generate Kubernetes deployment manifests (or serverless function configs) for the agent.
    - Trigger the deployment to a Kubernetes cluster (or cloud function service).
    - Update the agent's `deployment_status` and `deployed_endpoint` in the database."
  - **Vibe Code:** `git add app/services/agent_deployer.py && git commit -m "Agent deployment orchestration service"`
- [ ] **Publish Agent Endpoint:**
  - **Cursor AI:** Ask Cursor: "Add a `POST /agents/{agent_id}/publish` route to `app/api/v1/agents.py`. This endpoint should call functions in `app/services/agent_deployer.py` to initiate deployment. Make it an async background task if deployment is long-running."
  - **Vibe Code:** `git commit -m "Add publish agent API endpoint"`
- [ ] **Tests for Agent Deployment:**
  - **Cursor AI:** Ask Cursor: "Write a high-level integration test in `tests/test_agent_deployment.py` that simulates publishing an agent. Mock the actual deployment calls to cloud services."
  - **Vibe Code:** Run tests. `git add tests/test_agent_deployment.py && git commit -m "Add tests for agent deployment"`

### 2.3. Agent Runtime Service (User-Deployed Agents)

- [ ] **Generic Agent Runtime Dockerfile:**
  - **Cursor AI:** Ask Cursor: "Create a generic Dockerfile template in `templates/agent_runtime_dockerfile.j2` that can run a Langflow-exported agent flow. It should:
    - Use a lightweight Python base image.
    - Install Langflow OSS and necessary dependencies (LangChain, LLM integrations, Supabase client).
    - Copy the `langflow_flow_json` (or a reference to it) into the container.
    - Set `LANGFLOW_BACKEND_ONLY=true` to run in headless mode.
    - Expose a port for API calls.
    - Define the command to run the flow as an API endpoint."
  - **Vibe Code:** `git add templates/agent_runtime_dockerfile.j2 && git commit -m "Generic agent runtime Dockerfile template"`
- [ ] **Agent Execution Endpoint:**
  - **Cursor AI:** Ask Cursor: "Create `app/api/v1/run/routes.py` with a `POST /run/{agent_id}` endpoint. This endpoint will be called by users to execute their deployed agents. It should:
    - Load the `langflow_flow_json` for the given `agent_id`.
    - Initialize and run the Langflow flow.
    - Handle input/output.
    - Integrate with LangSmith/Langfuse for tracing.
    - Ensure agent memory (Supabase) is correctly configured for the specific agent/user."
  - **Cursor AI:** Ask Cursor: "Create `app/api/v1/run/__init__.py` to import and expose the `router` from `routes.py`."
  - **Vibe Code:** `git add app/api/v1/run/routes.py app/api/v1/run/__init__.py && git commit -m "Implement agent execution API endpoint"`
- [ ] **Tests for Agent Execution:**
  - **Cursor AI:** Ask Cursor: "Write high-level integration tests for agent execution in `tests/test_agent_run.py`. Mock LLM calls and Supabase interactions. Test input/output and basic flow execution."
  - **Vibe Code:** Run tests. `git add tests/test_agent_run.py && git commit -m "Add tests for agent execution"`

## Phase 3: Advanced Features & Observability

### 3.1. Natural Language Agent Creation

- [ ] **NL to Flow Logic:**
  - **Cursor AI:** Ask Cursor: "Create `app/services/nl_agent_generator.py`. This module will contain a function that takes a `natural_language_description` and uses an LLM to:
    - Parse the description into a structured representation of agent components (LLM, tools, memory, basic flow).
    - Generate a basic Langflow flow JSON.
    - Consider using `langchain` for parsing and structured output."
  - **Vibe Code:** `git add app/services/nl_agent_generator.py && git commit -m "Natural language agent generator service"`
- [ ] **NL Agent API Endpoints:**
  - **Cursor AI:** Ask Cursor: "Create `app/api/v1/nl_agents/routes.py` with `POST /nl-agents/create` and `POST /nl-agents/{agent_id}/refine` routes. These should call the `nl_agent_generator` service. Protect with authentication."
  - **Cursor AI:** Ask Cursor: "Create `app/api/v1/nl_agents/__init__.py` to import and expose the `router` from `routes.py`."
  - **Vibe Code:** `git add app/api/v1/nl_agents/routes.py app/api/v1/nl_agents/__init__.py && git commit -m "Implement natural language agent creation API endpoints"`
- [ ] **Tests for NL Agent Creation:**
  - **Cursor AI:** Ask Cursor: "Write high-level integration tests for natural language agent creation in `tests/test_nl_agents.py`. Mock LLM calls and test various descriptions."
  - **Vibe Code:** Run tests. `git add tests/test_nl_agents.py && git commit -m "Add tests for natural language agent creation"`

### 3.2. Monitoring & Observability

- [ ] **LangSmith/Langfuse Integration:**
  - **Action:** Ensure `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` are correctly set in your FastAPI and Langflow Docker environments.
  - **Cursor AI:** Ask Cursor: "Add `langsmith` and `langfuse` initialization to `main.py` and `app/api/v1/run.py` to trace LLM calls and agent executions."
  - **Vibe Code:** `git commit -m "Integrate LangSmith/Langfuse for tracing"`
- [ ] **Centralized Logging:**
  - **Cursor AI:** Ask Cursor: "Configure Python's `logging` module in `main.py` and other services to output structured logs (e.g., JSON format). Suggest a basic setup for local file logging and a placeholder for cloud-native logging."
  - **Vibe Code:** `git commit -m "Implement centralized logging"`

### 3.3. Multi-Agent Orchestration

- [ ] **CrewAI Integration (via Langflow):**
  - **Action:** Guide users on how to use Langflow's native CrewAI components. This is primarily a documentation task for your users.
  - **Cursor AI:** Ask Cursor: "Generate a sample Langflow flow JSON for a simple CrewAI setup (e.g., a 'Researcher' and 'Writer' agent collaborating on a topic). Save this to `sample_flows/crewai_example.json`."
  - **Vibe Code:** `git add sample_flows/crewai_example.json && git commit -m "Add sample CrewAI flow"`
- [ ] **AutoGen Integration (via Custom Component/Tool):**
  - **Cursor AI:** Ask Cursor: "Create a custom Langflow component in `langflow_custom_components/autogen_wrapper.py` that wraps an AutoGen multi-agent conversation. This component should take inputs, initiate an AutoGen chat, and return the result. It should use `langgraph` for integration as shown in research."
  - **Vibe Code:** `git add langflow_custom_components/autogen_wrapper.py && git commit -m "Custom Langflow component for AutoGen integration"`

### 3.4. Interoperability Protocols (MCP & A2A)

- [ ] **MCP Integration:**
  - **Action:** Langflow natively supports MCP as client/server.
  - **Cursor AI:** Ask Cursor: "Provide instructions for users on how to expose their Langflow-built agents as MCP servers. Include steps for configuring Langflow's MCP server tab and connecting Cursor AI as an MCP client."
  - **Cursor AI:** Ask Cursor: "Generate a custom Langflow component in `langflow_custom_components/mcp_client_tool.py` that acts as an MCP client, allowing agents to discover and use external MCP tools."
  - **Vibe Code:** `git add langflow_custom_components/mcp_client_tool.py && git commit -m "MCP client custom component"`
- [ ] **A2A Protocol (Future-Proofing):**
  - **Action:** Monitor A2A protocol development.
  - **Cursor AI:** Ask Cursor: "Outline a high-level plan for how my FastAPI backend could act as an A2A client/server, allowing agents on my platform to communicate with other A2A-compatible agents. Focus on the API endpoints and data structures needed." (This is a research/planning task for now).
  - **Vibe Code:** `git commit -m "A2A protocol integration plan (placeholder)"`

## Phase 4: Production Deployment & Refinement

### 4.1. Cloud Deployment

- [ ] **Container Registry Setup:**
  - **External:** Choose a container registry (e.g., Docker Hub, AWS ECR, Google Container Registry, Azure Container Registry).
  - **Cursor AI:** Ask Cursor: "Generate a `Dockerfile` for my `fastapi_backend` service, optimized for production. Include multi-stage build if appropriate."
  - **Vibe Code:** `git add Dockerfile.backend && git commit -m "Production Dockerfile for FastAPI backend"`
- [ ] **Kubernetes Deployment (for Platform Services):**
  - **Cursor AI:** Ask Cursor: "Generate Kubernetes deployment, service, and ingress manifests (`.yaml` files) for my `fastapi_backend` and `langflow_ide` services. Include considerations for horizontal scaling, load balancing, and persistent storage for Langflow data. Use `kustomize` or `helm` for templating."
  - **Vibe Code:** `git add kubernetes/ && git commit -m "Kubernetes manifests for platform services"`
- [ ] **CI/CD Pipeline:**
  - **Cursor AI:** Ask Cursor: "Generate a GitHub Actions workflow to automatically build Docker images for `fastapi_backend` and `langflow_ide`, push them to a container registry, and deploy them to my Kubernetes cluster on push to `main` branch."
  - **Vibe Code:** `git add .github/workflows/ci-cd.yml && git commit -m "CI/CD pipeline for platform deployment"`
- [ ] **User Agent Deployment (Kubernetes/Serverless):**
  - **Action:** Implement the logic in `app/services/agent_deployer.py` to dynamically generate and apply Kubernetes manifests (or deploy serverless functions) for each user's agent.
  - **Vibe Code:** `git commit -m "Implement dynamic user agent deployment"`

### 4.2. Security Hardening & Compliance

- [ ] **WAF Configuration:**
  - **External:** Configure WAF rules on your cloud provider's API Gateway/Load Balancer.
- [ ] **Secret Management:**
  - **External:** Migrate sensitive environment variables to a cloud-native secret management service.
  - **Cursor AI:** Ask Cursor: "Modify my FastAPI application to retrieve secrets from a cloud-native secret management service (e.g., AWS Secrets Manager) instead of `.env` in production."
- [ ] **Regular Security Audits:**
  - **Action:** Schedule periodic penetration tests and vulnerability scans.

### 4.3. Documentation & User Guides

- [ ] **User Documentation:**
  - **Cursor AI:** Ask Cursor: "Generate a draft for a 'Getting Started' guide for users, explaining how to register, create their first agent using Langflow, and publish it. Include screenshots/placeholders."
  - **Cursor AI:** Ask Cursor: "Generate a guide on 'How to Create Custom Tools' for users, including Python code examples and OpenAPI spec examples."
  - **Cursor AI:** Ask Cursor: "Generate a guide on 'Building Multi-Agent Systems' using Langflow's CrewAI components."
  - **Vibe Code:** `git add docs/user_guides/ && git commit -m "Draft user documentation"`
- [ ] **API Documentation:**
  - **Action:** FastAPI automatically generates OpenAPI (Swagger UI) documentation. Ensure it's accessible and well-described.
  - **Cursor AI:** Ask Cursor: "Review my FastAPI Pydantic models and route docstrings to ensure they are clear and comprehensive for auto-generated API documentation."

### 4.4. Billing & Usage Tracking (If applicable for MVP)

- [ ] **Token Usage Tracking:**
  - **Cursor AI:** Ask Cursor: "Design a database schema for `token_usage` (`user_id`, `agent_id`, `llm_model`, `tokens_input`, `tokens_output`, `cost`, `timestamp`). Create `app/db/crud_usage.py`."
  - **Cursor AI:** Ask Cursor: "Implement a FastAPI middleware or a custom Langflow component to intercept LLM calls and log token usage to the `token_usage` table."
  - **Vibe Code:** `git commit -m "Implement token usage tracking"`
