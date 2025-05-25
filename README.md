# Kgents (Agent-as-a-Service) Platform

## Project Overview

Kgents is an Agent-as-a-Service platform that enables you to visually build, deploy, and manage autonomous AI agents. It combines Langflow for workflow design, FastAPI for serving APIs, and Supabase for persistent storage and real-time data.

## Tech Stack

- **Langflow**: Drag-and-drop AI workflow builder
- **FastAPI**: High-performance Python backend framework
- **Supabase**: Open-source Postgres database, authentication, and real-time APIs
- **Docker**: Containerization for consistent development and deployment
- **Kubernetes / Serverless**: Orchestration and scalable deployment options

## Key Features

- **Visual Agent Builder**: Design agent workflows through an intuitive UI without writing code
- **Multi-Agent Support**: Run and coordinate multiple agents concurrently for complex tasks
- **Natural Language Agent Creation**: Define and configure agents using plain English prompts

## Setup Instructions

### Prerequisites

- Docker & Docker Compose
- Node.js (>=14.x)
- Python 3.9+
- Supabase account (for hosted database and authentication)

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

---

## Architecture & Deployment Guide

For an in-depth overview of our service architecture, containerization, Kubernetes deployment, and migration path to standalone microservices, see [Architecture & Deployment Overview](docs/architecture.md).

_Happy agent-building!_
