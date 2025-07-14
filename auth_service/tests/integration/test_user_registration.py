import uuid

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import fixtures and test data manager
from tests.fixtures.test_data import TestDataManager

from auth_service.logging_config import logger

# Import models for database verification
from auth_service.models.profile import Profile

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


async def test_register_user_success(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_supabase_client,
    test_data: TestDataManager,
):
    """
    Tests successful user registration.
    Verifies:
    1. The API returns a 201 Created status.
    2. The response contains the correct profile information and a success message.
    3. A new Profile record is created in the database with the correct data.
    """
    # Configure a custom user in the mock Supabase client
    test_email = f"test.user.{uuid.uuid4().hex[:8]}@example.com"
    test_username = f"testuser_{uuid.uuid4().hex[:8]}"

    # Use enhanced mock to configure a specific user
    mock_supabase_client.configure_user(
        {"email": test_email, "user_metadata": {"username": test_username}}
    )

    # Get the test user ID from the enhanced mock
    test_user_id = mock_supabase_client.test_user_id
    logger.info(f"Configured mock Supabase with user ID: {test_user_id}")

    # Arrange: Define test user data using the same email for consistency
    user_data = {
        "email": test_email,
        "password": "a-very-secure-password123",
        "username": test_username,
        "first_name": "Test",
        "last_name": "User",
    }

    logger.info(f"Testing registration with user: {user_data['email']}")

    # Act: Make the API call to the registration endpoint
    response = await client.post("/api/v1/auth/users/register", json=user_data)

    # Log response for debugging
    logger.info(f"Registration response status: {response.status_code}")
    if response.status_code != status.HTTP_201_CREATED:
        logger.error(f"Response body: {response.text}")

    # Assert: Check the API response
    assert (
        response.status_code == status.HTTP_201_CREATED
    ), f"Expected 201 but got {response.status_code}: {response.text}"

    # Parse response data
    response_data = response.json()

    # Verify response content
    assert "message" in response_data, "Response missing 'message' field"
    assert "profile" in response_data, "Response missing 'profile' field"
    assert response_data["message"] == "User registered successfully."
    assert response_data["profile"]["email"] == user_data["email"]
    assert response_data["profile"]["username"] == user_data["username"]
    assert response_data["profile"]["first_name"] == user_data["first_name"]
    assert response_data["profile"]["last_name"] == user_data["last_name"]

    # Verify database state using the test database session
    result = await db_session.execute(
        select(Profile).where(
            (Profile.email == user_data["email"]) & (Profile.user_id == test_user_id)
        )
    )
    profile = result.scalars().first()

    # Verify that the profile exists with correct data
    assert (
        profile is not None
    ), f"Profile for {user_data['email']} not found in the database"

    # Convert test_user_id to UUID for comparison with profile.user_id (which is UUID object)
    test_user_uuid = (
        uuid.UUID(test_user_id) if isinstance(test_user_id, str) else test_user_id
    )

    # Now compare UUID objects
    assert (
        profile.user_id == test_user_uuid
    ), f"Profile user_id {profile.user_id} does not match test user ID {test_user_uuid}"
    assert profile.email == user_data["email"]
    assert profile.username == user_data["username"]
    assert profile.first_name == user_data["first_name"]
    assert profile.last_name == user_data["last_name"]

    logger.info(
        f"Successfully verified profile in database: {profile.email} with user_id: {profile.user_id}"
    )
