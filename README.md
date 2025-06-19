# Kgents (Agent-as-a-Service) Platform

## Project Overview

Kgents is an Agent-as-a-Service platform that enables you to visually build, deploy, and manage autonomous AI agents. It combines Langflow for workflow design, a suite of FastAPI microservices for backend logic, and Supabase for authentication, persistent storage, and real-time capabilities.

## Tech Stack

- **Backend Framework**: FastAPI for high-performance, asynchronous services.
- **Agent Workflow Design**: Langflow, integrated as the visual agent builder.
- **Database & Auth**: Supabase, providing PostgreSQL, pgvector, and user authentication.
- **Containerization**: Docker for creating consistent service images.
- **Local Orchestration**: Docker Compose for running the multi-service environment locally.
- **Deployment**: Kubernetes (e.g., AWS EKS, GKE, or AKS) for scalable production deployment.
- **CI/CD**: GitHub Actions for automated building, testing, and deployment of services.

## Key Features

- **Visual Agent Builder**: Design agent workflows through an intuitive UI without writing code
- **Multi-Agent Support**: Run and coordinate multiple agents concurrently for complex tasks
- **Natural Language Agent Creation**: Define and configure agents using plain English prompts

## Architecture

The platform is built on a microservice architecture, where each service has a distinct responsibility. This approach ensures scalability, resilience, and maintainability.

- **auth_service**: Manages user registration, login, profiles, and API key generation. It acts as the central authentication authority.
- **agent_management_service**: Handles the lifecycle of agents, including creating, updating, and storing their definitions (Langflow JSON).
- **tool_registry_service**: Manages the registration and storage of custom tools that agents can use.
- **agent_deployment_service**: Orchestrates the deployment of agent flows into runnable, containerized services.
- **agent_runtime_service**: The execution environment where deployed agents run.
- **(Future Services)**: nl_agent_service, observability_service, etc.

## Setup Instructions

### Prerequisites

- Docker & Docker Compose
- Node.js (>=14.x)
- Python 3.12+ and Poetry
- Supabase CLI and Supabase account (for hosted database and authentication)

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
SUPABASE_URL=<your-supabase-url>
SUPABASE_ANON_KEY=<your-supabase-anon-key>
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### Local Development

1. Clone the repository:

   ```bash
   git clone https://github.com/yourorg/kgents.git
   cd kgents
   ```

2. Install Supabase CLI globally:

   ```bash
   npm install -g supabase    # or brew install supabase/tap/supabase
   ```

3. Initialize Supabase in your project:

   ```bash
   supabase init
   ```

4. Start the Supabase local stack (Auth, Database, Realtime, Storage, PostgREST):

   ```bash
   supabase start
   ```

5. In parallel, start your FastAPI backend:

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

6. In parallel, start the Langflow IDE (headless mode):

   ```bash
   docker run -it --rm --env-file .env -p 7860:7860 langflowai/langflow:latest
   ```

7. (Optional) For live frontend development:

   ```bash
   cd frontend && npm install && npm run dev
   ```

### Docker

To run all backend and Langflow services in containers:

```bash
supabase start          # bring up Supabase stack
docker-compose up --build
```

This will launch your FastAPI and Langflow IDE containers connected to the local Supabase services.

### Kubernetes / Serverless

- **Kubernetes:**

  ```bash
  kubectl apply -f k8s/
  ```

- **Serverless:**
  ```bash
  serverless deploy
  ```

### Production Deployment

For production, configure your application to use your hosted Supabase instance. Update your `.env`:

```bash
SUPABASE_URL=<your-production-supabase-url>
SUPABASE_ANON_KEY=<your-production-anon-key>
DATABASE_URL=postgresql://<user>:<password>@<prod-db-host>:5432/<database>
```

Build and push Docker images to your container registry:

```bash
docker build -t <registry>/kgents-auth:latest -f app/api/v1/auth/Dockerfile .
docker push <registry>/kgents-auth:latest
# repeat for agents, tools, nl_agents, run services
```

Deploy in your production environment:

- Docker Compose: `docker-compose -f docker-compose.prod.yml up -d`
- Kubernetes: `kubectl apply -f kubernetes/`

Automate these steps in your CI/CD pipeline (see the **CI/CD Pipeline** task in `todo.md`).

---

## Architecture & Deployment Guide

For an in-depth overview of our service architecture, containerization, Kubernetes deployment, and migration path to standalone microservices, see [Architecture & Deployment Overview](docs/architecture.md).

_Happy agent-building!_
