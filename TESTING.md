# Kgents Platform Testing Strategy

This document outlines the comprehensive testing strategy for the Kgents Agent-as-a-Service platform, covering unit, integration, and end-to-end testing approaches.

## Testing Pyramid

We follow the testing pyramid approach to ensure comprehensive coverage with an optimal balance of speed and reliability:

```
    /\
   /  \      E2E Tests (10%)
  /----\
 /      \    Integration Tests (30%)
/________\   Unit Tests (60%)
```

## Test Directory Structure

Each microservice follows a consistent test directory structure:

```
service_name/
├── tests/
│   ├── unit/              # Isolated unit tests
│   │   ├── test_models.py
│   │   ├── test_schemas.py
│   │   ├── test_crud.py
│   │   ├── test_routes.py
│   │   └── test_services.py
│   ├── integration/       # Service integration tests
│   │   └── test_*_flow.py
│   ├── fixtures/          # Modular test fixtures
│   │   ├── client.py      # Test client fixtures
│   │   ├── db.py          # Database fixtures
│   │   └── helpers.py     # Helper functions for tests
│   ├── mocks.py           # Common mock classes/functions
│   └── conftest.py        # Pytest fixtures
└── src/
    └── ...

kgents/                    # Project root
├── tests/                 # Cross-service tests
│   ├── e2e/               # End-to-end tests
│   │   ├── conftest.py    # E2E test fixtures
│   │   └── test_*.py      # E2E test cases
│   └── performance/       # Performance/load tests
└── ...
```

## Unit Testing Strategy

Unit tests focus on testing individual components in isolation:

### What to Test

- **Pydantic Models/Schemas**: Validation rules, default values, field transformations
- **Database Models**: Properties, relationships, methods
- **CRUD Functions**: Database operations with mocked sessions
- **Route Handlers**: Request handling logic with mocked dependencies
- **Services/Utilities**: Helper functions, transformations, calculations
- **Security**: Authentication, authorization, JWT handling, password hashing

### Test Isolation

We use dependency injection and mocking to isolate components:

```python
# Example: Testing route with mocked dependencies
@pytest.mark.asyncio
async def test_get_user_profile():
    # Arrange
    mock_db_session = AsyncMock()
    mock_profile = Profile(...)

    # Configure mock to return our test profile
    mock_db_session.execute.return_value = AsyncMock()
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_profile

    # Act
    result = await get_user_profile(user_id=uuid.uuid4(), db_session=mock_db_session)

    # Assert
    assert result.username == mock_profile.username
    # ...more assertions
```

## Integration Testing Strategy

Integration tests verify that components work together correctly:

### What to Test

- **Route-to-Database Integration**: Testing API endpoints with real database sessions
- **Service-to-Service Communication**: Testing how services interact
- **External Dependencies**: Testing integration with Supabase, LLM providers, etc.
- **Authentication Flow**: Testing the complete auth flow from login to protected resource access

### Test Setup

- Use test-specific databases or schemas
- Initialize database with known test data
- Override external dependencies with test doubles when necessary

```python
# Example: Integration test with test database
@pytest.mark.asyncio
async def test_user_registration_db_integration(test_db_session):
    # Arrange
    client = AsyncClient(app=app, base_url="http://test")
    user_data = {...}

    # Act
    response = await client.post("/api/v1/auth/users/register", json=user_data)

    # Assert API response
    assert response.status_code == 201

    # Verify database state
    result = await test_db_session.execute(
        select(Profile).where(Profile.email == user_data["email"])
    )
    profile = result.scalar_one_or_none()
    assert profile is not None
    assert profile.username == user_data["username"]
```

## End-to-End (E2E) Testing Strategy

E2E tests validate complete user journeys across the entire platform:

### What to Test

- **User Registration to Agent Deployment**: The complete user journey
- **Cross-Service Workflows**: Processes spanning multiple services
- **Real External Integrations**: Testing with actual (or well-simulated) external services

### Test Implementation

- Spin up all required services for testing
- Create realistic test data
- Execute complete workflows
- Verify system state at each step

## Mock Strategy

We use the following approach to mocking:

1. **Custom Mock Classes**: For complex external dependencies with specific behavior
2. **AsyncMock**: For asynchronous dependencies and coroutines
3. **Dependency Injection**: Override FastAPI dependencies for testing
4. **FastAPI TestClient**: For API endpoint testing

Example of a custom mock class:

```python
class MockSupabaseClient:
    """Mock Supabase client for testing auth flows."""

    def __init__(self):
        self.auth = MockSupabaseAuth()
        self.table = lambda name: MockSupabaseTable(name)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
```

## Database Testing Strategy

For database-related tests:

1. **Test Database Setup**: Create separate test databases or schemas using the provided utility script
2. **Environment Configuration**: Use a service-specific `.env.test` file to configure test database connections
3. **Migration Testing**: Ensure all migrations apply correctly
4. **Rollbacks**: Use transaction rollbacks to keep tests isolated
5. **Fixtures**: Use pytest fixtures to share database sessions

