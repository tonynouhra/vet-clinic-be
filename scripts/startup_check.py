#!/usr/bin/env python3
"""
Comprehensive startup verification script.
Runs all necessary checks before starting the application.
"""

import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


async def run_startup_checks():
    """Run all startup checks."""
    logger.info("🚀 Running Startup Verification Checks")
    logger.info("=" * 50)
    
    checks_passed = 0
    total_checks = 4
    
    # Check 1: Configuration Verification
    logger.info("\n1️⃣  Configuration Verification")
    logger.info("-" * 30)
    try:
        from scripts.verify_config import ConfigVerifier
        verifier = ConfigVerifier()
        success, issues = verifier.verify_configuration()
        
        if success:
            logger.info("✅ Configuration verification passed")
            checks_passed += 1
        else:
            logger.error("❌ Configuration verification failed")
            verifier.show_configuration_report(issues)
            logger.error("🔧 Fix configuration issues before starting")
    except Exception as e:
        logger.error(f"❌ Configuration check failed: {e}")
    
    # Check 2: Database Connection
    logger.info("\n2️⃣  Database Connection Test")
    logger.info("-" * 30)
    try:
        from app.core.database import DatabaseHealthCheck
        health_check = DatabaseHealthCheck()
        is_healthy = await health_check.check_connection()
        
        if is_healthy:
            logger.info("✅ Database connection successful")
            
            # Get connection details
            conn_info = await health_check.get_connection_info()
            logger.info(f"   Database: {conn_info.get('database')}")
            logger.info(f"   Server: {conn_info.get('server_addr')}:{conn_info.get('server_port')}")
            checks_passed += 1
        else:
            logger.error("❌ Database connection failed")
            logger.error("🔧 Check your DATABASE_URL in .env file")
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
    
    # Check 3: Schema Verification
    logger.info("\n3️⃣  Database Schema Check")
    logger.info("-" * 30)
    try:
        from scripts.schema_manager import SchemaManager
        schema_manager = SchemaManager()
        
        # Check for schema changes
        new_tables, new_columns = await schema_manager.detect_schema_changes()
        
        if not new_tables and not new_columns:
            logger.info("✅ Database schema is up to date")
            checks_passed += 1
        else:
            if new_tables:
                logger.info(f"🆕 New tables detected: {', '.join(sorted(new_tables))}")
            if new_columns:
                for table, columns in new_columns.items():
                    logger.info(f"🔧 New columns in {table}: {', '.join(sorted(columns))}")
            
            logger.info("⚡ Schema will be updated automatically on startup")
            checks_passed += 1
    except Exception as e:
        logger.error(f"❌ Schema check failed: {e}")
    
    # Check 4: Application Import Test
    logger.info("\n4️⃣  Application Import Test")
    logger.info("-" * 30)
    try:
        from app.main import app
        from app.core.config import get_settings
        
        settings = get_settings()
        logger.info("✅ Application imports successful")
        logger.info(f"   Environment: {settings.ENVIRONMENT}")
        logger.info(f"   Debug Mode: {settings.DEBUG}")
        logger.info(f"   API Version: {settings.APP_VERSION}")
        checks_passed += 1
    except Exception as e:
        logger.error(f"❌ Application import failed: {e}")
    
    # Summary
    logger.info("\n📊 Startup Check Summary")
    logger.info("=" * 30)
    logger.info(f"Checks Passed: {checks_passed}/{total_checks}")
    
    if checks_passed == total_checks:
        logger.info("🎉 All startup checks passed!")
        logger.info("✅ Application is ready to start")
        logger.info("\n🚀 You can now start the application:")
        logger.info("   • PyCharm: Run 'FastAPI Development Server'")
        logger.info("   • Command line: uvicorn app.main:app --reload")
        logger.info("   • Development script: ./scripts/dev.sh")
        return True
    else:
        failed_checks = total_checks - checks_passed
        logger.error(f"❌ {failed_checks} check(s) failed!")
        logger.error("🔧 Fix the issues above before starting the application")
        
        logger.info("\n💡 Quick fixes:")
        logger.info("   • Configuration: python scripts/verify_config.py")
        logger.info("   • Database: python scripts/test_db.py")
        logger.info("   • Schema: python scripts/schema_manager.py --status")
        logger.info("   • Dependencies: pip install -r requirements.txt")
        return False


def main():
    """Main function."""
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
Startup Verification Script

Usage:
    python scripts/startup_check.py

This script runs comprehensive checks to ensure the application
is ready to start:
- Configuration verification
- Database connection test
- Schema validation
- Application import test

Run this before starting the application to catch issues early.
        """)
        sys.exit(0)
    
    try:
        success = asyncio.run(run_startup_checks())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⏹️  Startup check cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Startup check failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()