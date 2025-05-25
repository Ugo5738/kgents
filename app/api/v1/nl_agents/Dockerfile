FROM python:3.12-slim

WORKDIR /app

# Install Poetry for dependency management
RUN pip install --no-cache-dir poetry

# Copy project metadata and install dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-dev --no-interaction --no-ansi

# Copy application code
COPY . .

# Expose the service port
EXPOSE 8000

# Start the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 