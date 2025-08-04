"""
Core configuration settings for the Veterinary Clinic Backend.
Uses Pydantic Settings for environment variable management.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application Settings
    APP_NAME: str = "Veterinary Clinic Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool
    ENVIRONMENT: str
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    API_V2_PREFIX: str = "/api/v2"
    
    # Database Settings (Supabase PostgreSQL)
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int
    DATABASE_MAX_OVERFLOW: int
    
    # Redis Settings
    REDIS_URL: str
    
    # Celery Settings
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    # Authentication Settings (Clerk)
    CLERK_API_URL: str = "https://api.clerk.com"
    CLERK_SECRET_KEY: str
    CLERK_PUBLISHABLE_KEY: str
    CLERK_WEBHOOK_SECRET: Optional[str] = None
    CLERK_JWT_ISSUER: str = "https://clerk.dev"
    CLERK_JWKS_URL: Optional[str] = None
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # File Storage Settings (Supabase Storage)
    SUPABASE_STORAGE_ENDPOINT: str
    SUPABASE_STORAGE_BUCKET: str
    SUPABASE_ACCESS_KEY_ID: str
    SUPABASE_SECRET_ACCESS_KEY: str
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int
    
    # Email Settings
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_USE_TLS: bool
    
    # Monitoring Settings
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        allowed_environments = ["development", "staging", "production"]
        if v not in allowed_environments:
            raise ValueError(f"Environment must be one of: {allowed_environments}")
        return v
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v):
        """Ensure database URL is provided."""
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v
    
    @field_validator("CLERK_SECRET_KEY")
    @classmethod
    def validate_clerk_secret_key(cls, v):
        """Validate Clerk secret key format."""
        if not v:
            raise ValueError("CLERK_SECRET_KEY is required")
        if not v.startswith("sk_"):
            raise ValueError("CLERK_SECRET_KEY must start with 'sk_'")
        return v
    
    @field_validator("CLERK_PUBLISHABLE_KEY")
    @classmethod
    def validate_clerk_publishable_key(cls, v):
        """Validate Clerk publishable key format."""
        if not v:
            raise ValueError("CLERK_PUBLISHABLE_KEY is required")
        if not v.startswith("pk_"):
            raise ValueError("CLERK_PUBLISHABLE_KEY must start with 'pk_'")
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings