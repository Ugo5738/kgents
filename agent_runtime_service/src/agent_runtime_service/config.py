from enum import Enum
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Configuration settings for the Agent Runtime Service.

    Loads from a .env file and environment variables.

    All environment variables are prefixed with AGENT_RUNTIME_SERVICE_
    to avoid conflicts with other services.
    """

    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- GENERAL APP SETTINGS ---
    PROJECT_NAME: str = "Agent Runtime Service"
    DEBUG: bool = Field(False, alias="AGENT_RUNTIME_SERVICE_DEBUG")
    ENVIRONMENT: Environment = Field(
        Environment.DEVELOPMENT, alias="AGENT_RUNTIME_SERVICE_ENVIRONMENT"
    )
    LOGGING_LEVEL: str = Field("INFO", alias="AGENT_RUNTIME_SERVICE_LOGGING_LEVEL")
    ROOT_PATH: str = Field("/api/v1", alias="AGENT_RUNTIME_SERVICE_ROOT_PATH")

    # --- CORS SETTINGS ---
    CORS_ALLOW_ORIGINS: List[str] = Field(
        ["*"], alias="AGENT_RUNTIME_SERVICE_CORS_ALLOW_ORIGINS"
    )

    # --- JWT Settings for M2M and User tokens ---
    M2M_JWT_SECRET_KEY: str = Field(
        ..., alias="AGENT_RUNTIME_SERVICE_M2M_JWT_SECRET_KEY"
    )
    M2M_JWT_ALGORITHM: str = Field(
        "HS256", alias="AGENT_RUNTIME_SERVICE_M2M_JWT_ALGORITHM"
    )
    M2M_JWT_ISSUER: str = Field(
        "kgents_auth_service", alias="AGENT_RUNTIME_SERVICE_M2M_JWT_ISSUER"
    )
    M2M_JWT_AUDIENCE: str = Field(
        "kgents_microservices", alias="AGENT_RUNTIME_SERVICE_M2M_JWT_AUDIENCE"
    )

    USER_JWT_SECRET_KEY: str = Field(
        ..., alias="AGENT_RUNTIME_SERVICE_USER_JWT_SECRET_KEY"
    )
    USER_JWT_ALGORITHM: str = Field(
        "HS256", alias="AGENT_RUNTIME_SERVICE_USER_JWT_ALGORITHM"
    )
    USER_JWT_ISSUER: str = Field(
        ..., alias="AGENT_RUNTIME_SERVICE_USER_JWT_ISSUER"
    )
    USER_JWT_AUDIENCE: str = Field(
        ..., alias="AGENT_RUNTIME_SERVICE_USER_JWT_AUDIENCE"
    )

    # --- Provider settings ---
    LANGFLOW_API_URL: str = Field(
        "http://langflow_ide:7860", alias="AGENT_RUNTIME_SERVICE_LANGFLOW_API_URL"
    )

    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    def is_development(self) -> bool:
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    def is_testing(self) -> bool:
        return self.ENVIRONMENT == Environment.TESTING


settings = Settings()
