#!/bin/bash
# Initialize database for agent_management_service

set -e

# Set database connection parameters from environment variables
DB_HOST=${POSTGRES_HOST:-127.0.0.1}
DB_PORT=${POSTGRES_PORT:-54322}
DB_USER=${POSTGRES_USER:-postgres}
DB_PASSWORD=${POSTGRES_PASSWORD:-postgres}
DB_NAME=${POSTGRES_DB:-postgres}

# Wait for the database to be ready
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c '\q'; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up - executing database migrations"

# Run alembic migrations
alembic upgrade head

echo "Database initialization completed successfully"
