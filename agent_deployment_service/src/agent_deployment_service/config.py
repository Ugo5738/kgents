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
    Configuration settings for the Agent Deployment Service.

    Loads from a .env file and environment variables.

    All environment variables are prefixed with AGENT_DEPLOYMENT_SERVICE_
    to avoid conflicts with other services.
    """

    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- GENERAL APP SETTINGS ---
    PROJECT_NAME: str = "Agent Deployment Service"
    DEBUG: bool = Field(False, alias="AGENT_DEPLOYMENT_SERVICE_DEBUG")
    ENVIRONMENT: Environment = Field(
        Environment.DEVELOPMENT, alias="AGENT_DEPLOYMENT_SERVICE_ENVIRONMENT"
    )
    LOGGING_LEVEL: str = Field("INFO", alias="AGENT_DEPLOYMENT_SERVICE_LOGGING_LEVEL")
    ROOT_PATH: str = Field("/api/v1", alias="AGENT_DEPLOYMENT_SERVICE_ROOT_PATH")

    # --- DATABASE SETTINGS ---
    DATABASE_URL: str = Field(..., alias="AGENT_DEPLOYMENT_SERVICE_DATABASE_URL")
    REDIS_URL: str = Field(
        "redis://localhost:6379/0", alias="AGENT_DEPLOYMENT_SERVICE_REDIS_URL"
    )

    # --- CORS SETTINGS ---
    CORS_ALLOW_ORIGINS: List[str] = Field(
        ["*"], alias="AGENT_DEPLOYMENT_SERVICE_CORS_ALLOW_ORIGINS"
    )

    # --- SECURITY SETTINGS ---
    # Jwt validation settings
    # These MUST match the values used by the auth_service to sign the tokens.
    M2M_JWT_SECRET_KEY: str = Field(
        ..., alias="AGENT_DEPLOYMENT_SERVICE_M2M_JWT_SECRET_KEY"
    )
    M2M_JWT_ALGORITHM: str = Field(
        "HS256", alias="AGENT_DEPLOYMENT_SERVICE_M2M_JWT_ALGORITHM"
    )
    M2M_JWT_ISSUER: str = Field(
        "kgents_auth_service", alias="AGENT_DEPLOYMENT_SERVICE_M2M_JWT_ISSUER"
    )
    M2M_JWT_AUDIENCE: str = Field(
        "kgents_microservices", alias="AGENT_DEPLOYMENT_SERVICE_M2M_JWT_AUDIENCE"
    )

    USER_JWT_SECRET_KEY: str = Field(
        ..., alias="AGENT_DEPLOYMENT_SERVICE_USER_JWT_SECRET_KEY"
    )
    USER_JWT_ALGORITHM: str = Field(
        "HS256", alias="AGENT_DEPLOYMENT_SERVICE_USER_JWT_ALGORITHM"
    )
    USER_JWT_ISSUER: str = Field(..., alias="AGENT_DEPLOYMENT_SERVICE_USER_JWT_ISSUER")
    USER_JWT_AUDIENCE: str = Field(
        ..., alias="AGENT_DEPLOYMENT_SERVICE_USER_JWT_AUDIENCE"
    )

    # --- INTERNAL SERVICE-TO-SERVICE SETTINGS ---
    AUTH_SERVICE_URL: str = Field(
        "http://auth_service:8001", alias="AGENT_DEPLOYMENT_SERVICE_AUTH_SERVICE_URL"
    )
    AGENT_MANAGEMENT_SERVICE_URL: str = Field(
        "http://agent_management_service:8002",
        alias="AGENT_DEPLOYMENT_SERVICE_AGENT_MANAGEMENT_SERVICE_URL",
    )
    DEPLOYMENT_SERVICE_CLIENT_ID: str = Field(
        "deployment_service_client_id",
        alias="AGENT_DEPLOYMENT_SERVICE_CLIENT_ID",
    )
    DEPLOYMENT_SERVICE_CLIENT_SECRET: str = Field(
        "deployment_service_client_secret",
        alias="AGENT_DEPLOYMENT_SERVICE_CLIENT_SECRET",
    )

    # --- GCP SETTINGS ---
    GCP_PROJECT_ID: str = Field(
        "your-gcp-project-id", alias="AGENT_DEPLOYMENT_SERVICE_GCP_PROJECT_ID"
    )
    GCP_REGION: str = Field("us-central1", alias="AGENT_DEPLOYMENT_SERVICE_GCP_REGION")
    GCR_HOSTNAME: str = Field(
        f"gcr.io/{GCP_PROJECT_ID}", alias="AGENT_DEPLOYMENT_SERVICE_GCR_HOSTNAME"
    )

    # --- DEPLOYMENT SETTINGS ---
    DEPLOYMENT_STRATEGY: str = Field(
        "cloud_run", alias="AGENT_DEPLOYMENT_SERVICE_DEPLOYMENT_STRATEGY"
    )

    # --- LANGFLOW SETTINGS ---
    LANGFLOW_API_URL: str = Field(
        "http://langflow_ide:7860", alias="AGENT_DEPLOYMENT_SERVICE_LANGFLOW_API_URL"
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


# Global instance of the settings
settings = Settings()
