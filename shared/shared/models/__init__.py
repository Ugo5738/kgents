"""
Shared models package.
Contains base models and mixins used across microservices.
"""

from .base import Base, UUIDMixin, TimestampMixin

__all__ = ["Base", "UUIDMixin", "TimestampMixin"]
