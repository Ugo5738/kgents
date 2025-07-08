# Tool Registry Service Testing Guide

This document provides guidelines and instructions for testing the Tool Registry Service.

## Testing Architecture

The Tool Registry Service follows a comprehensive testing approach with multiple layers:

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test interactions between components
3. **API Tests**: Test HTTP endpoints and responses
4. **End-to-End Tests**: Test complete workflows

### Test Directory Structure

```
tests/
├── conftest.py           # Test configuration and fixtures
├── fixtures/             # Test data factories
│   └── tools.py          # Tool and category fixtures
├── integration/          # Integration tests
│   ├── test_category_routes.py
│   └── test_tool_routes.py
├── unit/                 # Unit tests
│   ├── test_category_crud.py
│   └── test_tool_crud.py
└── utils/                # Testing utilities
    ├── auth.py           # Authentication test helpers
    └── db.py             # Database test helpers
```

## Setting Up the Test Environment

### Prerequisites

- Python 3.12+
- Poetry
- PostgreSQL (for integration tests)
- Docker (optional, for containerized testing)

### Local Test Setup

1. **Install test dependencies**:
   ```bash
   poetry install --with dev
   ```

2. **Set up test environment variables**:
   ```bash
   cp .env.example .env.test
   # Edit .env.test with test settings
   ```

3. **Create test database**:
   ```bash
   # Using the migration script
   python scripts/manage_migrations.py create-db --name tool_registry_test_db
   
   # Or using Docker Compose (if using containerized PostgreSQL)
   docker-compose -f docker-compose.test.yml up -d postgres
   ```

## Running Tests

### Running All Tests

```bash
# Using pytest directly
pytest

# Using Docker Compose
docker-compose -f docker-compose.test.yml up --build
```

### Running Specific Tests

```bash
# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run a specific test file
pytest tests/unit/test_category_crud.py

# Run a specific test function
pytest tests/unit/test_category_crud.py::test_create_tool_category
```

### Test Output and Coverage

```bash
# Run tests with coverage report
pytest --cov=src.tool_registry_service tests/

# Generate HTML coverage report
pytest --cov=src.tool_registry_service --cov-report=html tests/
# Report will be in htmlcov/ directory
```

## Test Fixtures

The test suite includes several fixtures to simplify test setup:

### Database Fixtures

- `db_session`: Provides a fresh database session for each test
- `seed_test_data`: Seeds the database with common test data

### Authentication Fixtures

- `override_auth_dependencies`: Mocks authentication and authorization
- `client`: Provides a configured FastAPI test client

## Writing New Tests

### Unit Tests

Unit tests should focus on testing a single function or class in isolation:

```python
@pytest.mark.asyncio
async def test_create_tool_category(db_session):
    # Arrange
    category_data = ToolCategoryCreate(name="Test Category")
    
    # Act
    category = await create_tool_category(db_session, category_data)
    
    # Assert
    assert category.id is not None
    assert category.name == "Test Category"
```

### Integration Tests

Integration tests should test the interaction between components:

```python
@pytest.mark.asyncio
async def test_create_category_api(client, db_session):
    # Arrange
    category_data = {"name": "Test API Category"}
    
    # Act
    response = await client.post("/api/v1/categories/", json=category_data)
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == category_data["name"]
```

### Using Test Fixtures

Use the provided fixtures to simplify test setup:

```python
@pytest.mark.asyncio
async def test_get_tool_by_id(db_session, seed_test_data):
    # Arrange
    tool_id = seed_test_data["tools"][0].id
    
    # Act
    tool = await get_tool(db_session, tool_id)
    
    # Assert
    assert tool.id == tool_id
    assert tool.name == seed_test_data["tools"][0].name
```

### Testing Authentication and Authorization

Use the authentication utilities to test different scenarios:

```python
@pytest.mark.asyncio
async def test_admin_only_endpoint(client):
    # Test with admin user
    setup_auth_overrides(app, is_admin=True)
    response = await client.post("/api/v1/categories/", json={"name": "New Category"})
    assert response.status_code == 201
    
    # Test with non-admin user
    setup_auth_overrides(app, is_admin=False)
    response = await client.post("/api/v1/categories/", json={"name": "New Category"})
    assert response.status_code == 403
    
    # Clean up
    reset_auth_overrides(app)
```

## Mocking External Services

For tests that involve external services, use mocking:

```python
@pytest.fixture
def mock_auth_service(monkeypatch):
    async def mock_validate_token(*args, **kwargs):
        return {"sub": "00000000-0000-0000-0000-000000000001", "roles": ["user"]}
    
    monkeypatch.setattr(
        "tool_registry_service.clients.auth.AuthClient.validate_token",
        mock_validate_token
    )
```

## Continuous Integration

The Tool Registry Service uses automated CI/CD pipelines for testing:

1. **Pull Request Validation**: Runs all tests on pull requests
2. **Main Branch Validation**: Runs all tests when merging to main
3. **Performance Benchmarks**: Runs performance tests periodically

Tests must pass before code can be merged to the main branch.
