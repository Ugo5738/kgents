import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from agent_management_service.config import settings

# Bearer token security scheme
security = HTTPBearer(
    auto_error=True,
    description="JWT token for authentication",
)


async def validate_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validate the JWT token against the auth_service.
    
    Args:
        request: FastAPI Request object
        credentials: HTTP Authorization credentials containing the token
        
    Returns:
        dict: User information from the validated token
        
    Raises:
        HTTPException: If token validation fails
    """
    token = credentials.credentials
    
    # Call auth_service to validate the token
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.AUTH_SERVICE_URL}{settings.TOKEN_URL}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0, # 5 second timeout
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
                
            user_data = response.json()
            # Set the user data in the request state for use in route handlers
            request.state.user = user_data
            return user_data
            
        except httpx.RequestError:
            settings.logger.error("Failed to connect to auth_service for token validation")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable",
            )
