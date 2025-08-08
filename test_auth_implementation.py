#!/usr/bin/env python3
"""
Test script to verify authentication implementation is working correctly.
This script tests the authentication endpoints and functionality.
"""

import asyncio
import httpx
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
API_V1_PREFIX = "/api/v1"

async def test_authentication_endpoints():
    """Test authentication endpoints to verify implementation."""
    
    print("🧪 Testing Authentication Implementation")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Health check
        print("\n1. Testing health check endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Environment: {data.get('environment')}")
                print(f"   Database: {data.get('database')}")
                print("   ✅ Health check passed")
            else:
                print("   ❌ Health check failed")
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
        
        # Test 2: Root endpoint
        print("\n2. Testing root endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   API Version: {data.get('version')}")
                print(f"   Environment: {data.get('environment')}")
                print("   ✅ Root endpoint passed")
            else:
                print("   ❌ Root endpoint failed")
        except Exception as e:
            print(f"   ❌ Root endpoint error: {e}")
        
        # Test 3: Development users list
        print("\n3. Testing development users endpoint...")
        try:
            response = await client.get(f"{BASE_URL}{API_V1_PREFIX}/auth/dev-users")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Available test users: {len(data.get('users', []))}")
                for user in data.get('users', [])[:2]:  # Show first 2 users
                    print(f"     - {user.get('email')} ({user.get('role')})")
                print("   ✅ Dev users endpoint passed")
            else:
                print("   ❌ Dev users endpoint failed")
        except Exception as e:
            print(f"   ❌ Dev users endpoint error: {e}")
        
        # Test 4: Development login
        print("\n4. Testing development login...")
        try:
            login_data = {
                "email": "admin@vetclinic.com",
                "password": "dev-password"
            }
            response = await client.post(
                f"{BASE_URL}{API_V1_PREFIX}/auth/dev-login",
                json=login_data
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                token = data.get('token')
                user = data.get('user', {})
                print(f"   User: {user.get('email')} ({user.get('role')})")
                print(f"   Token length: {len(token) if token else 0}")
                print("   ✅ Dev login passed")
                
                # Test 5: Token validation
                print("\n5. Testing token validation...")
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(
                    f"{BASE_URL}{API_V1_PREFIX}/auth/test-token-dev",
                    headers=headers
                )
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Authentication method: {data.get('authentication_method')}")
                    print("   ✅ Token validation passed")
                else:
                    print("   ❌ Token validation failed")
                    
            else:
                print("   ❌ Dev login failed")
        except Exception as e:
            print(f"   ❌ Dev login error: {e}")
        
        # Test 6: User info endpoint (without auth)
        print("\n6. Testing user info endpoint (no auth)...")
        try:
            response = await client.get(f"{BASE_URL}{API_V1_PREFIX}/auth/user-info")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Authenticated: {data.get('authenticated')}")
                print(f"   API Name: {data.get('api_info', {}).get('name', 'N/A')}")
                print("   ✅ User info (no auth) passed")
            else:
                print("   ❌ User info (no auth) failed")
        except Exception as e:
            print(f"   ❌ User info (no auth) error: {e}")
        
        # Test 7: Authentication endpoints structure
        print("\n7. Testing authentication endpoints structure...")
        endpoints_to_test = [
            "/auth/dev-users",
            "/auth/dev-login", 
            "/auth/test-token-dev",
            "/auth/user-info"
        ]
        
        for endpoint in endpoints_to_test:
            try:
                # Use OPTIONS to check if endpoint exists
                response = await client.options(f"{BASE_URL}{API_V1_PREFIX}{endpoint}")
                if response.status_code in [200, 405]:  # 405 is OK, means endpoint exists
                    print(f"   ✅ {endpoint} - endpoint exists")
                else:
                    print(f"   ❌ {endpoint} - endpoint missing (status: {response.status_code})")
            except Exception as e:
                print(f"   ❌ {endpoint} - error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Authentication implementation test completed!")
    print("\nNext steps:")
    print("1. Start the server: python -m uvicorn app.main:app --reload")
    print("2. Test with Postman using the dev-login endpoint")
    print("3. Use the returned token in Authorization header: Bearer <token>")

if __name__ == "__main__":
    asyncio.run(test_authentication_endpoints())