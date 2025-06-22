from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from agent_management_service.clients.auth_service_client import AuthServiceClient, get_auth_service_client
from agent_management_service.config import settings

# Bearer token security scheme
security = HTTPBearer(
    auto_error=True,
    description="JWT token for authentication",
)


async def validate_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_client: AuthServiceClient = Depends(get_auth_service_client),
) -> dict:
    """
    Validate the JWT token against the auth_service.
    
    Args:
        request: FastAPI Request object
        credentials: HTTP Authorization credentials containing the token
        auth_client: Auth service client instance for token validation
        
    Returns:
        dict: User information from the validated token
        
    Raises:
        HTTPException: If token validation fails
    """
    token = credentials.credentials
    
    try:
        # Use the AuthServiceClient to validate the token
        user_data = await auth_client.validate_token(token)
        
        # Set the user data in the request state for use in route handlers
        request.state.user = user_data
        return user_data
        
    except HTTPException as ex:
        # Log the exception and re-raise it
        settings.logger.error(f"Token validation failed: {ex.detail}")
        raise
