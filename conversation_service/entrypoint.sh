#!/bin/sh
set -e

# (Optional) Install shared package in development mode if it exists
if [ -d "/shared" ]; then
  echo "Installing shared package in development mode..."
  pip install -e /shared
  echo "Shared package installed successfully."
fi

DB_HOST=$CONVERSATION_SERVICE_POSTGRES_HOST
DB_PORT=$CONVERSATION_SERVICE_POSTGRES_PORT

# These variables are sourced from the .env.dev file via docker-compose
echo "Waiting for database at $DB_HOST:$DB_PORT..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "Database is ready."

# Run the database setup for the conversation_service
echo "Running Alembic migrations..."
python scripts/manage_db.py init
echo "Alembic migrations complete."

# Execute the main command (uvicorn)
echo "Starting Conversation Service..."
exec "$@"
