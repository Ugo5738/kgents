#!/bin/sh
set -e

DB_HOST=$AUTH_SERVICE_POSTGRES_HOST
DB_PORT=$AUTH_SERVICE_POSTGRES_PORT

# These variables are sourced from the .env.dev file via docker-compose
echo "Waiting for database at $DB_HOST:$DB_PORT..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "Database is ready."

# Run the database setup for the auth_service
echo "Running setup for auth_service..."
python scripts/setup_database.py
echo "Setup for auth_service complete."

# Execute the main command (uvicorn)
echo "Starting Auth Service..."
exec "$@"