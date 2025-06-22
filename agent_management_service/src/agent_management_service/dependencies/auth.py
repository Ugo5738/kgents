from uuid import UUID

from fastapi import Depends, Request

from agent_management_service.clients.auth_service_client import get_auth_service_client
from agent_management_service.security import validate_token


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
    user_id = request.state.user.get("sub") or request.state.user.get("user_id")
    
    # Return as UUID
    return UUID(user_id)
