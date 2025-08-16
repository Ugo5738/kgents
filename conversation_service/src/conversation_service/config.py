from enum import Enum
from typing import List

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Configuration settings for the Conversation Service.

    Loads from a .env file and environment variables.

    All environment variables are prefixed with CONVERSATION_SERVICE_
    to avoid conflicts with other services.
    """

    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- GENERAL APP SETTINGS ---
    PROJECT_NAME: str = "Conversation Service"
    DEBUG: bool = Field(False, alias="CONVERSATION_SERVICE_DEBUG")
    ENVIRONMENT: Environment = Field(
        Environment.DEVELOPMENT, alias="CONVERSATION_SERVICE_ENVIRONMENT"
    )
    LOGGING_LEVEL: str = Field("INFO", alias="CONVERSATION_SERVICE_LOGGING_LEVEL")
    ROOT_PATH: str = Field("/api/v1", alias="CONVERSATION_SERVICE_ROOT_PATH")

    # --- DATABASE SETTINGS ---
    DATABASE_URL: str = Field(..., alias="CONVERSATION_SERVICE_DATABASE_URL")

    # --- CORS SETTINGS ---
    CORS_ALLOW_ORIGINS: List[str] = Field(
        ["*"], alias="CONVERSATION_SERVICE_CORS_ALLOW_ORIGINS"
    )

    # --- JWT Settings for M2M and User tokens ---
    M2M_JWT_SECRET_KEY: str = Field(
        ..., alias="CONVERSATION_SERVICE_M2M_JWT_SECRET_KEY"
    )
    M2M_JWT_ALGORITHM: str = Field(
        "HS256", alias="CONVERSATION_SERVICE_M2M_JWT_ALGORITHM"
    )
    M2M_JWT_ISSUER: str = Field(
        "kgents_auth_service", alias="CONVERSATION_SERVICE_M2M_JWT_ISSUER"
    )
    M2M_JWT_AUDIENCE: str = Field(
        "kgents_microservices", alias="CONVERSATION_SERVICE_M2M_JWT_AUDIENCE"
    )

    USER_JWT_SECRET_KEY: str = Field(
        ..., alias="CONVERSATION_SERVICE_USER_JWT_SECRET_KEY"
    )
    USER_JWT_ALGORITHM: str = Field(
        "HS256", alias="CONVERSATION_SERVICE_USER_JWT_ALGORITHM"
    )
    USER_JWT_ISSUER: str = Field(..., alias="CONVERSATION_SERVICE_USER_JWT_ISSUER")
    USER_JWT_AUDIENCE: str = Field(..., alias="CONVERSATION_SERVICE_USER_JWT_AUDIENCE")

    # External runtimes
    LANGFLOW_RUNTIME_URL: str = Field(
        "http://langflow_ide:7860", alias="LANGFLOW_RUNTIME_URL"
    )

    # Auth service base URL (includes /api/v1)
    AUTH_SERVICE_URL: str = Field(
        "http://auth_service:8000/api/v1", alias="AUTH_SERVICE_URL"
    )

    # Optional: default flow id to bind conversations to on first user message
    DEFAULT_FLOW_ID: str | None = Field(
        default=None, alias="CONVERSATION_SERVICE_DEFAULT_FLOW_ID"
    )

    # Optional: agent runtime service endpoint for provisioning flows (preferred)
    AGENT_RUNTIME_SERVICE_URL: str | None = Field(
        default=None, alias="AGENT_RUNTIME_SERVICE_URL"
    )

    # Optional: M2M client credentials created by bootstrap for inter-service auth
    CLIENT_ID: str | None = Field(default=None, alias="CONVERSATION_SERVICE_CLIENT_ID")
    CLIENT_SECRET: str | None = Field(
        default=None, alias="CONVERSATION_SERVICE_CLIENT_SECRET"
    )

    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    def is_development(self) -> bool:
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    def is_testing(self) -> bool:
        return self.ENVIRONMENT == Environment.TESTING

    @field_validator("DATABASE_URL", mode="after")
    def validate_db_url(cls, v: PostgresDsn) -> str:
        """Ensures the database URL uses the psycopg driver."""
        return str(v).replace("postgresql://", "postgresql+psycopg://")


settings = Settings()
