#!/usr/bin/env python3
"""
Simple test script to verify authentication test setup.
"""
import os
import sys

# Set test environment variables
os.environ.update({
    'DEBUG': 'true',
    'ENVIRONMENT': 'development',
    'DATABASE_URL': 'sqlite+aiosqlite:///:memory:',
    'DATABASE_POOL_SIZE': '5',
    'DATABASE_MAX_OVERFLOW': '10',
    'REDIS_URL': 'redis://localhost:6379/1',
    'CELERY_BROKER_URL': 'redis://localhost:6379/1',
    'CELERY_RESULT_BACKEND': 'redis://localhost:6379/1',
    'CLERK_SECRET_KEY': 'sk_test_mock_secret_key_for_testing_12345678901234567890',
    'CLERK_PUBLISHABLE_KEY': 'pk_test_mock_publishable_key_for_testing_12345678901234567890',
    'CLERK_WEBHOOK_SECRET': 'test_webhook_secret_key_for_testing',
    'CLERK_JWT_ISSUER': 'https://clerk.dev',
    'JWT_SECRET_KEY': 'test_jwt_secret_key_for_testing_change_in_production_12345678901234567890',
    'JWT_ALGORITHM': 'HS256',
    'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
    'SUPABASE_STORAGE_ENDPOINT': 'https://test.storage.supabase.co',
    'SUPABASE_STORAGE_BUCKET': 'test-bucket',
    'SUPABASE_ACCESS_KEY_ID': 'test_access_key_id_for_testing',
    'SUPABASE_SECRET_ACCESS_KEY': 'test_secret_access_key_for_testing',
    'ALLOWED_ORIGINS': '["http://localhost:3000", "http://localhost:3001"]',
    'RATE_LIMIT_PER_MINUTE': '1000',
    'SMTP_HOST': 'smtp.test.com',
    'SMTP_PORT': '587',
    'SMTP_USERNAME': 'test@example.com',
    'SMTP_PASSWORD': 'test_password',
    'SMTP_USE_TLS': 'true',
    'LOG_LEVEL': 'DEBUG'
})

try:
    # Test imports
    from tests.test_config import get_test_settings
    from app.models.user import UserRole
    from app.schemas.clerk_schemas import ClerkUser, ClerkEmailAddress
    
    print("✓ All imports successful")
    
    # Test configuration
    settings = get_test_settings()
    print(f"✓ Test settings loaded: {settings.ENVIRONMENT}")
    print(f"✓ Clerk secret key: {settings.CLERK_SECRET_KEY[:10]}...")
    
    # Test basic functionality
    user_role = UserRole.PET_OWNER
    print(f"✓ UserRole enum works: {user_role}")
    
    print("\n🎉 Authentication test setup is working correctly!")
    
except Exception as e:
    print(f"❌ Error in test setup: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)