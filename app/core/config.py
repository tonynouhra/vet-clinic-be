"""
Application configuration settings using Pydantic Settings.
"""
import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Project information
    PROJECT_NAME: str = "Veterinary Clinic Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Environment (this comes from the loaded .env file)
    ENVIRONMENT: str = Field(default="development", alias="ENVIRONMENT")
    DEBUG: bool = Field(default=True, alias="DEBUG")

    # Database configuration
    DATABASE_URL: str = Field(..., alias="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")

    # Redis configuration
    REDIS_URL: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    REDIS_CACHE_TTL: int = Field(default=3600, alias="REDIS_CACHE_TTL")  # 1 hour

    # Celery configuration
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND")

    # Security
    SECRET_KEY: str = Field(..., alias="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # CORS
    BACKEND_CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        alias="BACKEND_CORS_ORIGINS"
    )

    # Clerk Authentication
    CLERK_SECRET_KEY: Optional[str] = Field(default=None, alias="CLERK_SECRET_KEY")
    CLERK_PUBLISHABLE_KEY: Optional[str] = Field(default=None, alias="CLERK_PUBLISHABLE_KEY")

    # File storage
    SUPABASE_URL: Optional[str] = Field(default=None, alias="SUPABASE_URL")
    SUPABASE_KEY: Optional[str] = Field(default=None, alias="SUPABASE_KEY")
    SUPABASE_BUCKET: str = Field(default="vet-clinic-files", alias="SUPABASE_BUCKET")

    # Email configuration
    SMTP_HOST: Optional[str] = Field(default=None, alias="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, alias="SMTP_PORT")
    SMTP_USERNAME: Optional[str] = Field(default=None, alias="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = Field(default=None, alias="SMTP_PASSWORD")
    SMTP_FROM_EMAIL: Optional[str] = Field(default=None, alias="SMTP_FROM_EMAIL")

    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins as a list."""
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            return [i.strip() for i in self.BACKEND_CORS_ORIGINS.split(",") if i.strip()]
        return []

    model_config = {
        "env_file": f".env.{os.getenv(ENVIRONMENT, 'development')}",
        "case_sensitive": True,
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()