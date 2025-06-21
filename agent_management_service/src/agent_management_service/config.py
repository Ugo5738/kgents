import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    STAGING = "staging"
    TESTING = "testing"


class Settings(BaseSettings):
    """Service settings loaded from environment variables with sensible defaults."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # API configuration
    ROOT_PATH: str = Field("/api/v1", alias="AGENT_MANAGEMENT_SERVICE_ROOT_PATH")
    PROJECT_NAME: str = "Agent Management Service"
    ENVIRONMENT: Environment = Field(
        Environment.DEVELOPMENT, alias="AGENT_MANAGEMENT_SERVICE_ENVIRONMENT"
    )
    DEBUG: bool = Field(False, alias="AGENT_MANAGEMENT_SERVICE_DEBUG")
    LOGGING_LEVEL: str = Field("INFO", alias="AGENT_MANAGEMENT_SERVICE_LOGGING_LEVEL")

    # Security
    AUTH_SERVICE_URL: str = Field(
        "http://auth_service:8000", alias="AGENT_MANAGEMENT_SERVICE_AUTH_SERVICE_URL"
    )
    TOKEN_URL: str = Field(
        "/api/v1/auth/validate-token", alias="AGENT_MANAGEMENT_SERVICE_TOKEN_URL"
    )

    # CORS Settings
    CORS_ORIGINS: List[str] = Field(
        ["*"], alias="AGENT_MANAGEMENT_SERVICE_CORS_ORIGINS"
    )

    # Database
    POSTGRES_HOST: str = Field(..., alias="AGENT_MANAGEMENT_SERVICE_POSTGRES_HOST")
    POSTGRES_USER: str = Field(..., alias="AGENT_MANAGEMENT_SERVICE_POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(
        ..., alias="AGENT_MANAGEMENT_SERVICE_POSTGRES_PASSWORD"
    )
    POSTGRES_DB: str = Field(..., alias="AGENT_MANAGEMENT_SERVICE_POSTGRES_DB")
    POSTGRES_PORT: str = Field("5432", alias="AGENT_MANAGEMENT_SERVICE_POSTGRES_PORT")
    DATABASE_URL: Optional[PostgresDsn] = Field(
        None, alias="AGENT_MANAGEMENT_SERVICE_DATABASE_URL"
    )

    @field_validator("DATABASE_URL", mode="after")
    def assemble_db_connection(cls, v: Optional[str], info: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=info.data.get("POSTGRES_USER"),
            password=info.data.get("POSTGRES_PASSWORD"),
            host=info.data.get("POSTGRES_HOST"),
            port=int(info.data.get("POSTGRES_PORT", 5432)),
            path=f"/{info.data.get('POSTGRES_DB') or ''}",
        )

    # Langflow Integration
    LANGFLOW_API_URL: str = Field(
        "http://langflow_ide:7860", alias="AGENT_MANAGEMENT_SERVICE_LANGFLOW_API_URL"
    )

    @property
    def logger(self) -> logging.Logger:
        """Get the logger instance configured for this service.

        Returns:
            logging.Logger: Configured logger instance.
        """
        logger = logging.getLogger("agent_management_service")

        # Configure handlers if they don't exist
        if not logger.handlers:
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            # Set level from settings
            level = getattr(logging, self.LOGGING_LEVEL.upper(), logging.INFO)
            logger.setLevel(level)

        return logger


# Create global settings instance
settings = Settings()
