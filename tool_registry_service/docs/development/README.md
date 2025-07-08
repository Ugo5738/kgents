# Tool Registry Service Development Guide

This document provides guidelines and instructions for developers working on the Tool Registry Service.

## Architecture Overview

The Tool Registry Service follows the microservice architecture pattern established for the Kgents platform. It is responsible for managing, categorizing, and securely executing tools that can be used across the platform.

### Key Components

1. **Models**: SQLAlchemy models defining the database schema
2. **Schemas**: Pydantic models for request/response validation
3. **CRUD Operations**: Database operations encapsulated in CRUD modules
4. **Routers**: FastAPI route handlers organized by resource
5. **Dependencies**: Reusable dependency functions (auth, database)
6. **Services**: Business logic for tool execution in various environments

### Directory Structure

```
tool_registry_service/
├── alembic/                # Database migration configuration
│   ├── versions/           # Migration scripts
│   ├── env.py              # Alembic environment configuration
│   └── script.py.mako      # Migration script template
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── sql/                    # SQL schema files
├── src/                    # Source code
│   └── tool_registry_service/
│       ├── clients/        # External service clients
│       ├── crud/           # Database CRUD operations
│       ├── dependencies/   # FastAPI dependencies
│       ├── models/         # SQLAlchemy models
│       ├── routers/        # API route handlers
│       ├── schemas/        # Pydantic models
│       ├── services/       # Business logic services
│       ├── config.py       # Configuration settings
│       ├── db.py           # Database setup
│       ├── main.py         # Application entry point
│       └── security.py     # Security utilities
├── tests/                  # Test suite
├── .env.example            # Environment variables example
├── alembic.ini             # Alembic configuration
├── docker-compose.dev.yml  # Development Docker Compose
├── docker-compose.test.yml # Testing Docker Compose
├── Dockerfile              # Development Dockerfile
└── pyproject.toml          # Project dependencies
```

## Development Setup

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- Docker and Docker Compose
- PostgreSQL 15+

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd kgents/tool_registry_service
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env.dev
   # Edit .env.dev with your local settings
   ```

4. **Create the development database**:
   ```bash
   python scripts/manage_migrations.py create-db
   ```

5. **Apply migrations**:
   ```bash
   python scripts/manage_migrations.py upgrade
   ```

6. **Start the development server**:
   ```bash
   # Using Docker Compose
   docker-compose -f docker-compose.dev.yml up -d

   # Or directly with uvicorn
   uvicorn src.tool_registry_service.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access the API documentation**:
   ```
   http://localhost:8003/api/docs
   ```

## Code Style and Standards

The Tool Registry Service follows the established coding standards for the Kgents platform:

1. **PEP 8**: Follow PEP 8 style guide for Python code
2. **Type Hints**: Use type hints for all function signatures
3. **Docstrings**: Include docstrings for all modules, classes, and functions
4. **Async**: Use async/await for all I/O operations
5. **Error Handling**: Implement proper error handling with custom exceptions
6. **Security**: Follow security best practices for authentication and data validation

## Database Migrations

The service uses Alembic for database migrations. The `manage_migrations.py` script provides a convenient interface for common migration operations across different environments (dev and prod):

### Environment-Specific Operations

All commands support the `--env` parameter to specify which environment to target:

```bash
# Development environment (default)
python scripts/manage_migrations.py command --env=dev

# Production environment
python scripts/manage_migrations.py command --env=prod
```

The script automatically loads the appropriate environment file (`.env.dev` or `.env.prod`) and extracts the correct database configuration from it.

### Common Migration Operations

```bash
# Create a new migration
python scripts/manage_migrations.py generate "description_of_changes" --env=dev

# Apply migrations
python scripts/manage_migrations.py upgrade --env=dev

# Rollback migrations
python scripts/manage_migrations.py downgrade --env=dev

# Show current migration version
python scripts/manage_migrations.py current --env=dev

# Show migration history
python scripts/manage_migrations.py history --env=dev
```

### Database Lifecycle Management

The script also provides commands for managing the database lifecycle:

```bash
# Create a new database if it doesn't exist
python scripts/manage_migrations.py create-db --env=dev

# Drop an existing database
python scripts/manage_migrations.py drop-db --env=dev

# Reset database (drop and recreate)
python scripts/manage_migrations.py reset-db --env=dev
```

Each command clearly indicates which environment it's operating on and automatically extracts database names from the environment-specific connection strings.

## Adding New Features

When adding new features to the Tool Registry Service:

1. **Models**: Start by defining or updating SQLAlchemy models
2. **Schemas**: Create Pydantic models for request/response validation
3. **CRUD**: Implement database operations in the appropriate CRUD module
4. **Service Layer**: Add business logic in service modules if needed
5. **Routes**: Create API endpoints in router modules
6. **Tests**: Write tests for new functionality
7. **Migrations**: Generate a migration for schema changes
8. **Documentation**: Update API documentation

## Integration with Other Services

The Tool Registry Service integrates with other Kgents platform services:

1. **Auth Service**: For JWT token validation and role-based access control
2. **Agent Management Service**: For agent-tool association

Ensure that your changes maintain compatibility with these services.
