"""
Authentication dependencies for the Tool Registry Service.

This module provides FastAPI dependencies for extracting user information
from authenticated requests and enforcing role-based access control.
"""

from uuid import UUID

from fastapi import Depends, Request

from tool_registry_service.clients.auth_service_client import get_auth_service_client
from tool_registry_service.security import validate_token


async def get_current_user_id(
    request: Request,
    token_data: dict = Depends(validate_token)
) -> UUID:
    """
    Extract and return the current authenticated user's ID from the request state.
    
    This dependency relies on the validate_token middleware to have already
    validated the token and stored the user data in request.state.user.
    
    Args:
        request: FastAPI Request object with user data stored in state
        token_data: Validated token data from the validate_token dependency
        
    Returns:
        UUID of the authenticated user
        
    Note:
        The validate_token dependency must be executed before this one, which
        happens automatically due to FastAPI's dependency resolution.
    """
    # The user data should be available in request.state after token validation
    if not hasattr(request.state, "user") or not request.state.user:
        # This should never happen if validate_token is working correctly
        # But we include it as a safety check
        raise RuntimeError("User data not found in request state")
    
    # Extract user ID from the validated token data
    # Check multiple possible field names for the user ID based on how auth_service returns it
    user_id = request.state.user.get("id") or request.state.user.get("sub") or request.state.user.get("user_id")
    
    if not user_id:
        raise ValueError(f"User ID not found in token data. Available fields: {list(request.state.user.keys())}")
    
    # Return as UUID
    return UUID(user_id)


async def check_admin_role(
    request: Request,
    token_data: dict = Depends(validate_token)
) -> bool:
    """
    Check if the current user has admin role.
    
    Args:
        request: FastAPI Request object with user data stored in state
        token_data: Validated token data from the validate_token dependency
        
    Returns:
        bool: True if user has admin role, False otherwise
        
    Raises:
        ValueError: If role information is not found in user data
    """
    # The user data should be available in request.state after token validation
    if not hasattr(request.state, "user") or not request.state.user:
        raise RuntimeError("User data not found in request state")
    
    # User metadata may contain roles
    user_metadata = request.state.user.get("user_metadata", {})
    roles = user_metadata.get("roles", [])
    
    # Check if 'admin' is in the roles list
    return "admin" in roles
