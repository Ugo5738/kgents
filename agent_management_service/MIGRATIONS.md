# Agent Management Service Migration Workflow

This document outlines the database migration workflow for the `agent_management_service` component of the Kgents platform.

## Architecture Overview

The agent_management_service database schema consists of tables that manage:

1. **Agent Definitions**: Core agent metadata and configuration
2. **Agent Versions**: Version history and snapshots of agent configurations
3. **Related Entities**: Any auxiliary tables for managing agent relationships

## Migration Setup Process

### Step 1: Configure Database Connection

Ensure your `.env` or `.env.dev` file contains the correct database URL:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@supabase_db_kgents:5432/agent_management_dev_db
```

### Step 2: Configure Alembic

Ensure `alembic.ini` points to the correct database:

```ini
# in alembic.ini
sqlalchemy.url = ${DATABASE_URL}
```

Ensure `env.py` is configured to:

1. Import all models
2. Set `target_metadata = Base.metadata`
3. Handle async database connections correctly

### Step 3: Generate and Apply Migrations

```bash
# Generate new migration
alembic revision --autogenerate -m "describe_your_changes"

# Apply migrations
alembic upgrade head
```

### Step 4: Verify Migration

After applying migrations, verify the schema was updated correctly:

```bash
python scripts/verify_migrations.py
```

This script:

- Extracts expected schema from SQLAlchemy models
- Compares with the actual database schema
- Reports any discrepancies (missing tables or columns)

## Handling Model Changes

When changing models:

1. Update SQLAlchemy models in `src/agent_management_service/models/`
2. Generate a new migration: `alembic revision --autogenerate -m "describe_changes"`
3. Review the generated migration file for accuracy
4. Apply the migration: `alembic upgrade head`
5. Verify using the verification script

## Common Issues and Solutions

### Circular Import Issues

- Use string-based relationship references (`"src.auth_service.models.SomeModel"`)
- Import models through `src.auth_service.models` module (preferred), not directly
- Ensure models are correctly registered with `Base.metadata`

### Database URL Configuration

- Ensure the database URL in `alembic.ini` points to the correct database
- For local development, use: `postgresql+psycopg://postgres:postgres@127.0.0.1:54322/agent_management_dev_db`
- For production, use environment variables to configure the URL

## Development Workflow

For a new developer setting up migrations from scratch:

```bash
# 1. Create a fresh development database
createdb -h 127.0.0.1 -p 54322 -U postgres agent_management_dev_db

# 2. Apply all migrations
alembic upgrade head

# 3. Verify migrations applied correctly
python scripts/verify_migrations.py
```

When making schema changes:

1. Update the SQLAlchemy models in `src/agent_management_service/models/`
2. Generate a new migration with descriptive name:
   ```bash
   alembic revision --autogenerate -m "add_field_x_to_agent"
   ```
3. Review the generated migration in `alembic/versions/`
4. Apply the migration:
   ```bash
   alembic upgrade head
   ```
5. Include the migration file in version control

## Script Reference

- **verify_migrations.py**: Verifies that the database schema matches SQLAlchemy models

## Migration Best Practices

1. **Breaking Changes**: Avoid breaking changes to existing tables when possible
2. **Data Migration**: For complex data migrations, write separate scripts
3. **Testing**: Always test migrations in a development environment before production
4. **Rollbacks**: Include downgrade paths in migrations for rollback support
5. **Idempotency**: Ensure migrations are idempotent when possible

## Production Deployment

For production deployments:

1. Back up the database before migration
2. Run migrations during scheduled maintenance if they might cause downtime
3. Consider running migrations in a transaction when possible
4. Monitor the migration process for any issues
