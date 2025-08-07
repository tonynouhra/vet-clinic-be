#!/usr/bin/env python3
"""
Simple test runner to verify the authentication flow tests.
This script sets up minimal environment variables to avoid configuration errors.
"""

import os
import sys
import subprocess

# Set minimal environment variables for testing
os.environ.update({
    'ENVIRONMENT': 'test',
    'DEBUG': 'true',
    'DATABASE_URL': 'sqlite:///test.db',
    'REDIS_URL': 'redis://localhost:6379/0',
    'CLERK_SECRET_KEY': 'sk_test_fake_key_for_testing_only',
    'CLERK_PUBLISHABLE_KEY': 'pk_test_fake_key_for_testing_only',
    'CLERK_JWT_ISSUER': 'https://test.clerk.accounts.dev',
    'CLERK_WEBHOOK_SECRET': 'test_webhook_secret',
    'JWT_SECRET_KEY': 'test_jwt_secret_key_for_testing_only',
    'SUPABASE_STORAGE_ENDPOINT': 'https://test.supabase.co',
    'SUPABASE_STORAGE_BUCKET': 'test-bucket',
    'SUPABASE_ACCESS_KEY_ID': 'test_access_key',
    'SUPABASE_SECRET_ACCESS_KEY': 'test_secret_key',
    'ALLOWED_ORIGINS': '["http://localhost:3000"]',
    'RATE_LIMIT_PER_MINUTE': '100',
    'SMTP_SERVER': 'smtp.gmail.com',
    'SMTP_PORT': '587',
    'SMTP_USERNAME': 'test@example.com',
    'SMTP_PASSWORD': 'test_password',
    'SMTP_USE_TLS': 'true',
    'LOG_LEVEL': 'INFO'
})

def run_tests():
    """Run the authentication flow tests."""
    print("Running authentication flow integration tests...")
    
    # Test commands to run
    test_commands = [
        # Test complete authentication flow
        [
            'python', '-m', 'pytest', 
            'tests/integration/test_complete_authentication_flow.py::TestCompleteAuthenticationFlow::test_complete_user_registration_flow',
            '-v', '--tb=short'
        ],
        # Test role-based access control
        [
            'python', '-m', 'pytest', 
            'tests/integration/test_complete_authentication_flow.py::TestRoleBasedAccessControl::test_admin_access_control',
            '-v', '--tb=short'
        ],
        # Test webhook synchronization
        [
            'python', '-m', 'pytest', 
            'tests/integration/test_complete_authentication_flow.py::TestWebhookDrivenUserSynchronization::test_user_created_webhook_synchronization',
            '-v', '--tb=short'
        ],
        # Test performance
        [
            'python', '-m', 'pytest', 
            'tests/integration/test_complete_authentication_flow.py::TestAuthenticationPerformance::test_authentication_endpoint_performance',
            '-v', '--tb=short'
        ]
    ]
    
    success_count = 0
    total_tests = len(test_commands)
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n{'='*60}")
        print(f"Running test {i}/{total_tests}: {' '.join(cmd[-2:])}")
        print('='*60)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ PASSED")
                success_count += 1
            else:
                print("❌ FAILED")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                
        except subprocess.TimeoutExpired:
            print("❌ TIMEOUT - Test took longer than 60 seconds")
        except Exception as e:
            print(f"❌ ERROR - {e}")
    
    print(f"\n{'='*60}")
    print(f"Test Results: {success_count}/{total_tests} tests passed")
    print('='*60)
    
    if success_count == total_tests:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(run_tests())