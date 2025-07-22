# Auth Service

## Overview
The Auth Service is a critical component of the Kgents platform responsible for managing user authentication, authorization, and identity management. This service integrates with Supabase Auth for underlying authentication while implementing custom permission models, profiles, API key management, and service-to-service authentication features.

## Technical Stack
- **Framework**: FastAPI with async support
- **Database**: PostgreSQL via SQLAlchemy 2.0 (async)
- **Migration**: Alembic
- **Authentication**: Supabase Auth integration + JWT
- **Testing**: Pytest with async fixtures
- **Documentation**: Swagger UI / OpenAPI

## Features
- User authentication & registration
- Role-based access control (RBAC)
- API key generation and management
- User profile management
- Application client registration and management
- Service-to-service (M2M) authentication
- JWT token validation and generation

## Project Structure
```
auth_service/
├── alembic/            # Database migration configuration and versions
├── scripts/            # Utility scripts for setup, testing and migration
├── src/
│   └── auth_service/
│       ├── api/        # API endpoints and routers
│       ├── config/     # Configuration settings
│       ├── core/       # Core functionality
│       ├── crud/       # Database CRUD operations
│       ├── db.py       # Database connection setup
│       ├── models/     # SQLAlchemy models
│       ├── schemas/    # Pydantic schemas for validation
│       └── utils/      # Utility functions
├── tests/              # Test suite
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── .env.example        # Example environment variables
├── alembic.ini         # Alembic configuration
├── pyproject.toml      # Python dependencies and project metadata
├── Dockerfile          # Container configuration
└── MIGRATIONS.md       # Detailed migration documentation
```

## Setup and Development

### Prerequisites
- Python 3.12+
- Poetry
- Docker and Docker Compose
- Supabase CLI (for managing the local development environment)

### Environment Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd auth_service
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Copy environment template:
   ```bash
   cp .env.example .env.dev
   ```

4. Configure environment variables:
   - Edit the `.env.dev` file with your local settings. The default values are configured to work with the local Supabase stack.

### Database Setup

The auth_service database setup is fully automated. For a first-time setup or to completely reset the database, run the following command from the auth_service/ directory:

```bash
python scripts/manage_db.py recreate
```

This command handles everything: it stops and restarts the local Supabase stack, creates the database, applies the latest migrations, and runs the initial data bootstrap process (creating default roles, permissions, and the admin user). For more details, see the Migration Guide.

## Running the Service

### Development Mode:
```bash
uvicorn src.auth_service.main:app --reload --host 0.0.0.0 --port 8001
```

### Docker:
The entire environment, including this service and the Supabase stack, can be managed from the project's root docker-compose.yml file.

```bash
# From the project root directory
docker-compose up --build auth_service
```

## Database Migrations

All database schema changes are managed through Alembic, using a wrapper script for consistency. Please use the following commands instead of calling alembic directly.

### Creating a New Migration

After making changes to your SQLAlchemy models in src/auth_service/models/, generate a new migration:

```bash
# Use a short, descriptive message for your change
python scripts/manage_db.py create-migration -m "Add new_column_to_profiles_table"
```

### Applying Migrations

To apply all pending migrations and bring the database schema up-to-date, run:

```bash
python scripts/manage_db.py upgrade
```

For a more detailed explanation of the migration process and available commands, please refer to the Auth Service Migration Guide.

## API Documentation

When the service is running, access the API documentation at:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## Testing

The service includes a comprehensive testing suite.

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=src/auth_service
```
