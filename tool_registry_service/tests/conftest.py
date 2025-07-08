"""
Test configuration for the Tool Registry Service.

This module provides test fixtures for database access, authentication,
and API client testing.
"""

import asyncio
import os
import uuid
from typing import AsyncGenerator, Dict, Generator, List

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from tool_registry_service.config import settings
from tool_registry_service.db import Base, get_db
from tool_registry_service.models.tool import (
    ExecutionEnvironment,
    ToolCategory,
    ToolType,
)

# Use a test database URL - this should be a unique database for testing
# We'll use the DATABASE_URL from settings if set, or construct a test URL
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/tool_registry_dev_db",
)


# Create async database engine for tests
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)

# Session factory for test database
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Import the app here to avoid circular imports
from tool_registry_service.main import app as fastapi_app


# Override the dependency for database sessions in tests
async def override_get_db_session():
    """
    Override the database session dependency for testing.

    Yields:
        AsyncSession: Test database session
    """
    async with TestingSessionLocal() as session:
        yield session


fastapi_app.dependency_overrides[get_db] = override_get_db_session


# Auth testing helpers
def mock_get_current_user_id():
    """Mock the get_current_user_id dependency."""
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


def mock_check_admin_role():
    """Mock the check_admin_role dependency."""
    return True


# Fixture for the FastAPI test client
@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an AsyncClient for testing FastAPI routes.

    Yields:
        AsyncClient: HTTP test client
    """
    async with AsyncClient(app=fastapi_app, base_url="http://test") as client:
        yield client


# Fixture for the database session
@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for a test.

    Yields:
        AsyncSession: Database session
    """
    # Create tables for testing - will be dropped and recreated for each test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    # Clean up: drop all tables after tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Fixture for seeding test data
@pytest_asyncio.fixture
async def seed_test_data(db_session: AsyncSession) -> AsyncGenerator[Dict, None]:
    """
    Seed test data into the database.

    Args:
        db_session: Database session

    Yields:
        Dict: Dictionary containing test data references
    """
    # Create test data
    test_data = {}

    # Create categories
    categories = []
    for i, name in enumerate(["API Tools", "Code Tools", "Utility Tools"]):
        category = ToolCategory(
            id=uuid.uuid4(),
            name=name,
            description=f"Test category {i+1}",
            display_order=i,
        )
        db_session.add(category)
        categories.append(category)

    await db_session.commit()

    # Add categories to test data
    test_data["categories"] = categories

    # Create user IDs for testing
    test_data["user_ids"] = {
        "owner": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "other": uuid.UUID("00000000-0000-0000-0000-000000000002"),
    }

    yield test_data

    # Clean up is handled by the db_session fixture


# Event loop fixture
@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for each test.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
