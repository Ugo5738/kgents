"""
Integration tests for the complete user registration flow.
Tests the registration route with mocked external dependencies but real internal components.
"""

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from tests.fixtures.db import get_test_engine

# Import the test data manager and fixtures
from tests.fixtures.test_data import DataManager

from auth_service.logging_config import logger

# Import our models to check database state
from auth_service.models.profile import Profile

# Import our mock AuthApiError
from tests.fixtures.mocks import AuthApiError as MockAuthApiError

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


# We're now using the enhanced mock Supabase client from fixtures/mocks.py
# which provides MockSupabaseUser, MockSupabaseSession, and MockSupabaseResponse classes


async def test_register_user_integration(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_supabase_client,
    test_data: DataManager,
):
    """
    Integration test for user registration flow.
    Tests the complete registration process including:
    1. API endpoint functionality
    2. Request validation
    3. Supabase client integration
    4. Database profile creation
    5. Response formatting
    """
    # Configure a custom user in the mock Supabase client
    test_email = f"test.user.{uuid.uuid4().hex[:8]}@example.com"
    test_username = f"testuser_{uuid.uuid4().hex[:8]}"

    # Generate a fixed test user ID to use throughout the test
    test_user_id = str(uuid.uuid4())

    # Create a new mock response with our fixed test user ID
    from tests.fixtures.mocks import MockSupabaseResponse

    # Create user data with our fixed ID
    test_user_data = {
        "id": test_user_id,
        "email": test_email,
        "user_metadata": {"username": test_username},
        "app_metadata": {},
        "phone": None,
        "phone_confirmed_at": None,
        "email_confirmed_at": datetime.utcnow().isoformat(),
        "confirmed_at": datetime.utcnow().isoformat(),
        "last_sign_in_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "identities": [],
        "aud": "authenticated",
        "role": "authenticated",
    }

    # Create a mock response with our fixed test user ID
    mock_response = MockSupabaseResponse(test_user_data)

    # Override sign_up to return our specific mock response
    mock_supabase_client.auth.sign_up.return_value = mock_response

    # Update the test_user_id on the mock client for consistency
    mock_supabase_client.test_user_id = test_user_id
    mock_supabase_client.auth.test_user_id = test_user_id

    logger.info(f"Configured mock Supabase with user ID: {test_user_id}")

    # We need to directly set up the test user in the auth.users table for the foreign key constraint
    # Using a fresh connection to avoid transaction issues
    engine = get_test_engine()

    try:
        # Create independent connection to insert auth user
        async with engine.begin() as conn:
            # Create the auth user to satisfy FK constraint
            await conn.execute(
                text(
                    """
                INSERT INTO auth.users 
                    (id, email, email_confirmed_at, created_at, updated_at, raw_app_meta_data, raw_user_meta_data) 
                VALUES 
                    (:user_id, :email, now(), now(), now(), '{}'::jsonb, '{}'::jsonb)
                ON CONFLICT (id) DO NOTHING
            """
                ),
                {"user_id": test_user_id, "email": test_email},
            )

            # Verify the user was actually inserted - this is crucial
            result = await conn.execute(
                text(
                    """
                SELECT id FROM auth.users WHERE id = :user_id
            """
                ),
                {"user_id": test_user_id},
            )

            row = result.fetchone()
            if row:
                logger.info(f"Verified user in auth.users table: {row[0]}")
            else:
                logger.error(
                    f"Failed to find user {test_user_id} in auth.users after insertion"
                )
                raise RuntimeError(
                    f"User {test_user_id} not found in auth.users after insertion"
                )

        logger.info(f"Created mock Supabase user in auth.users table: {test_user_id}")
    except Exception as e:
        logger.error(f"Error creating mock user in auth.users table: {e}")
        raise  # Raise the exception to fail the test - we need to know about insert failures

    # Arrange - Test User Data with unique identifiers
    user_data = {
        "email": test_email,
        "password": "SecurePassword123!",
        "username": test_username,
        "first_name": "Test",
        "last_name": "User",
    }

    logger.info(f"Testing integration registration with user: {user_data['email']}")

    # Act - Make request to registration endpoint
    # Use correct URL format with /api/v1 prefix
    response = await client.post("/api/v1/auth/users/register", json=user_data)

    # Log response for debugging
    logger.info(f"Integration registration response status: {response.status_code}")
    if response.status_code != status.HTTP_201_CREATED:
        logger.error(f"Integration registration response: {response.text}")

    # Assert - Check the response
    assert (
        response.status_code == status.HTTP_201_CREATED
    ), f"Expected 201, got {response.status_code}: {response.text}"

    # Parse response data
    data = response.json()

    # 1. Response structure check
    assert "message" in data, "Response missing 'message' field"
    assert "profile" in data, "Response missing 'profile' field"

    # 2. Response content check
    # Since our mock user has email_confirmed_at set, the message will be 'User registered successfully.'
    assert data["message"] == "User registered successfully."

    # Get the profile details from the response
    profile_data = data["profile"]

    # 3. Check profile fields in response
    assert profile_data["email"] == user_data["email"]
    assert profile_data["username"] == user_data["username"]
    assert profile_data["first_name"] == user_data["first_name"]
    assert profile_data["last_name"] == user_data["last_name"]
    assert "id" in profile_data, "Profile should have an ID"

    # 4. Verify that a profile was actually created in the database
    # This verifies the database operation actually happened
    result = await db_session.execute(
        select(Profile).where(
            (Profile.email == user_data["email"]) & (Profile.user_id == test_user_id)
        )
    )
    profile = result.scalars().first()

    assert (
        profile is not None
    ), f"Profile for {user_data['email']} not found in database"
    # Convert test_user_id to UUID for comparison
    test_user_uuid = (
        uuid.UUID(test_user_id) if isinstance(test_user_id, str) else test_user_id
    )

    # 5. Verify database values match expected values
    assert profile.user_id == test_user_uuid
    assert profile.email == user_data["email"]
    assert profile.username == user_data["username"]
    assert profile.first_name == user_data["first_name"]
    assert profile.last_name == user_data["last_name"]
    assert profile.is_active is True


