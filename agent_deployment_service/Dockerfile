# agent_deployment_service/Dockerfile
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
    PYTHONPATH=/app/src:/app \
    PATH="/usr/lib/google-cloud-sdk/bin:${PATH}"

WORKDIR /app

# Install Google Cloud SDK and Docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dependencies for gcloud SDK
    curl \
    gnupg \
    apt-transport-https \
    ca-certificates \
    lsb-release \
    # Dependencies for our entrypoint script
    netcat-openbsd \
    postgresql-client \
    # Install Docker CLI for buildx support
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli docker-buildx-plugin \
    # Dependencies for gcloud SDK
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - \
    && apt-get update && apt-get install -y google-cloud-sdk \
    # Clean up apt caches to keep the image small
    && rm -rf /var/lib/apt/lists/*

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
COPY src/agent_deployment_service/templates/ ./src/agent_deployment_service/templates/

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Expose the port the app runs on
EXPOSE 8000

# Start the development server with hot-reloading
CMD uvicorn ${SERVICE_MODULE}.main:app --host 0.0.0.0 --port 8000 --reload