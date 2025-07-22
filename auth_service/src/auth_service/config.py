from enum import Enum
from typing import List, Optional

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Configuration settings for the Auth Service.

    Loads from a .env file and environment variables.

    All environment variables are prefixed with AUTH_SERVICE_
    to avoid conflicts with other services.
    """

    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- GENERAL APP SETTINGS ---
    PROJECT_NAME: str = "Authentication Service"
    DEBUG: bool = Field(False, alias="AUTH_SERVICE_DEBUG")
    ENVIRONMENT: Environment = Field(
        Environment.DEVELOPMENT, alias="AUTH_SERVICE_ENVIRONMENT"
    )
    LOGGING_LEVEL: str = Field("INFO", alias="AUTH_SERVICE_LOGGING_LEVEL")
    ROOT_PATH: str = Field("/api/v1", alias="AUTH_SERVICE_ROOT_PATH")

    # --- DATABASE & CACHE SETTINGS ---
    DATABASE_URL: str = Field(..., alias="AUTH_SERVICE_DATABASE_URL")
    REDIS_URL: str = Field("redis://localhost:6379/0", alias="AUTH_SERVICE_REDIS_URL")

    # --- CORS SETTINGS ---
    CORS_ALLOW_ORIGINS: List[str] = Field(
        ["*"], alias="AUTH_SERVICE_CORS_ALLOW_ORIGINS"
    )

    # --- SERVICE-SPECIFIC SETTINGS ---
    SUPABASE_URL: str = Field(..., alias="AUTH_SERVICE_SUPABASE_URL")
    SUPABASE_ANON_KEY: str = Field(..., alias="AUTH_SERVICE_SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        ..., alias="AUTH_SERVICE_SUPABASE_SERVICE_ROLE_KEY"
    )
    SUPABASE_EMAIL_CONFIRMATION_REQUIRED: bool = Field(
        True, alias="AUTH_SERVICE_SUPABASE_EMAIL_CONFIRMATION_REQUIRED"
    )

    # --- JWT & TOKEN SETTINGS ---
    M2M_JWT_SECRET_KEY: str = Field(..., alias="AUTH_SERVICE_M2M_JWT_SECRET_KEY")
    M2M_JWT_ALGORITHM: str = Field("HS256", alias="AUTH_SERVICE_M2M_JWT_ALGORITHM")
    M2M_JWT_ISSUER: str = Field(
        "kgents_auth_service", alias="AUTH_SERVICE_M2M_JWT_ISSUER"
    )
    M2M_JWT_AUDIENCE: str = Field(
        "kgents_microservices", alias="AUTH_SERVICE_M2M_JWT_AUDIENCE"
    )
    M2M_JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        30, alias="AUTH_SERVICE_M2M_JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(
        60 * 24 * 7, alias="AUTH_SERVICE_JWT_REFRESH_TOKEN_EXPIRE_MINUTES"
    )  # 7 days

    # --- OAUTH & REDIRECT SETTINGS ---
    EMAIL_CONFIRMATION_REDIRECT_URL: str = Field(
        "http://localhost:3000/auth/callback",
        alias="AUTH_SERVICE_EMAIL_CONFIRMATION_REDIRECT_URL",
    )
    PASSWORD_RESET_REDIRECT_URL: str = Field(
        "http://localhost:3000/auth/update-password",
        alias="AUTH_SERVICE_PASSWORD_RESET_REDIRECT_URL",
    )
    OAUTH_REDIRECT_URI: str = Field(
        "http://localhost:8000/auth/users/login/google/callback",
        alias="AUTH_SERVICE_OAUTH_REDIRECT_URI",
    )
    OAUTH_STATE_COOKIE_NAME: str = Field(
        "auth_state", alias="AUTH_SERVICE_OAUTH_STATE_COOKIE_NAME"
    )
    OAUTH_STATE_COOKIE_MAX_AGE_SECONDS: int = Field(
        300, alias="AUTH_SERVICE_OAUTH_STATE_COOKIE_MAX_AGE_SECONDS"
    )

    # --- BOOTSTRAP SETTINGS ---
    INITIAL_ADMIN_EMAIL: str = Field(
        "admin@admin.com", alias="AUTH_SERVICE_INITIAL_ADMIN_EMAIL"
    )
    INITIAL_ADMIN_PASSWORD: str = Field(
        "admin", alias="AUTH_SERVICE_INITIAL_ADMIN_PASSWORD"
    )

    # --- RATE LIMITING SETTINGS ---
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_REGISTER: str = "5/minute"
    RATE_LIMIT_TOKEN: str = "10/minute"
    RATE_LIMIT_PASSWORD_RESET: str = "3/minute"
    RATE_LIMIT_REQUESTS_PER_MINUTE: Optional[str] = None
    RATE_LIMIT_WINDOW_SECONDS: Optional[str] = None

    # --- OAUTH SETTINGS ---
    GOOGLE_CLIENT_ID: Optional[str] = Field(None, alias="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(None, alias="GOOGLE_CLIENT_SECRET")

    # --- AWS CREDENTIALS ---
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None

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
