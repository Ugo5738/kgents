#!/bin/sh
set -e

# Install shared package in development mode if present
if [ -d "/shared" ]; then
  echo "Installing shared package in development mode..."
  pip install -e /shared
  echo "Shared package installed successfully."
fi

# Start the service
echo "Starting Agent Runtime Service..."
exec "$@"
