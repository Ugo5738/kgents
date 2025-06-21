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

### Local Development

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env.dev
   # Edit .env.dev with your settings
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
