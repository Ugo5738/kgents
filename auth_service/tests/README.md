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

- `fixtures/`: Shared test fixtures and utilities
  - `db.py`: Database connection and transaction management
  - `test_data.py`: Data generation utilities with `DataManager` class
  - `mocks.py`: Mock implementations of external services (Supabase)
  - `helpers.py`: General test helper functions
- `unit/`: Unit tests for individual components
- `integration/`: Integration tests for API endpoints

## Key Patterns

1. **Database Isolation**: Each test runs in its own transaction that gets rolled back
2. **Dependency Overrides**: FastAPI dependencies are overridden for testing
3. **Mock Services**: External services are mocked for deterministic testing
4. **Data Management**: The `DataManager` class provides utilities for creating test data with proper relationships
5. **Response Serialization**: Pydantic models use computed fields and serializers for consistent API responses

## Testing Utilities

### DataManager

The `DataManager` class in `fixtures/test_data.py` provides methods for creating test data with the correct relationships. It handles:

- Profile creation with automatic UUID generation
- Role and permission creation
- User-role relationship management
- Foreign key constraint satisfaction

### Mocks

The test suite includes mock implementations for:

- Supabase authentication client
- Response objects and error types
- JWT validation

### Response Validation

Tests validate that API responses match the expected schemas, including:

- Field presence and types
- Proper serialization of UUIDs and dates
- Consistent handling of nested objects
