"""
Shared schemas package.
Contains Pydantic models and validation schemas used across microservices.
"""

from .user_schemas import UserTokenData

__all__ = ["UserTokenData"]
