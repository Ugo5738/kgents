# Agent Management Service

## Overview

The Agent Management Service is a core component of the Kgents platform responsible for managing AI agents, including their creation, versioning, lifecycle management, and integration with the Langflow IDE. This service provides a secure API that enables users to define, publish, and archive agents while maintaining version history.

## Technical Stack

- **Framework**: FastAPI with async support
- **Database**: PostgreSQL via SQLAlchemy 2.0 (async)
- **Migration**: Alembic
- **Authentication**: JWT-based via auth_service
- **Testing**: Pytest with async fixtures
- **Documentation**: Swagger UI / OpenAPI

## Features

- Agent creation and management
- Automatic version history tracking
- Agent lifecycle states (draft, published, archived)
- Langflow IDE integration for agent configuration
- User ownership and access control
- Pagination for collection endpoints
- Health check endpoints for Kubernetes integration

## Project Structure

```
agent_management_service/
├── alembic/               # Database migration configuration and versions
├── src/
│   └── agent_management_service/
│       ├── crud/          # Database CRUD operations
│       ├── dependencies/  # FastAPI dependencies
│       ├── models/        # SQLAlchemy models
│       ├── routers/       # API endpoints and routers
│       ├── schemas/       # Pydantic schemas for validation
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── .env.dev              # Development environment variables
├── .env.example          # Example environment variables
├── alembic.ini           # Alembic configuration
├── pyproject.toml        # Python dependencies and project metadata
├── Dockerfile            # Container configuration
├── docker-compose.dev.yml # Development compose configuration
└── init_database.sh      # Database initialization script
```

## Setup and Development

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Poetry
- Supabase CLI (for local development with Supabase)

### Database Configuration

#### Development Environment

The service uses two database configurations depending on the context:

1. **Docker Development Environment**:
   When running inside Docker, the service connects to the Supabase container using the container network:
   ```
   DATABASE_URL=postgresql+psycopg://postgres:postgres@supabase_db_kgents:5432/agent_management_dev_db
   ```

2. **Local Development Environment**:
   When running locally with Supabase started via `supabase start`, use the local port mapping:
   ```
   DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:54322/agent_management_dev_db
   ```

#### Test Environment

Test configuration in `.env.test` should always use the local port mapping, as tests typically run outside of Docker:
```
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:54322/agent_management_test_db
```

### Database Migrations

#### Initial Setup

1. Development database migrations:
   ```bash
   # Make sure you're using the correct DATABASE_URL for your context
   export PYTHONPATH=$PYTHONPATH:$(pwd)
   alembic upgrade head
   ```

2. Test database setup:
   Tests use SQLAlchemy metadata to create tables directly rather than Alembic migrations.
   To manually initialize the test database schema:
   ```bash
   python scripts/setup_test_db.py
   ```

#### Adding New Migrations

1. Create a new migration after model changes:
   ```bash
   alembic revision --autogenerate -m "description of changes"
   ```

2. Review the generated migration file in `alembic/versions/`

3. Apply the migration:
   ```bash
   alembic upgrade head
   ```

### Local Development

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env.dev
   # Edit .env.dev with your settings based on your environment (local or Docker)
   ```

3. Run migrations:
   ```bash
   alembic upgrade head
   ```

4. Start the service:
   ```bash
   uvicorn src.agent_management_service.main:app --reload
   ```

### Docker Development

```bash
# Run with Docker Compose
docker-compose -f docker-compose.dev.yml up
```

## API Documentation

API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agent_management_service
```
