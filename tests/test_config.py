"""
Test configuration for authentication flow tests.
Provides mock settings that bypass validation for testing.
"""

from unittest.mock import Mock
from app.models.user import UserRole


class TestSettings:
    """Mock settings for testing."""
    
    # Application Settings
    APP_NAME = "Test Veterinary Clinic Backend"
    DEBUG = True
    ENVIRONMENT = "development"
    
    # Database Settings
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    
    # Redis Settings
    REDIS_URL = "redis://localhost:6379/1"
    REDIS_CACHE_TTL = 900
    REDIS_USER_CACHE_TTL = 900
    REDIS_JWT_CACHE_TTL = 3600
    
    # Authentication Settings (Clerk)
    CLERK_API_URL = "https://api.clerk.com"
    CLERK_SECRET_KEY = "sk_test_mock_secret_key_for_testing"
    CLERK_PUBLISHABLE_KEY = "pk_test_mock_publishable_key_for_testing"
    CLERK_WEBHOOK_SECRET = "test_webhook_secret_key"
    CLERK_JWT_ISSUER = "https://clerk.dev"
    JWT_SECRET_KEY = "test_jwt_secret_key_for_testing"
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # Clerk Error Handling Configuration
    CLERK_CIRCUIT_BREAKER_THRESHOLD = 5
    CLERK_CIRCUIT_BREAKER_TIMEOUT = 60
    CLERK_MAX_RETRIES = 3
    CLERK_RETRY_BASE_DELAY = 1.0
    CLERK_REQUEST_TIMEOUT = 30
    
    # File Storage Settings
    SUPABASE_STORAGE_ENDPOINT = "https://test.storage.supabase.co"
    SUPABASE_STORAGE_BUCKET = "test-bucket"
    SUPABASE_ACCESS_KEY_ID = "test_access_key"
    SUPABASE_SECRET_ACCESS_KEY = "test_secret_key"
    
    # CORS Settings
    ALLOWED_ORIGINS = ["http://localhost:3000"]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = 60
    
    # Email Settings
    SMTP_HOST = "smtp.test.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "test@example.com"
    SMTP_PASSWORD = "test_password"
    SMTP_USE_TLS = True
    
    # Monitoring Settings
    SENTRY_DSN = None
    LOG_LEVEL = "DEBUG"


def get_test_settings():
    """Get test settings instance."""
    return TestSettings()


# Role mapping for tests
TEST_CLERK_ROLE_MAPPING = {
    "admin": UserRole.ADMIN,
    "veterinarian": UserRole.VETERINARIAN,
    "receptionist": UserRole.RECEPTIONIST,
    "clinic_manager": UserRole.CLINIC_MANAGER,
    "pet_owner": UserRole.PET_OWNER,
}