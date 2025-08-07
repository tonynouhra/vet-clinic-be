#!/usr/bin/env python3
"""
Test runner for authentication flow tests.
"""
import os
import sys
import subprocess

# Set test environment variables before any imports
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
    'ALLOWED_ORIGINS': '["http://localhost:3000","http://localhost:3001"]',
    'RATE_LIMIT_PER_MINUTE': '1000',
    'SMTP_HOST': 'smtp.test.com',
    'SMTP_PORT': '587',
    'SMTP_USERNAME': 'test@example.com',
    'SMTP_PASSWORD': 'test_password',
    'SMTP_USE_TLS': 'true',
    'LOG_LEVEL': 'DEBUG'
})

if __name__ == "__main__":
    # Run the specific test
    test_command = [
        sys.executable, "-m", "pytest", 
        "tests/integration/test_complete_authentication_flow.py",
        "-v", "--tb=short"
    ]
    
    print("Running authentication flow test...")
    result = subprocess.run(test_command, env=os.environ)
    sys.exit(result.returncode)