### Test Database Configuration Example

```python
# In tests/fixtures/db.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

# Create a PostgreSQL engine for testing using settings from .env.test
engine = create_async_engine(
    settings.DATABASE_URL,  # From .env.test
    poolclass=NullPool,
    echo=False,
    future=True
)

# Session fixture with transaction rollback for test isolation
@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    connection = await engine.connect()
    trans = await connection.begin()  # Begin transaction
    session = TestingSessionLocal(bind=connection)

    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()  # Roll back transaction after test
        await connection.close()
```

## Testing Different Service Types

### auth_service Tests

- User registration, login, profile management
- JWT token creation, validation, refresh
- Password security, rate limiting
- Role-based access control (RBAC)

### agent_management_service Tests

- Agent CRUD operations
- Langflow flow validation
- Agent visualization and export
- Agent version management

### tool_registry_service Tests

- Tool registration and documentation
- Tool discovery mechanism
- Security and isolation of tool execution
- Tool versioning and dependency management

### agent_deployment_service Tests

- Agent deployment workflows
- Container creation and orchestration
- Environment configuration
- Scaling and resource management

### agent_runtime_service Tests

- Agent execution
- Tool invocation
- Memory management
- Performance and reliability

## Test Execution and CI/CD

Testing is integrated into our CI/CD pipeline:

1. **Pre-Commit Hooks**: Run unit tests and linting
2. **Pull Request Checks**: Run unit and integration tests
3. **Main Branch Builds**: Run unit, integration, and selected E2E tests
4. **Release Builds**: Run all tests, including complete E2E suite

## Test Coverage

We maintain high test coverage across all services:

- **Unit Tests**: Minimum 80% code coverage
- **Integration Tests**: Cover all main service interactions
- **E2E Tests**: Cover all critical user journeys

Coverage is monitored using pytest-cov and reports are generated as part of the CI/CD pipeline.

## Load and Performance Testing

Performance tests verify the system meets scalability requirements:

- **Load Testing**: Verify system performance under expected load
- **Stress Testing**: Determine system limits and failure modes
- **Scalability Testing**: Verify horizontal scaling capabilities
- **Tools**: Locust, k6, or similar tools for HTTP-based load testing

## Security Testing

Security tests verify system robustness against threats:

- **Authentication Testing**: Verify access control mechanisms
- **Input Validation**: Test against injection attacks
- **Rate Limiting**: Test against DoS attacks
- **Dependency Scanning**: Check for known vulnerabilities in dependencies
- **Secret Management**: Verify secure handling of sensitive information

## Test Data Management

We use a consistent approach to test data:

- **Fixtures**: Use pytest fixtures to generate test data
- **Factories**: Use factory patterns for complex test data creation
- **Cleanup**: Ensure test data is cleaned up after tests
- **Isolation**: Use unique identifiers to avoid test data collision

## Test Environment Management

We manage test environments to ensure consistency:

- **Local Development**: Run tests in Docker containers
- **CI/CD Pipeline**: Use ephemeral test environments
- **Staging**: Deploy to a staging environment for manual testing
- **Production**: Run smoke tests in production after deployment

## Best Practices

- **Test Isolation**: Tests should not depend on each other
- **Test Speed**: Optimize tests for fast execution
- **Test Clarity**: Make test failures easy to understand
- **Test Maintenance**: Regularly review and update tests
- **Test Documentation**: Document test coverage and gaps

## Test Database Management

We use dedicated test databases for each service to ensure test isolation and prevent interference with development data.

### Test Database Creation

We provide a utility script to easily create test databases for each service:

```bash
# Create a test database for a service
./scripts/create_test_db.sh service_name

# Example: Create a test database for auth_service
./scripts/create_test_db.sh auth_service

# With custom connection string
./scripts/create_test_db.sh -c 'postgresql://user:pass@host:port/postgres' service_name

# Get help and usage information
./scripts/create_test_db.sh --help
```

The script will generate a database named `{service_name}_test_db` and provide the connection string to use in your `.env.test` file.

### Usage Workflow

When creating a new service that requires database access, follow these steps:

1. Create the test database:
   ```bash
   # From the project root
   ./scripts/create_test_db.sh my_new_service
   ```

2. Copy the connection string from the output and add it to your service's `.env.test` file:
   ```
   DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/my_new_service_test_db
   ```

3. Configure your test fixtures to use this database via the environment variables.

### Environment Configuration

Each service should contain a `.env.test` file specifically for test configuration, which should include:

```
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/service_name_test_db
```

### Best Practices

- **Never use production databases for testing**: Always create separate test databases
- **Use transaction rollbacks**: Wrap each test in a transaction that gets rolled back
- **Reset between test runs**: If needed, you can recreate the test database between CI runs
- **Migrations**: Ensure your test setup applies all necessary migrations before tests run
