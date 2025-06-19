# app/api/v1/auth/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install Poetry for dependency management
RUN pip install --no-cache-dir poetry

# Copy only pyproject.toml and poetry.lock first for dependency caching
# This ensures that Docker reuses the dependency layer if only app code changes
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-dev --no-interaction --no-ansi

# Copy necessary application code for this specific service and shared modules
# Service-specific code:
COPY app/api/v1/auth /app/app/api/v1/auth

# Shared modules:
COPY app/core /app/app/core
COPY app/models /app/app/models
COPY app/db /app/app/db

# Main app entrypoint (if your main.py includes routers from all services)
COPY main.py /app/main.py
# If main.py is in an 'app' directory:
# COPY app/main.py /app/app/main.py
# Adjust CMD accordingly if main.py is in app/ e.g., "app.main:app"

# Ensure all necessary top-level __init__.py files are copied if they affect imports
COPY app/__init__.py /app/app/__init__.py
COPY app/api/__init__.py /app/app/api/__init__.py
COPY app/api/v1/__init__.py /app/app/api/v1/__init__.py


# Expose the service port
EXPOSE 8000

# Start the FastAPI app - assuming main.py is at the root of WORKDIR /app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]