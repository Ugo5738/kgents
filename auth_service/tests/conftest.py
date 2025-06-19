import os

from dotenv import load_dotenv

# Explicitly load the test environment variables at the very start.
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env.test")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)
else:
    print(f"Warning: .env.test file not found at {dotenv_path}")

from importlib import reload

from auth_service import config

reload(config)
import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
import uuid
from fastapi import FastAPI, Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text  # <-- Import the 'text' construct
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, patch, MagicMock

from auth_service.config import settings
from auth_service.db import Base, get_db
from auth_service.supabase_client import get_supabase_client
from auth_service.crud import user_crud

# Import our mocks - use a direct import rather than package-style import
from mocks import MockCrud

# Create a test-specific app instance
# Use imported app as a template but customize for tests
from auth_service.main import app as fastapi_app

# Ensure the root_path is set to empty string for tests
fastapi_app.root_path = ""

engine = create_async_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """
    Manages the test database schema across the entire test session.
    """
    async with engine.begin() as conn:
        # Drop all tables first to ensure a clean state
        await conn.run_sync(Base.metadata.drop_all)

        # --- FIX: Create the 'auth' schema required by our models ---
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth;"))

        # Now, create all tables
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Teardown: drop all tables after the test session finishes
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def mock_supabase_client():
    """
    Create a mock Supabase client for testing that responds to authentication methods.
    """
    # Use our MockSupabaseResponse class which will create properly structured mock objects
    from mocks import MockSupabaseResponse
    
    # Create a mock response with user and session data
    mock_auth_response = MockSupabaseResponse()
    
    # Configure the sign_up method to return our mock response
    mock_auth = AsyncMock()
    mock_auth.sign_up = AsyncMock(return_value=mock_auth_response)
    
    # Create the main Supabase client mock
    mock_client = AsyncMock()
    mock_client.auth = mock_auth
    
    return mock_client

@pytest_asyncio.fixture
async def client(db_session: AsyncSession, mock_supabase_client) -> AsyncGenerator[AsyncClient, None]:
    """
    Provides an HTTP client for making requests to the FastAPI app.
    It overrides the `get_db` dependency to use the isolated test database session
    and the Supabase client dependency to use our mock.
    """

    def override_get_db() -> Generator[AsyncSession, None, None]:
        """Dependency override to use the test session."""
        yield db_session

    def override_get_supabase_client():
        """Dependency override to use the mock Supabase client."""
        return mock_supabase_client

    # Apply the dependency overrides
    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_supabase_client] = override_get_supabase_client
    
    # Patch the user_crud.create_profile_in_db method
    # This avoids the database operation that would cause the foreign key violation
    with patch('auth_service.crud.user_crud.create_profile_in_db', MockCrud.create_profile_in_db):
        # Instantiate AsyncClient using ASGITransport
        transport = ASGITransport(app=fastapi_app)
        
        # Important: FastAPI test client maintains the full route structure including prefixes
        # Our app has routes with /api/v1 prefix and router has /auth/users prefix
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    # Clean up the overrides after the test
    del fastapi_app.dependency_overrides[get_db]
    del fastapi_app.dependency_overrides[get_supabase_client]
