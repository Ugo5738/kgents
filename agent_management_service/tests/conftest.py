"""
Main conftest file that imports and re-exports all fixtures from modular files.
This approach improves maintainability by organizing fixtures into logical modules.
"""

import asyncio
import os

from dotenv import load_dotenv

# Explicitly load the test environment variables before importing any app modules
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env.test")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)
else:
    print(f"Warning: .env.test file not found at {dotenv_path}")

# Now reload the config to ensure it picks up test settings
from importlib import reload

from agent_management_service import config

reload(config)

# Make seed_test_user available as a fixture as well for convenience
import pytest

# Import and re-export fixtures from modular files
# This keeps this file clean while allowing tests to import fixtures normally
from tests.fixtures.client import client
from tests.fixtures.db import db_session, event_loop, setup_test_database
from tests.fixtures.helpers import create_test_agent, create_test_agent_version, seed_test_user
from tests.fixtures.mocks import MockCrud, mock_auth_service_client


@pytest.fixture
def test_user_helper():
    """Return the seed_test_user helper function directly as a fixture."""
    return seed_test_user


@pytest.fixture
def test_agent_helper():
    """Return the create_test_agent helper function directly as a fixture."""
    return create_test_agent


@pytest.fixture
def test_agent_version_helper():
    """Return the create_test_agent_version helper function directly as a fixture."""
    return create_test_agent_version


# Mock JWT token for authentication in tests
@pytest.fixture
def mock_token() -> str:
    """Return a mock JWT token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IlRlc3QgVXNlciIsImlhdCI6MTUxNjIzOTAyMn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"


# Mock user ID for testing
@pytest.fixture
def test_user_id() -> str:
    """Return a test user ID for testing."""
    # Use the same test user ID as defined in the .env.test file and fixtures
    return os.environ.get("TEST_USER_ID", "00000000-0000-0000-0000-000000000001")


# This fixture mocks the validate_token dependency
@pytest.fixture
def mock_validate_token(monkeypatch, test_user_id):
    """Mock the validate_token function to always succeed."""
    async def mock_func(*args, **kwargs):
        return {"sub": test_user_id, "name": "Test User"}
    
    # Import here to avoid circular imports
    from agent_management_service.dependencies import auth
    monkeypatch.setattr(auth, "validate_token", mock_func)
