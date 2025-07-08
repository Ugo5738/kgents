from enum import Enum
from typing import Any, List, Optional

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Configuration settings for the Agent Management Service.

    Loads from a .env file and environment variables.

    All environment variables are prefixed with AGENT_MANAGEMENT_SERVICE_
    to avoid conflicts with other services.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # --- GENERAL APP SETTINGS ---
    PROJECT_NAME: str = "Agent Management Service"
    DEBUG: bool = Field(False, alias="AGENT_MANAGEMENT_SERVICE_DEBUG")
    ENVIRONMENT: Environment = Field(
        Environment.DEVELOPMENT, alias="AGENT_MANAGEMENT_SERVICE_ENVIRONMENT"
    )
    LOGGING_LEVEL: str = Field("INFO", alias="AGENT_MANAGEMENT_SERVICE_LOGGING_LEVEL")
    ROOT_PATH: str = Field("/api/v1", alias="AGENT_MANAGEMENT_SERVICE_ROOT_PATH")

    # --- DATABASE SETTINGS ---
    DATABASE_URL: str = Field(..., alias="AGENT_MANAGEMENT_SERVICE_DATABASE_URL")

    # --- CORS SETTINGS ---
    CORS_ALLOW_ORIGINS: List[str] = Field(
        ["*"], alias="AGENT_MANAGEMENT_SERVICE_CORS_ALLOW_ORIGINS"
    )

    # --- SERVICE-SPECIFIC SETTINGS ---
    # Jwt validation settings
    # These MUST match the values used by the auth_service to sign the tokens.
    M2M_JWT_SECRET_KEY: str = Field(..., alias="AUTH_SERVICE_M2M_JWT_SECRET_KEY")
    M2M_JWT_ALGORITHM: str = Field("HS256", alias="AUTH_SERVICE_M2M_JWT_ALGORITHM")
    M2M_JWT_ISSUER: str = Field(
        "kgents_auth_service", alias="AUTH_SERVICE_M2M_JWT_ISSUER"
    )
    M2M_JWT_AUDIENCE: str = Field(
        "kgents_microservices", alias="AUTH_SERVICE_M2M_JWT_AUDIENCE"
    )

    # Langflow Integration
    LANGFLOW_API_URL: str = Field(
        "http://langflow_ide:7860", alias="AGENT_MANAGEMENT_SERVICE_LANGFLOW_API_URL"
    )

    @field_validator("DATABASE_URL", mode="after")
    def assemble_db_connection(cls, v: Optional[PostgresDsn], info: Any) -> PostgresDsn:
        if isinstance(v, str):
            return PostgresDsn(
                str(v).replace("postgresql+asyncpg://", "postgresql+psycopg://")
            )
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=info.data.get("POSTGRES_USER"),
            password=info.data.get("POSTGRES_PASSWORD"),
            host=info.data.get("POSTGRES_HOST"),
            port=int(info.data.get("POSTGRES_PORT", 5432)),
            path=f"{info.data.get('POSTGRES_DB') or ''}",
        )


# Global instance of the settings
settings = Settings()
