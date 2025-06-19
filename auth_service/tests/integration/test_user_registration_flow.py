"""
Integration tests for the complete user registration flow.
Tests the registration route with mocked external dependencies but real internal components.
"""
import pytest
import uuid
from datetime import datetime, timezone
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from auth_service.main import app
from auth_service.supabase_client import get_supabase_client
from auth_service.dependencies.app_deps import get_app_settings
from auth_service.db import get_db


# Helper classes to mimic Supabase response structures
class SupabaseAuthResponse:
    def __init__(self, user, session):
        self.user = user
        self.session = session

class SupabaseUser:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        
    def model_dump(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

class SupabaseSession:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        
    def model_dump(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


@pytest.mark.asyncio
async def test_register_user_integration():
    """
    Integration test for user registration flow.
    Tests the complete registration process including:
    1. API endpoint functionality
    2. Request validation
    3. Supabase client integration
    4. Database profile creation
    5. Response formatting
    """
    # Arrange - Test User Data
    user_data = {
        "email": f"test.{uuid.uuid4()}@example.com",
        "password": "SecurePassword123!",
        "username": f"testuser_{uuid.uuid4().hex[:8]}",
        "first_name": "Test",
        "last_name": "User"
    }
    
    # Create mock Supabase response with proper object structure
    mock_user_id = str(uuid.uuid4())
    mock_user = SupabaseUser(
        id=mock_user_id,
        aud="authenticated",
        role="authenticated",
        email=user_data["email"],
        phone=None,
        email_confirmed_at=None,  # Important: None to trigger confirmation flow
        phone_confirmed_at=None,
        confirmed_at=None,
        last_sign_in_at=datetime.now(timezone.utc).isoformat(),
        app_metadata={"provider": "email"},
        user_metadata={},
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat()
    )
    
    mock_session = SupabaseSession(
        access_token="mock.jwt.token",
        token_type="bearer",
        expires_in=3600,
        refresh_token="mock.refresh.token",
        user=mock_user
    )
    
    # Mock Supabase Client for authentication
    mock_supabase = AsyncMock()
    mock_auth = AsyncMock()
    mock_auth.sign_up.return_value = SupabaseAuthResponse(mock_user, mock_session)
    mock_supabase.auth = mock_auth
    
    # Create a mock DB session
    mock_db = AsyncMock()
    # Mock the create_profile_in_db function to return a "successful" result
    mock_profile = MagicMock()
    mock_profile.user_id = mock_user_id
    mock_profile.email = user_data["email"]
    mock_profile.username = user_data["username"]
    mock_profile.first_name = user_data["first_name"]
    mock_profile.last_name = user_data["last_name"]
    mock_profile.is_active = True
    mock_profile.created_at = datetime.now(timezone.utc)
    
    # Apply dependency overrides
    app.dependency_overrides[get_supabase_client] = lambda: mock_supabase
    app.dependency_overrides[get_db] = lambda: mock_db
    
    # Use patch to mock the user_crud operations
    with patch('auth_service.crud.user_crud.create_profile_in_db') as mock_create_profile:
        # Setup mock return value for create_profile_in_db
        mock_create_profile.return_value = mock_profile
        
        try:
            # Act - Make request to registration endpoint
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/auth/users/register", 
                    json=user_data
                )
            
            # Assert
            # 1. Status code check
            assert response.status_code == status.HTTP_201_CREATED, f"Expected 201, got {response.status_code}: {response.text}"
            
            # 2. Response structure check
            data = response.json()
            assert "message" in data
            assert "session" in data
            assert "profile" in data
            
            # 3. Response content check
            assert data["message"] == "User registration initiated. Please check your email to confirm your account."
            assert data["session"]["access_token"] == mock_session.access_token
            assert data["profile"]["email"] == user_data["email"]
            assert data["profile"]["username"] == user_data["username"]

            # Verify Supabase was called with correct parameters
            mock_auth.sign_up.assert_called_once_with(
                {
                    "email": user_data["email"],
                    "password": user_data["password"],
                    "options": {"data": {
                        "username": user_data["username"],
                        "first_name": user_data["first_name"],
                        "last_name": user_data["last_name"],
                    }}
                }
            )
            
            # Verify the database function was called
            mock_create_profile.assert_called_once()
        
        finally:
            # Clean up dependency overrides
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_user_invalid_data():
    """Test registration with invalid data."""
    # Arrange - Invalid User Data (missing required fields)
    invalid_user_data = {
        "email": "test@example.com",
        # Missing password
        "username": "testuser"
        # Missing first_name and last_name
    }
    
    # Act - Make request to registration endpoint
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/users/register", 
            json=invalid_user_data
        )
    
    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # Verify validation error details
    data = response.json()
    assert "detail" in data
    errors = data["detail"]
    error_fields = [error["loc"][1] for error in errors]
    assert "password" in error_fields  # Should complain about missing password


@pytest.mark.asyncio
async def test_register_user_supabase_error():
    """Test registration when Supabase throws an error."""
    # Arrange - Test User Data
    user_data = {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User"
    }
    
    # Mock Supabase Client that raises an exception
    mock_supabase = AsyncMock()
    mock_auth = AsyncMock()
    mock_auth.sign_up.side_effect = Exception("Supabase connection error")
    mock_supabase.auth = mock_auth
    
    # Create a mock DB session
    mock_db = AsyncMock()
    
    # Apply dependency overrides
    app.dependency_overrides[get_supabase_client] = lambda: mock_supabase
    app.dependency_overrides[get_db] = lambda: mock_db
    
    try:
        # Act - Make request to registration endpoint
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/users/register", 
                json=user_data
            )
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Check that we have a meaningful error message
        data = response.json()
        assert "detail" in data
        
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()
