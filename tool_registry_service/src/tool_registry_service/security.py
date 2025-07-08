"""
Security utilities for the Tool Registry Service.

This module handles token validation, authentication with auth_service,
and security-related dependencies.
"""

import logging
from typing import Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from tool_registry_service.clients.auth_service_client import get_auth_service_client

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme for FastAPI
security = HTTPBearer(auto_error=False)


async def validate_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict:
    """
    Validate JWT token with auth_service and store user data in request.state.
    
    Args:
        request: FastAPI request object
        credentials: HTTP Authorization header with Bearer token
        
    Returns:
        Dict: User data from the validated token
        
    Raises:
        HTTPException: If token is missing, invalid, or auth_service is unavailable
    """
    # Check if token is provided
    if not credentials:
        logger.warning("Missing authentication token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    auth_client = get_auth_service_client()
    
    try:
        # Validate token with auth_service
        user_data = await auth_client.validate_token(token)
        
        # Store user data in request.state for use in dependencies
        request.state.user = user_data
        
        return user_data
    
    except HTTPException:
        # Re-raise HTTPExceptions from the auth_client
        raise
    
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
