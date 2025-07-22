"""
Shared models package.
Contains base models and mixins used across microservices.
"""

from .base import Base, TimestampMixin, UUIDMixin

__all__ = ["Base", "UUIDMixin", "TimestampMixin"]