async def test_register_user_invalid_data(client: AsyncClient):
    """Test registration with invalid data."""
    # Arrange - Invalid User Data (missing required fields)
    invalid_user_data = {
        "email": "test@example.com",
        # Missing password
        "username": "testuser",
        # Missing first_name and last_name
    }

    logger.info("Testing registration with invalid data")

    # Act - Make request to registration endpoint
    response = await client.post("/auth/users/register", json=invalid_user_data)

    logger.info(f"Invalid data response status: {response.status_code}")

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Verify validation error details
    data = response.json()
    assert "detail" in data
    errors = data["detail"]
    error_fields = [error["loc"][1] for error in errors]
    assert "password" in error_fields, "Validation should reject missing password"
    logger.info("Validation correctly rejected invalid data")


# We're now using the MockSupabaseUser and MockSupabaseSession classes from fixtures/mocks.py


@patch('auth_service.routers.user_auth_routes.SupabaseAPIError', MockAuthApiError)
async def test_register_user_supabase_error(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_supabase_client,
    test_data: DataManager,
):
    """Test registration when Supabase throws an error."""
    # Configure a unique user email and username for this test
    test_email = f"error.user.{uuid.uuid4().hex[:8]}@example.com"
    test_username = f"erroruser_{uuid.uuid4().hex[:8]}"

    # Arrange - Test User Data with unique identifiers
    user_data = {
        "email": test_email,
        "password": "SecurePassword123!",
        "username": test_username,
        "first_name": "Error",
        "last_name": "Test",
    }

    logger.info(f"Testing Supabase error handling for: {user_data['email']}")

    # Generate a fixed test user ID for error test
    test_user_id = str(uuid.uuid4())

    # Create a new mock response with our fixed test user ID
    from tests.fixtures.mocks import MockSupabaseResponse

    # Create user data with our fixed ID
    test_user_data = {
        "id": test_user_id,
        "email": test_email,
        "user_metadata": {"username": test_username},
        "app_metadata": {},
        "phone": None,
        "phone_confirmed_at": None,
        "email_confirmed_at": datetime.utcnow().isoformat(),
        "confirmed_at": datetime.utcnow().isoformat(),
        "last_sign_in_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "identities": [],
        "aud": "authenticated",
        "role": "authenticated",
    }

    # Set the test_user_id on the mock client for consistency
    mock_supabase_client.test_user_id = test_user_id
    mock_supabase_client.auth.test_user_id = test_user_id

    # We'll use our mock AuthApiError rather than importing the real one
    # This will be patched to replace the real AuthApiError in the router
    mock_supabase_client.auth.sign_up.side_effect = MockAuthApiError(
        "User already registered", 409, "user_already_registered"
    )

    logger.info(f"Configured mock Supabase with user ID: {test_user_id}")

    # We need to set up the test user in the auth.users table first
    engine = get_test_engine()

    try:
        # Create independent connection to insert auth user
        async with engine.begin() as conn:
            # Create the auth user to satisfy FK constraint
            await conn.execute(
                text(
                    """
                INSERT INTO auth.users 
                    (id, email, email_confirmed_at, created_at, updated_at, raw_app_meta_data, raw_user_meta_data) 
                VALUES 
                    (:user_id, :email, now(), now(), now(), '{}'::jsonb, '{}'::jsonb)
                ON CONFLICT (id) DO NOTHING
            """
                ),
                {"user_id": test_user_id, "email": test_email},
            )

            # Verify the user was actually inserted
            result = await conn.execute(
                text(
                    """
                SELECT id FROM auth.users WHERE id = :user_id
            """
                ),
                {"user_id": test_user_id},
            )

            row = result.fetchone()
            if row:
                logger.info(f"Verified user in auth.users table: {row[0]}")
            else:
                logger.error(
                    f"Failed to find user {test_user_id} in auth.users after insertion"
                )
                raise RuntimeError(
                    f"User {test_user_id} not found in auth.users after insertion"
                )

        logger.info(f"Created mock Supabase user in auth.users table: {test_user_id}")
    except Exception as e:
        logger.error(f"Error creating mock user in auth.users table: {e}")
        raise  # Raise the exception to fail the test

    # Configure the mock Supabase client to return an authentication error
    # This is much cleaner with our enhanced mock infrastructure
    mock_supabase_client.set_auth_error("sign_up")

    # Act - Make the registration request which should now fail due to the mocked error
    response = await client.post("/auth/users/register", json=user_data)

    logger.info(f"Supabase error test response status: {response.status_code}")

    # Assert - We should get an error status code
    assert (
        response.status_code != status.HTTP_201_CREATED
    ), "Should not succeed when Supabase auth errors"
    # In our implementation, auth errors for already registered users return 409 Conflict
    assert (
        response.status_code == status.HTTP_409_CONFLICT
    ), "Should return 409 Conflict on duplicate registration error"

    # Parse the response to check error details
    data = response.json()
    assert "detail" in data, "Error response should include detail field"

    # Verify no profile was created in the database despite the error
    result = await db_session.execute(
        select(Profile).where(Profile.email == user_data["email"])
    )
    profile = result.scalars().first()
    assert (
        profile is None
    ), f"No profile should be created when Supabase errors, but found: {profile}"

    logger.info("Supabase error test completed successfully")
