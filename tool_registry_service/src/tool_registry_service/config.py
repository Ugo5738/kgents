"""
Configuration settings for the Tool Registry Service.

This module defines Pydantic Settings classes for managing environment variables
and application configuration following the same patterns as other services.
"""

import os
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Configuration settings for the Tool Registry Service.

    All environment variables are prefixed with TOOL_REGISTRY_SERVICE_
    to avoid conflicts with other services.
    """

    # General App settings
    ENVIRONMENT: Environment = Field(
        Environment.DEVELOPMENT, alias="TOOL_REGISTRY_SERVICE_ENVIRONMENT"
    )
    LOGGING_LEVEL: str = Field("INFO", alias="TOOL_REGISTRY_SERVICE_LOGGING_LEVEL")
    ROOT_PATH: str = Field("", alias="TOOL_REGISTRY_SERVICE_ROOT_PATH")
    VERSION: str = "0.1.0"
    DEBUG: bool = Field(False, alias="TOOL_REGISTRY_SERVICE_DEBUG")
    PORT: int = Field(8000, alias="TOOL_REGISTRY_SERVICE_PORT")
    RELOAD: bool = Field(False, alias="TOOL_REGISTRY_SERVICE_RELOAD")
    SHOW_DOCS: bool = Field(True, alias="TOOL_REGISTRY_SERVICE_SHOW_DOCS")

    # Database settings
    DATABASE_URL: str = Field(..., alias="TOOL_REGISTRY_SERVICE_DATABASE_URL")
    POSTGRES_SERVER: str = Field(
        "localhost", alias="TOOL_REGISTRY_SERVICE_POSTGRES_SERVER"
    )
    POSTGRES_USER: str = Field("postgres", alias="TOOL_REGISTRY_SERVICE_POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(
        "postgres", alias="TOOL_REGISTRY_SERVICE_POSTGRES_PASSWORD"
    )
    POSTGRES_DB: str = Field("tool_registry", alias="TOOL_REGISTRY_SERVICE_POSTGRES_DB")
    POSTGRES_PORT: str = Field("5432", alias="TOOL_REGISTRY_SERVICE_POSTGRES_PORT")

    # Authentication and authorization settings
    AUTH_SERVICE_URL: str = Field(
        "http://auth_service:8000", alias="TOOL_REGISTRY_SERVICE_AUTH_SERVICE_URL"
    )
    TOKEN_URL: str = Field(
        "http://auth_service:8000/api/v1/auth/validate-token",
        alias="TOOL_REGISTRY_SERVICE_TOKEN_URL",
    )

    # Tool execution settings
    SANDBOX_EXECUTION_ENABLED: bool = Field(
        True, alias="TOOL_REGISTRY_SERVICE_SANDBOX_EXECUTION_ENABLED"
    )
    MAX_TOOL_EXECUTION_TIME_SECONDS: int = Field(
        30, alias="TOOL_REGISTRY_SERVICE_MAX_TOOL_EXECUTION_TIME_SECONDS"
    )

    # API key for accessing external services (if needed)
    API_KEY: Optional[str] = Field(None, alias="TOOL_REGISTRY_SERVICE_API_KEY")

    # CORS settings
    CORS_ALLOW_ORIGINS: List[str] = Field(
        ["*"], alias="TOOL_REGISTRY_SERVICE_CORS_ALLOW_ORIGINS"
    )
    CORS_ALLOW_METHODS: List[str] = Field(
        ["*"], alias="TOOL_REGISTRY_SERVICE_CORS_ALLOW_METHODS"
    )
    CORS_ALLOW_HEADERS: List[str] = Field(
        ["*"], alias="TOOL_REGISTRY_SERVICE_CORS_ALLOW_HEADERS"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        True, alias="TOOL_REGISTRY_SERVICE_CORS_ALLOW_CREDENTIALS"
    )

    @field_validator("DATABASE_URL")
    def validate_database_url(cls, v: str, info: Any) -> str:
        """Validate and possibly construct the database URL.

        If DATABASE_URL is not provided, attempts to construct it from individual components.
        Also ensures that the URL is properly formatted for use with the psycopg driver.

        Args:
            v: The current value of DATABASE_URL
            info: Validation information containing other field values

        Returns:
            The validated or constructed DATABASE_URL
        """
        if not v and all(
            [
                info.data.get("POSTGRES_SERVER"),
                info.data.get("POSTGRES_USER"),
                info.data.get("POSTGRES_PASSWORD"),
                info.data.get("POSTGRES_DB"),
            ]
        ):
            # Construct database URL from components
            db_host = info.data.get("POSTGRES_SERVER")
            db_port = info.data.get("POSTGRES_PORT", "5432")
            db_user = info.data.get("POSTGRES_USER")
            db_pass = info.data.get("POSTGRES_PASSWORD")
            db_name = info.data.get("POSTGRES_DB")

            return f"postgresql+psycopg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

        # Ensure the URL uses psycopg driver if it's not already specified
        if (
            v
            and v.startswith("postgresql://")
            and not v.startswith("postgresql+psycopg://")
        ):
            v = v.replace("postgresql://", "postgresql+psycopg://")

        return v

    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    def is_development(self) -> bool:
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    def is_testing(self) -> bool:
        return self.ENVIRONMENT == Environment.TESTING

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


# Create a global instance of settings
settings = Settings()
