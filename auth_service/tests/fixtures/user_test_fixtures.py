"""
Test fixtures for user authentication tests that require proper mock user objects.
"""

import uuid
from typing import Dict, Any, Optional

from tests.fixtures.mocks import MockSupabaseUser


def create_test_user_response(user_id: Optional[str] = None) -> Any:
    """
    Create a properly structured user response object that passes Pydantic validation.
    
    Args:
        user_id: Optional user ID to use (UUID string)
        
    Returns:
        A mock user response object with a properly structured user attribute
    """
    # Create test user data that will pass validation
    test_user_data = {
        "id": user_id or str(uuid.uuid4()),
        "email": "test.user@example.com",
        "phone": "",
        "app_metadata": {"roles": ["user"]},
        "user_metadata": {},
        "aud": "authenticated",
        "role": "authenticated",
        "email_confirmed_at": "2025-01-01T00:00:00Z",
        "phone_confirmed_at": None,
        "confirmed_at": "2025-01-01T00:00:00Z",
        "last_sign_in_at": "2025-01-01T00:00:00Z",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "identities": []
    }
    
    # Create a proper user object
    user_obj = MockSupabaseUser(test_user_data)
    
    # Create a UserResponse class that has a user attribute
    UserResponse = type('UserResponse', (), {})
    user_response = UserResponse()
    user_response.user = user_obj
    
    return user_response
