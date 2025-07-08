"""
Auth Service Client for Tool Registry Service.

This client handles communication with the auth service for token validation,
user information retrieval, and other auth-related operations.
"""

import logging
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status

from tool_registry_service.config import settings

logger = logging.getLogger(__name__)


class AuthServiceClient:
    """Client for communicating with the Auth Service."""

    def __init__(self, base_url: str, token_url: str):
        """
        Initialize the Auth Service client.

        Args:
            base_url: Base URL of the auth service (e.g. http://auth_service:8000)
            token_url: URL for token validation endpoint
        """
        # Simply use the provided token_url directly, with no manipulation
        # This aligns with auth_service's approach, letting Docker environment handle the URL
        self.validation_url = token_url

        logger.info(
            f"Initialized auth service client with validation URL: {self.validation_url}"
        )

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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
            )

        headers = {"Authorization": f"Bearer {token}"}

        try:
            # Enhanced debugging - print detailed request information
            logger.debug(f"URL: {self.validation_url}, Headers: {headers}")

            # Try with default timeout of 5 seconds
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.debug(
                    f"Sending token validation request to {self.validation_url}"
                )

                # Add verbose HTTP logging
                response = await client.get(
                    self.validation_url,
                    headers=headers,
                    timeout=10.0,  # Increased timeout for reliability
                    follow_redirects=True,  # Handle any redirects automatically
                )

                # Log the response details for debugging
                logger.debug(
                    f"Received response: status={response.status_code}, headers={response.headers}"
                )

                if response.status_code == status.HTTP_200_OK:
                    return response.json()

                # Handle various error cases
                if response.status_code == status.HTTP_401_UNAUTHORIZED:
                    logger.warning(
                        f"Token validation failed: Unauthorized - {response.text}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid or expired token",
                    )

                # Log the error response body for diagnostics
                logger.error(
                    f"Token validation failed with status {response.status_code} - Response: {response.text}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Token validation failed: {response.text}",
                )

        except httpx.RequestError as e:
            # Provide more detailed error information
            logger.error(
                f"Error connecting to auth service: {str(e)}\nRequest details: URL={self.validation_url}"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Authentication service unavailable: {str(e)}",
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
