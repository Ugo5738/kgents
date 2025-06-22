# Database Migration Best Practices

This document outlines recommended practices for maintaining database schema migrations in the Agent Management Service.

## Key Principles

1. **Model-Migration Synchronization**
   - Always keep SQLAlchemy models and Alembic migrations synchronized
   - Run `alembic check` before committing code changes to verify synchronization

2. **Development Workflow**
   - After modifying SQLAlchemy models:
     1. Generate migrations: `python -m alembic revision --autogenerate -m "descriptive_message"`
     2. Review the generated migration file for accuracy
     3. Apply the migration: `python -m alembic upgrade head`
     4. Run tests to verify everything works

3. **CI/CD Integration**
   - Add a CI check that runs `alembic check` to ensure models and migrations are in sync
   - Consider running migrations automatically in dev/staging environments

4. **Testing Database Setup**
   - For tests, use the `setup_test_db.py` script to create tables directly from SQLAlchemy models
   - This bypasses Alembic migrations for faster test setup and allows mocking the Supabase auth schema

5. **Environment-Specific Configuration**
   - Development database: `agent_management_dev_db`
     - Connection URL: `postgresql+psycopg://postgres:postgres@{HOST}:5432/agent_management_dev_db`
     - Where `HOST` is `supabase_db_kgents` inside Docker or `127.0.0.1` locally with port 54322
   - Test database: `agent_management_test_db`
     - Connection URL: `postgresql+psycopg://postgres:postgres@127.0.0.1:54322/agent_management_test_db`
     - Used only for local testing, not in Docker

6. **Migration Hygiene**
   - Use meaningful migration names that describe what's changing
   - Avoid generating multiple migrations for related changes - batch them together
   - Review migrations before committing to ensure they only include intended changes
   - Avoid manual edits to migration files when possible

7. **Handling Foreign Keys and Circular References**
   - Use `use_alter=True` and named constraints for self-referential or circular foreign keys
   - Test that migrations can be applied from scratch and rolled back

8. **Version Control**
   - Never delete or modify existing migration files that have been applied to any environment
   - If a migration needs to be fixed, create a new migration that corrects the issue

9. **Large-Scale Changes**
   - For major schema changes, consider using branch-based migrations
   - Test migrations with realistic data volumes to identify potential performance issues

10. **Documentation**
    - Document any non-standard migration patterns or workarounds
    - Keep this recommendations file updated as new practices emerge

## Common Issues and Solutions

- **Transaction already deassociated warning**: This SQLAlchemy warning during tests can be safely ignored. It's related to connection lifecycle management in async tests.

- **Missing foreign key constraints**: If `alembic check` shows missing constraints, create a targeted migration to add them.

- **Test database setup failures**: Use `setup_test_db.py --force` to recreate the test database schema from scratch.
