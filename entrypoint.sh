#!/bin/sh
# Exit immediately if a command exits with a non-zero status.
set -e

# Wait for the database to be available.
# It uses environment variables that will be provided by docker-compose.
echo "Waiting for database at $POSTGRES_HOST:$POSTGRES_PORT..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 1
done
echo "Database is ready."

# --- Service-Specific Setup Commands Go Here ---
# This is the part we will customize for each service.
# For example:
# echo "Creating database and running migrations..."
# python scripts/manage_migrations.py create-db --env=dev
# python scripts/manage_migrations.py upgrade --env=dev
# -----------------------------------------------

# Execute the main command (e.g., uvicorn) passed to this script
echo "Starting the application..."
exec "$@"