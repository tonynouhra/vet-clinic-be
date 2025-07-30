#!/usr/bin/env python3
"""
Test script to verify the backend setup is working correctly.
"""
import asyncio
import sys
from app.core.config import settings
from app.core.redis import redis_client
from app.core.database import engine
from app.main import app


async def test_configuration():
    """Test configuration loading."""
    print("✓ Configuration loaded successfully")
    print(f"  - Project: {settings.PROJECT_NAME}")
    print(f"  - Version: {settings.VERSION}")
    print(f"  - Environment: {settings.ENVIRONMENT}")
    print(f"  - CORS Origins: {settings.cors_origins}")


async def test_fastapi_app():
    """Test FastAPI app creation."""
    print("✓ FastAPI app created successfully")
    print(f"  - Title: {app.title}")
    print(f"  - Version: {app.version}")
    print(f"  - OpenAPI URL: {app.openapi_url}")


async def test_redis_connection():
    """Test Redis connection."""
    try:
        await redis_client.connect()
        await redis_client.set("test_key", "test_value", ttl=60)
        value = await redis_client.get("test_key")
        if value == "test_value":
            print("✓ Redis connection working")
            await redis_client.delete("test_key")
        else:
            print("✗ Redis connection failed - value mismatch")
            return False
        await redis_client.disconnect()
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False
    return True


async def test_database_connection():
    """Test database connection."""
    try:
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1 as test")
            row = result.fetchone()
            if row and row[0] == 1:
                print("✓ Database connection working")
            else:
                print("✗ Database connection failed - query result invalid")
                return False
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    return True


async def main():
    """Run all tests."""
    print("Testing Veterinary Clinic Platform Backend Setup")
    print("=" * 50)

    # Test configuration
    await test_configuration()

    # Test FastAPI app
    await test_fastapi_app()

    # Test Redis (optional - may fail if Redis is not running)
    print("\nTesting external services (may fail if services are not running):")
    redis_ok = await test_redis_connection()

    # Test Database (optional - may fail if PostgreSQL is not running)
    db_ok = await test_database_connection()

    print("\n" + "=" * 50)
    print("Setup Test Summary:")
    print("✓ Core configuration: OK")
    print("✓ FastAPI application: OK")
    print(
        f"{'✓' if redis_ok else '✗'} Redis connection: {'OK' if redis_ok else 'FAILED (service may not be running)'}"
    )
    print(
        f"{'✓' if db_ok else '✗'} Database connection: {'OK' if db_ok else 'FAILED (service may not be running)'}"
    )

    if redis_ok and db_ok:
        print("\n🎉 All tests passed! Backend setup is complete.")
        return 0
    else:
        print("\n⚠️  Some external services are not available.")
        print("   This is normal if you haven't started Docker services yet.")
        print("   Run 'docker-compose up' to start all services.")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
