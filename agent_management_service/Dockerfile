# agent_management_service/Dockerfile
# Universal Dockerfile for Kgents Python services
# BUILT FROM WITHIN THE SERVICE DIRECTORY CONTEXT

FROM python:3.12-slim

# Set environment variables for Poetry and Python
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # The container's PYTHONPATH needs to include paths for module resolution
    PYTHONPATH=/app/src:/app

WORKDIR /app

# Install netcat for the entrypoint script and psql for db checks
RUN apt-get update && apt-get install -y netcat-openbsd postgresql-client && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy only pyproject.toml and poetry.lock to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Install all dependencies, including dev dependencies
RUN poetry install --no-root

# Copy the entire service source code into the container's src directory
COPY src ./src
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY scripts ./scripts
COPY entrypoint.sh ./entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Expose the port the app runs on
EXPOSE 8000

# Start the development server with hot-reloading
CMD uvicorn ${SERVICE_MODULE}.main:app --host 0.0.0.0 --port 8000 --reload