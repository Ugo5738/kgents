"""
Auth Service Client for validating tokens against the auth service.

This client handles communication with the auth service for token validation,
user information retrieval, and other auth-related operations.
"""
import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status

from agent_management_service.config import settings

logger = logging.getLogger(__name__)


class AuthServiceClient:
    """Client for interacting with the Auth Service API."""

    def __init__(self, base_url: str, token_url: str):
        """
        Initialize the Auth Service client.
        
        Args:
            base_url: Base URL of the auth service
            token_url: Endpoint path for token validation
        """
        self.base_url = base_url.rstrip('/')
        self.token_url = token_url.lstrip('/')
        self.validation_url = f"{self.base_url}/{self.token_url}"
        logger.debug(f"Auth Service client initialized with validation URL: {self.validation_url}")
        
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a JWT token against the Auth Service.
        
        Args:
            token: The JWT token to validate
            
        Returns:
            Dict containing user information from the validated token
            
        Raises:
            HTTPException: If token validation fails or auth service is unavailable
        """
        if not token:
            logger.warning("Empty token provided for validation")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
            )
            
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            async with httpx.AsyncClient() as client:
                logger.debug(f"Sending token validation request to {self.validation_url}")
                response = await client.get(self.validation_url, headers=headers, timeout=5.0)
                
                if response.status_code == status.HTTP_200_OK:
                    return response.json()
                    
                # Handle various error cases
                if response.status_code == status.HTTP_401_UNAUTHORIZED:
                    logger.warning("Token validation failed: Unauthorized")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid or expired token",
                    )
                    
                logger.error(f"Token validation failed with status {response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Token validation failed",
                )
                
        except httpx.RequestError as e:
            logger.error(f"Error connecting to auth service: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable",
            )


def get_auth_service_client() -> AuthServiceClient:
    """
    FastAPI dependency for obtaining an AuthServiceClient instance.
    
    Returns:
        Configured AuthServiceClient instance
    """
    return AuthServiceClient(
        base_url=settings.AUTH_SERVICE_URL,
        token_url=settings.TOKEN_URL,
    )
