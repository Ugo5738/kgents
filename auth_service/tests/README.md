# Auth Service Test Suite

## Overview

This directory contains automated tests for the Auth Service, organized into:

- **Unit Tests**: Testing individual components in isolation
- **Integration Tests**: Testing interaction between components
- **E2E Tests**: Testing complete user workflows

## Test Architecture

The test suite uses:

- **PostgreSQL**: Real database for testing with isolated transactions
- **FastAPI TestClient**: For API endpoint testing
- **Pytest Fixtures**: For test dependencies and setup/teardown
- **Mocking**: For external services like Supabase

## Running Tests

### Prerequisites

- A PostgreSQL test database (created automatically by test fixtures)
- Environment variables set in `.env.test`

### Commands

```bash
# Run all tests with pytest
pytest

# Run specific test files
pytest tests/unit/test_user_crud.py

# Run tests with specific markers
pytest -m "integration"

# Run with coverage report
pytest --cov=auth_service
```

## Test Organization

- `fixtures/`: Shared test fixtures
- `unit/`: Unit tests for individual components
- `integration/`: Integration tests for API endpoints
- `helpers/`: Utility functions for tests

## Key Patterns

1. **Database Isolation**: Each test runs in its own transaction that gets rolled back
2. **Dependency Overrides**: FastAPI dependencies are overridden for testing
3. **Mock Services**: External services are mocked for deterministic testing
