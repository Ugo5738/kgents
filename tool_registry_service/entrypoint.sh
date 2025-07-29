#!/bin/sh
# Exit immediately if a command exits with a non-zero status.
set -e

# (Optional but good practice) Install shared package in development mode if it exists
if [ -d "/shared" ]; then
  echo "Installing shared package in development mode..."
  pip install -e /shared
  echo "Shared package installed successfully."
fi

DB_HOST=$TOOL_REGISTRY_SERVICE_POSTGRES_HOST
DB_PORT=$TOOL_REGISTRY_SERVICE_POSTGRES_PORT

# These variables are sourced from the .env.dev file via docker-compose
echo "Waiting for database at $DB_HOST:$DB_PORT..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "Database is ready."

# 2. Run ONLY the database migrations.
# The application bootstrap (creating users, roles, etc.) will be handled
# by the FastAPI lifespan manager inside the running application.
echo "Running Alembic migrations..."
python scripts/manage_db.py init
echo "Alembic migrations complete."

# Execute the main command (uvicorn)
echo "Starting Auth Service..."
exec "$@"