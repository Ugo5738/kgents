"""
Authentication utilities for testing.

This module provides helper functions for mocking authentication
and authorization in tests.
"""

import uuid
from typing import Dict, Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from tool_registry_service.dependencies import auth as auth_deps


# Default test user IDs
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


def get_mock_user_id(user_id: uuid.UUID = DEFAULT_USER_ID):
    """
    Create a function that returns a fixed user ID for testing.
    
    Args:
        user_id: User ID to return
        
    Returns:
        Function that returns the user ID
    """
    return lambda: user_id


def get_mock_admin_check(is_admin: bool = True):
    """
    Create a function that returns a fixed admin status for testing.
    
    Args:
        is_admin: Whether the user is an admin
        
    Returns:
        Function that returns the admin status
    """
    return lambda: is_admin


def setup_auth_overrides(app, user_id: uuid.UUID = DEFAULT_USER_ID, is_admin: bool = False):
    """
    Set up authentication and authorization overrides for testing.
    
    Args:
        app: FastAPI application
        user_id: User ID to use for authentication
        is_admin: Whether the user should have admin privileges
    """
    app.dependency_overrides[auth_deps.get_current_user_id] = get_mock_user_id(user_id)
    app.dependency_overrides[auth_deps.check_admin_role] = get_mock_admin_check(is_admin)


def reset_auth_overrides(app):
    """
    Reset authentication and authorization overrides.
    
    Args:
        app: FastAPI application
    """
    if auth_deps.get_current_user_id in app.dependency_overrides:
        del app.dependency_overrides[auth_deps.get_current_user_id]
    
    if auth_deps.check_admin_role in app.dependency_overrides:
        del app.dependency_overrides[auth_deps.check_admin_role]
