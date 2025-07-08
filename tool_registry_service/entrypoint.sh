#!/bin/sh
set -e

# These variables are sourced from the .env.dev file via docker-compose
echo "Waiting for database at $TOOL_REGISTRY_SERVICE_POSTGRES_HOST:$TOOL_REGISTRY_SERVICE_POSTGRES_PORT..."
while ! nc -z $TOOL_REGISTRY_SERVICE_POSTGRES_HOST $TOOL_REGISTRY_SERVICE_POSTGRES_PORT; do
  sleep 1
done
echo "Database is ready."

# Run the database setup for the tool_registry_service
echo "Running setup for tool_registry_service..."
python scripts/manage_migrations.py create-db --env=dev
python scripts/manage_migrations.py upgrade --env=dev
echo "Setup for tool_registry_service complete."

# Execute the main command (uvicorn)
echo "Starting Tool Registry Service..."
exec "$@"