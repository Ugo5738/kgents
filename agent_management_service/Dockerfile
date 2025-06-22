# agent_management_service/Dockerfile
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

# Install Poetry
RUN pip install poetry

# Copy only pyproject.toml first to leverage Docker cache
COPY pyproject.toml ./

# Generate the lock file if it doesn't exist and install all dependencies
RUN poetry lock && poetry install --no-root

# Copy the entire service source code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Start the development server with hot-reloading
CMD ["uvicorn", "src.agent_management_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]