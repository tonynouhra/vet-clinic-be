#!/usr/bin/env python3
"""
Database initialization script for Veterinary Clinic Backend.
Creates all tables and optionally seeds with sample data.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import engine, Base, init_db, DatabaseHealthCheck
from app.core.config import get_settings
from app.models import user, pet, appointment, clinic, communication
from app.models.user import User, UserRole
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables(force_recreate: bool = False):
    """
    Create database tables if they don't exist.

    Args:
        force_recreate: If True, drop and recreate all tables (destructive!)
    """
    try:
        logger.info("Checking database tables...")

        async with engine.begin() as conn:
            if force_recreate:
                logger.warning("⚠️  FORCE RECREATE: Dropping all existing tables...")
                await conn.run_sync(Base.metadata.drop_all)
                logger.info("Dropped existing tables")

            # Create tables only if they don't exist
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables are ready (created only if missing)")

    except Exception as e:
        logger.error(f"Error with database tables: {e}")
        raise


async def check_existing_tables():
    """Check which tables already exist and show their status."""
    try:
        from app.core.database import AsyncSessionLocal

        # List of expected tables and their models
        expected_tables = {
            "users": "User records",
            # Future tables will be added here automatically
            # "pets": "Pet records",
            # "appointments": "Appointment records",
            # "clinics": "Clinic records",
            # "conversations": "Chat conversations",
        }

        existing_tables = []
        missing_tables = []

        async with AsyncSessionLocal() as session:
            for table_name, description in expected_tables.items():
                try:
                    result = await session.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = result.scalar()
                    logger.info(f"✅ {table_name}: {count} records ({description})")
                    existing_tables.append(table_name)
                except Exception:
                    logger.info(f"❌ {table_name}: Missing ({description})")
                    missing_tables.append(table_name)

        if existing_tables:
            logger.info(f"📊 Found {len(existing_tables)} existing tables")

        if missing_tables:
            logger.info(f"📝 Need to create {len(missing_tables)} missing tables")

        return len(existing_tables) > 0

    except Exception as e:
        logger.error(f"Error checking existing tables: {e}")
        return False


async def detect_new_tables():
    """
    Detect if there are new tables in models that don't exist in database.
    This helps when you add new models in the future.
    """
    try:
        logger.info("🔍 Checking for new tables in models...")

        # Import all models to register them
        from app.models import user  # Add more imports as you create new models

        # Get all table names from SQLAlchemy metadata
        model_tables = set(Base.metadata.tables.keys())
        logger.info(f"📋 Models define these tables: {', '.join(sorted(model_tables))}")

        # Check which ones exist in database
        from app.core.database import AsyncSessionLocal

        existing_tables = set()

        async with AsyncSessionLocal() as session:
            for table_name in model_tables:
                try:
                    await session.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
                    existing_tables.add(table_name)
                except Exception:
                    pass  # Table doesn't exist

        new_tables = model_tables - existing_tables

        if new_tables:
            logger.info(f"🆕 New tables to create: {', '.join(sorted(new_tables))}")
            return True
        else:
            logger.info("✅ All model tables already exist in database")
            return False

    except Exception as e:
        logger.error(f"Error detecting new tables: {e}")
        return False


async def seed_sample_data():
    """Seed database with sample data for development."""
    try:
        from app.core.database import AsyncSessionLocal

        logger.info("Seeding sample data...")

        async with AsyncSessionLocal() as session:
            # Create sample users
            sample_users = [
                User(
                    clerk_id="admin_001",
                    email="admin@vetclinic.com",
                    first_name="Admin",
                    last_name="User",
                    role=UserRole.ADMIN,
                    phone_number="+1234567890",
                    is_verified=True,
                ),
                User(
                    clerk_id="vet_001",
                    email="dr.smith@vetclinic.com",
                    first_name="Dr. Sarah",
                    last_name="Smith",
                    role=UserRole.VETERINARIAN,
                    phone_number="+1234567891",
                    department="General Practice",
                    is_verified=True,
                ),
                User(
                    clerk_id="owner_001",
                    email="john.doe@example.com",
                    first_name="John",
                    last_name="Doe",
                    role=UserRole.PET_OWNER,
                    phone_number="+1234567892",
                    is_verified=True,
                ),
                User(
                    clerk_id="receptionist_001",
                    email="receptionist@vetclinic.com",
                    first_name="Jane",
                    last_name="Wilson",
                    role=UserRole.RECEPTIONIST,
                    phone_number="+1234567893",
                    department="Front Desk",
                    is_verified=True,
                ),
            ]

            # Add users to session
            for user in sample_users:
                session.add(user)

            # Commit the transaction
            await session.commit()
            logger.info(f"Created {len(sample_users)} sample users")

    except Exception as e:
        logger.error(f"Error seeding sample data: {e}")
        raise


async def check_database_connection():
    """Check if database connection is working."""
    try:
        logger.info("Checking database connection...")

        health_check = DatabaseHealthCheck()
        is_healthy = await health_check.check_connection()

        if is_healthy:
            logger.info("✅ Database connection successful")

            # Get connection info
            conn_info = await health_check.get_connection_info()
            logger.info(f"Database: {conn_info.get('database')}")
            logger.info(f"User: {conn_info.get('user')}")
            logger.info(
                f"Server: {conn_info.get('server_addr')}:{conn_info.get('server_port')}"
            )

            return True
        else:
            logger.error("❌ Database connection failed")
            return False

    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return False


async def main():
    """Main initialization function."""
    settings = get_settings()

    logger.info("🚀 Starting database initialization...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(
        f"Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Hidden'}"
    )

    try:
        # Step 1: Check database connection
        if not await check_database_connection():
            logger.error("Cannot proceed without database connection")
            sys.exit(1)

        # Step 2: Check existing tables
        tables_exist = await check_existing_tables()

        # Step 3: Detect new tables (for future model additions)
        has_new_tables = await detect_new_tables()

        # Step 4: Create tables (only if needed)
        force_recreate = "--force" in sys.argv
        if force_recreate:
            logger.warning(
                "🔥 FORCE RECREATE mode enabled - this will delete all data!"
            )

        if not tables_exist or has_new_tables or force_recreate:
            await create_tables(force_recreate=force_recreate)
        else:
            logger.info("✅ All tables already exist and are up to date")

        # Step 4: Seed sample data (optional)
        if "--seed" in sys.argv:
            await seed_sample_data()

        logger.info("✅ Database initialization completed successfully!")

        # Show next steps
        logger.info("\n📋 Next steps:")
        logger.info("1. Start the FastAPI server: uvicorn app.main:app --reload")
        logger.info("2. Access API docs: http://localhost:8000/docs")
        logger.info("3. Test database connection: python scripts/test_db.py")

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)

    finally:
        # Close database connections
        await engine.dispose()


if __name__ == "__main__":
    # Check if --help flag is provided
    if "--help" in sys.argv or "-h" in sys.argv:
        print(
            """
Database Initialization Script

Usage:
    python scripts/init_db.py [OPTIONS]

Options:
    --seed         Seed database with sample data
    --force        Force recreate all tables (DESTRUCTIVE!)
    --help, -h     Show this help message

Examples:
    python scripts/init_db.py                # Create tables only (if missing)
    python scripts/init_db.py --seed         # Create tables and seed data
    python scripts/init_db.py --force        # Drop and recreate all tables
    python scripts/init_db.py --force --seed # Recreate tables and seed data
        """
        )
        sys.exit(0)

    # Run the main function
    asyncio.run(main())
