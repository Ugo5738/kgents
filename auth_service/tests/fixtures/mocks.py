"""
Mock fixtures for testing.
Provides mock implementations of external dependencies like Supabase client.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Union

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from tests.helpers.test_data_factory import TestDataFactory


class MockSupabaseUser:
    """Mock user object that matches Supabase user schema."""
    
    def __init__(self, user_data: Optional[Dict[str, Any]] = None):
        # Use provided data or generate default test user data
        if user_data is None:
            user_data = TestDataFactory.create_auth_user_data()
            
        # Set all the attributes from user_data
        for key, value in user_data.items():
            setattr(self, key, value)
            
    def model_dump(self) -> Dict[str, Any]:
        """Return user data as a dictionary, mimicking Pydantic's model_dump."""
        return {
            "id": self.id,
            "email": self.email,
            "app_metadata": self.app_metadata,
            "user_metadata": self.user_metadata,
            "phone": self.phone,
            "phone_confirmed_at": self.phone_confirmed_at,
            "email_confirmed_at": self.email_confirmed_at,
            "confirmed_at": self.confirmed_at,
            "last_sign_in_at": self.last_sign_in_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "identities": self.identities,
            "aud": self.aud,
            "role": self.role,
        }


class MockSupabaseSession:
    """Mock session object that matches Supabase session schema."""
    
    def __init__(self, user: Optional[MockSupabaseUser] = None, expires_in: int = 3600):
        self.access_token = f"mock_access_token_{uuid.uuid4().hex[:8]}"
        self.refresh_token = f"mock_refresh_token_{uuid.uuid4().hex[:8]}"
        # Calculate expiration time based on current time plus expires_in seconds
        self.expires_at = int((datetime.now() + timedelta(seconds=expires_in)).timestamp())
        self.token_type = "bearer"
        self.user = user
        
    def model_dump(self) -> Dict[str, Any]:
        """Return session data as a dictionary, mimicking Pydantic's model_dump."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "token_type": self.token_type,
            "user": self.user.model_dump() if self.user else None,
        }


class MockSupabaseResponse:
    """Mock response from Supabase authentication endpoints."""

    def __init__(self, user_data: Optional[Dict[str, Any]] = None, error: Optional[Dict[str, Any]] = None):
        # Store error if provided
        self.error = error
        
        # If there's an error, don't create user/session
        if error:
            return
            
        # Create user and session
        self.user = MockSupabaseUser(user_data)
        self.session = MockSupabaseSession(user=self.user)
        
    @property
    def is_error(self) -> bool:
        """Check if this response represents an error."""
        return self.error is not None


class SupabaseAuthMock(AsyncMock):
    """Enhanced mock for Supabase Auth API with configurable behavior."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Default test user ID and data
        self.test_user_id = str(uuid.uuid4())
        self.test_user_data = TestDataFactory.create_auth_user_data(
            user_id=self.test_user_id,
            email="test@example.com",
            username="test_user"
        )
        
        # Create default responses
        self.default_success_response = MockSupabaseResponse(self.test_user_data)
        
        # Default error responses
        self.auth_error_response = MockSupabaseResponse(
            error={"message": "Invalid credentials", "status": 401}
        )
        self.not_found_error_response = MockSupabaseResponse(
            error={"message": "User not found", "status": 404}
        )
        
        # Setup default behaviors
        self.sign_up = AsyncMock(return_value=self.default_success_response)
        self.sign_in = AsyncMock(return_value=self.default_success_response)
        self.sign_in_with_password = AsyncMock(return_value=self.default_success_response)
        self.sign_in_with_otp = AsyncMock(return_value=self.default_success_response)
        self.refresh_session = AsyncMock(return_value=self.default_success_response)
        self.sign_out = AsyncMock(return_value=None)
        self.reset_password_for_email = AsyncMock(return_value=None)
        self.update_user = AsyncMock(return_value=self.default_success_response)
        
        # Create response for get_user that matches expected structure
        self.user_response = MagicMock()
        self.user_response.user = self.default_success_response.user
        self.get_user = AsyncMock(return_value=self.user_response)
    
    def set_auth_error(self, method_name: str):
        """Configure a specific method to return an auth error."""
        if hasattr(self, method_name):
            # Create a proper AuthApiError exception to raise
            from gotrue.errors import AuthApiError
            error_msg = "Invalid credentials or user already registered"
            # Configure the method to raise an exception instead of returning an error response
            # AuthApiError takes message, status, and code parameters
            getattr(self, method_name).side_effect = AuthApiError(error_msg, 400, "invalid_credentials")
            
    def set_not_found_error(self, method_name: str):
        """Configure a specific method to return a not found error."""
        if hasattr(self, method_name):
            getattr(self, method_name).return_value = self.not_found_error_response
            
    def configure_user(self, user_data: Dict[str, Any]):
        """Update the test user with custom data."""
        self.test_user_data.update(user_data)
        self.test_user_id = user_data.get("id", self.test_user_id)
        
        # Update all the responses with the new user data
        self.default_success_response = MockSupabaseResponse(self.test_user_data)
        self.user_response.user = self.default_success_response.user
        
        # Reset the methods to use the new response
        self.sign_up.return_value = self.default_success_response
        self.sign_in.return_value = self.default_success_response
        self.sign_in_with_password.return_value = self.default_success_response
        self.sign_in_with_otp.return_value = self.default_success_response
        self.refresh_session.return_value = self.default_success_response
        self.update_user.return_value = self.default_success_response


@pytest_asyncio.fixture
async def mock_supabase_client():
    """
    Create a mock Supabase client for testing that responds to authentication methods.
    The client will return a consistent user ID that we can use to pre-create database
    records to satisfy foreign key constraints.
    """
    # Create enhanced auth mock
    mock_auth = SupabaseAuthMock()
    
    # Create the main Supabase client mock
    mock_client = AsyncMock()
    mock_client.auth = mock_auth
    
    # Add test user ID directly to client for convenience
    mock_client.test_user_id = mock_auth.test_user_id
    
    # Add utility methods for tests to customize behavior
    mock_client.configure_user = mock_auth.configure_user
    mock_client.set_auth_error = mock_auth.set_auth_error
    mock_client.set_not_found_error = mock_auth.set_not_found_error

    print(f"\nUsing mock Supabase client with test user ID: {mock_auth.test_user_id}")
    
    # Need to make sure our mock works with context manager protocol
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    return mock_client


class MockCrud:
    """Mock CRUD operations for when we need to bypass the database."""

    @staticmethod
    async def get_profile_by_user_id(*args, **kwargs):
        """Mock implementation of get_profile_by_user_id."""
        return None

    @staticmethod
    async def get_profile_by_email(*args, **kwargs):
        """Mock implementation of get_profile_by_email."""
        return None

    @staticmethod
    async def create_profile(*args, **kwargs):
        """Mock implementation of create_profile."""
        import uuid
        from datetime import datetime

        from auth_service.models.profile import Profile

        profile_in = kwargs.get("profile_in", None)
        if not profile_in:
            return None

        return Profile(
            user_id=(
                profile_in.user_id if hasattr(profile_in, "user_id") else uuid.uuid4()
            ),
            email=(
                profile_in.email if hasattr(profile_in, "email") else "mock@example.com"
            ),
            username=(
                profile_in.username if hasattr(profile_in, "username") else "mock_user"
            ),
            first_name=(
                profile_in.first_name if hasattr(profile_in, "first_name") else "Mock"
            ),
            last_name=(
                profile_in.last_name if hasattr(profile_in, "last_name") else "User"
            ),
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
