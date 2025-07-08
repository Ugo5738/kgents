# tool_registry_service/Dockerfile
# Base image for development
FROM python:3.12-slim

# Set environment variables for Poetry and Python
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy only the dependency files to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Install all dependencies, including dev dependencies
RUN poetry install --no-root

# Copy the shared library code into the container
COPY ../shared ./shared

# Copy the entire service source code
COPY . .

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Expose the port the app runs on
EXPOSE 8000

# Start the development server with hot-reloading
CMD ["uvicorn", "src.tool_registry_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]