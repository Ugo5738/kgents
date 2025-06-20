#!/usr/bin/env bash
set -e

# Wait for database to be available
echo "Waiting for database to be available..."

PGHOST=${PGHOST:-supabase_db_kgents}
PGPORT=${PGPORT:-5432}
PGUSER=${PGUSER:-postgres}
PGDB=${PGDB:-auth_dev_db}

until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "postgres" -c "\q" > /dev/null 2>&1; do
  echo "Postgres is unavailable - sleeping"
  sleep 1
done

echo "Database is available."

# Check if our database exists, create it if it doesn't
echo "Checking if database $PGDB exists..."
DB_EXISTS=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "postgres" -tAc "SELECT 1 FROM pg_database WHERE datname='$PGDB'" | grep -q 1 && echo "yes" || echo "no")

if [ "$DB_EXISTS" = "no" ]; then
  echo "Creating database $PGDB..."
  PGPASSWORD=$POSTGRES_PASSWORD psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "postgres" -c "CREATE DATABASE $PGDB"
  echo "Database $PGDB created successfully!"
else
  echo "Database $PGDB already exists."
fi

# Verify database connection before running migrations
echo "Verifying database connection..."
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

async def check_db_connection():
    # Use environment variable for database URL
    db_url = 'postgresql+asyncpg://$PGUSER:$POSTGRES_PASSWORD@$PGHOST:$PGPORT/$PGDB'
    print(f'Checking database connection to {db_url}')
    
    engine = create_async_engine(
        db_url,
        echo=True,
        connect_args={
            'application_name': 'auth_service_db_check',
            'options': '-c timezone=UTC -c statement_timeout=10000',
            'connect_timeout': 5
        }
    )
    
    try:
        async with engine.connect() as conn:
            result = await conn.execute('SELECT 1')
            print('Database connection successful!')
    except Exception as e:
        print(f'Error connecting to database: {e}')
        raise
    finally:
        await engine.dispose()

asyncio.run(check_db_connection())
"

# Set environment variables for Alembic
export AUTH_SERVICE_DATABASE_URL="postgresql+asyncpg://$PGUSER:$POSTGRES_PASSWORD@$PGHOST:$PGPORT/$PGDB"
echo "Using database URL: $AUTH_SERVICE_DATABASE_URL"

# Run Alembic migrations to create/update the schema
echo "Running database migrations with Alembic..."
alembic upgrade head

# Run bootstrap process to create initial data
echo "Running bootstrap process..."
python -c "
import asyncio
from auth_service.bootstrap import run_bootstrap
from auth_service.db import get_db
import os

async def run_bootstrap_process():
    # Using the correct session manager from db.py
    async for session in get_db():
        success = await run_bootstrap(session)
        if success:
            print('Bootstrap process completed successfully')
        else:
            print('Bootstrap process failed')
            exit(1)
        break

asyncio.run(run_bootstrap_process())
"

echo "Database initialization and bootstrap completed successfully!"
