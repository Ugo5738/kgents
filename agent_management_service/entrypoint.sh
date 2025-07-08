#!/bin/sh
set -e

# These variables are sourced from the .env.dev file via docker-compose
echo "Waiting for database at $AGENT_MANAGEMENT_SERVICE_POSTGRES_HOST:$AGENT_MANAGEMENT_SERVICE_POSTGRES_PORT..."
while ! nc -z $AGENT_MANAGEMENT_SERVICE_POSTGRES_HOST $AGENT_MANAGEMENT_SERVICE_POSTGRES_PORT; do
  sleep 1
done
echo "Database is ready."

# Run the database setup for the agent_management_service
echo "Running setup for agent_management_service..."
python scripts/manage_migrations.py create-db
python scripts/manage_migrations.py upgrade
echo "Setup for agent_management_service complete."

# Execute the main command (uvicorn)
echo "Starting Agent Management Service..."
exec "$@"