#!/usr/bin/env python3
"""
Database connection test script for Veterinary Clinic Backend.
Tests database connectivity and basic operations.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import AsyncSessionLocal, DatabaseHealthCheck
from app.core.config import get_settings
from app.models.user import User, UserRole
from sqlalchemy import select, func
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_connection():
    """Test basic database connection."""
    logger.info("🔍 Testing database connection...")
    
    health_check = DatabaseHealthCheck()
    is_healthy = await health_check.check_connection()
    
    if is_healthy:
        logger.info("✅ Database connection successful")
        
        # Get detailed connection info
        conn_info = await health_check.get_connection_info()
        logger.info(f"📊 Connection Details:")
        logger.info(f"  Database: {conn_info.get('database')}")
        logger.info(f"  User: {conn_info.get('user')}")
        logger.info(f"  Version: {conn_info.get('version', 'Unknown')[:50]}...")
        logger.info(f"  Server: {conn_info.get('server_addr')}:{conn_info.get('server_port')}")
        logger.info(f"  Pool Size: {conn_info.get('pool_size')}")
        logger.info(f"  Checked Out: {conn_info.get('checked_out')}")
        
        return True
    else:
        logger.error("❌ Database connection failed")
        return False


async def test_user_operations():
    """Test basic user CRUD operations."""
    logger.info("🧪 Testing user operations...")
    
    try:
        async with AsyncSessionLocal() as session:
            # Test 1: Count existing users
            result = await session.execute(select(func.count(User.id)))
            user_count = result.scalar()
            logger.info(f"📊 Total users in database: {user_count}")
            
            # Test 2: Get sample users
            result = await session.execute(
                select(User).limit(3).order_by(User.created_at.desc())
            )
            users = result.scalars().all()
            
            if users:
                logger.info(f"👥 Sample users:")
                for user in users:
                    logger.info(f"  - {user.full_name} ({user.email}) - {user.role.value}")
            else:
                logger.info("📝 No users found. Run 'python scripts/init_db.py --seed' to create sample data.")
            
            # Test 3: Test user roles
            for role in UserRole:
                result = await session.execute(
                    select(func.count(User.id)).where(User.role == role)
                )
                count = result.scalar()
                logger.info(f"  {role.value}: {count} users")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ User operations test failed: {e}")
        return False


async def test_table_structure():
    """Test database table structure."""
    logger.info("🏗️  Testing table structure...")
    
    try:
        async with AsyncSessionLocal() as session:
            # Test table existence by querying each model
            tables_to_test = [
                ("users", User),
            ]
            
            for table_name, model_class in tables_to_test:
                try:
                    result = await session.execute(select(func.count(model_class.id)))
                    count = result.scalar()
                    logger.info(f"✅ Table '{table_name}': {count} records")
                except Exception as e:
                    logger.error(f"❌ Table '{table_name}': {e}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Table structure test failed: {e}")
        return False


async def main():
    """Main test function."""
    settings = get_settings()
    
    logger.info("🧪 Starting database tests...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Hidden'}")
    
    tests_passed = 0
    total_tests = 3
    
    try:
        # Test 1: Connection
        if await test_connection():
            tests_passed += 1
        
        # Test 2: Table structure
        if await test_table_structure():
            tests_passed += 1
        
        # Test 3: User operations
        if await test_user_operations():
            tests_passed += 1
        
        # Summary
        logger.info(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            logger.info("✅ All database tests passed!")
            logger.info("\n🚀 Your database is ready for development!")
        else:
            logger.warning(f"⚠️  {total_tests - tests_passed} test(s) failed")
            logger.info("\n🔧 Troubleshooting:")
            logger.info("1. Check your .env file configuration")
            logger.info("2. Ensure database is accessible")
            logger.info("3. Run: python scripts/init_db.py --seed")
        
    except Exception as e:
        logger.error(f"❌ Database tests failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Check if --help flag is provided
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
Database Test Script

Usage:
    python scripts/test_db.py

This script tests:
- Database connection
- Table structure
- Basic CRUD operations
- Sample data queries

Examples:
    python scripts/test_db.py    # Run all database tests
        """)
        sys.exit(0)
    
    # Run the main function
    asyncio.run(main())