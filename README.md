# Agent-as-a-Service Platform

## Project Overview

Agent-as-a-Service is a platform that enables you to visually build, deploy, and manage autonomous AI agents. It combines Langflow for workflow design, FastAPI for serving APIs, and Supabase for persistent storage and real-time data.

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
   git clone https://github.com/yourorg/agent-as-a-service.git
   cd agent-as-a-service
   ```

2. Start the backend (FastAPI):

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

3. Start the frontend (UI):

   ```bash
   cd ../frontend
   npm install
   npm run dev
   ```

4. Open your browser at `http://localhost:3000` to access the visual agent builder.

### Docker

Build and run all services with Docker Compose:

```bash
docker-compose up --build
```

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

_Happy agent-building!_

## Architecture & Deployment Guide

For an in-depth overview of our service architecture, containerization, Kubernetes deployment, and migration path to standalone microservices, see [Architecture & Deployment Overview](docs/architecture.md).
