#!/usr/bin/env python3
"""
Smart schema management for development.
Detects and handles new tables and new columns in existing tables.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import logging

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import engine, Base, AsyncSessionLocal
from app.core.config import get_settings
from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateTable

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchemaManager:
    """Smart schema management for development environments."""
    
    def __init__(self):
        self.settings = get_settings()
        
    async def get_database_tables(self) -> Dict[str, Set[str]]:
        """Get current database tables and their columns."""
        try:
            async with AsyncSessionLocal() as session:
                # Get all table names
                result = await session.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                
                db_tables = {}
                table_names = [row[0] for row in result.fetchall()]
                
                # Get columns for each table
                for table_name in table_names:
                    result = await session.execute(text(f"""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns 
                        WHERE table_name = '{table_name}' 
                        AND table_schema = 'public'
                        ORDER BY ordinal_position
                    """))
                    
                    columns = set()
                    for row in result.fetchall():
                        column_name, data_type, is_nullable, default = row
                        columns.add(column_name)
                    
                    db_tables[table_name] = columns
                
                return db_tables
                
        except Exception as e:
            logger.error(f"Error getting database schema: {e}")
            return {}
    
    def get_model_tables(self) -> Dict[str, Set[str]]:
        """Get tables and columns defined in SQLAlchemy models."""
        try:
            # Import all models to register them
            from app.models import user  # Add more as you create them
            
            model_tables = {}
            
            for table_name, table in Base.metadata.tables.items():
                columns = set()
                for column in table.columns:
                    columns.add(column.name)
                model_tables[table_name] = columns
            
            return model_tables
            
        except Exception as e:
            logger.error(f"Error getting model schema: {e}")
            return {}
    
    async def detect_schema_changes(self) -> Tuple[Set[str], Dict[str, Set[str]]]:
        """
        Detect schema changes between models and database.
        
        Returns:
            Tuple of (new_tables, new_columns_by_table)
        """
        logger.info("🔍 Analyzing schema changes...")
        
        db_tables = await self.get_database_tables()
        model_tables = self.get_model_tables()
        
        # Find new tables
        db_table_names = set(db_tables.keys())
        model_table_names = set(model_tables.keys())
        new_tables = model_table_names - db_table_names
        
        # Find new columns in existing tables
        new_columns = {}
        for table_name in model_table_names:
            if table_name in db_tables:  # Table exists
                db_columns = db_tables[table_name]
                model_columns = model_tables[table_name]
                missing_columns = model_columns - db_columns
                
                if missing_columns:
                    new_columns[table_name] = missing_columns
        
        return new_tables, new_columns
    
    async def create_missing_tables(self, new_tables: Set[str]) -> bool:
        """Create only the missing tables."""
        if not new_tables:
            return True
            
        try:
            logger.info(f"🆕 Creating new tables: {', '.join(sorted(new_tables))}")
            
            async with engine.begin() as conn:
                # Create only missing tables
                tables_to_create = []
                for table_name in new_tables:
                    if table_name in Base.metadata.tables:
                        tables_to_create.append(Base.metadata.tables[table_name])
                
                for table in tables_to_create:
                    await conn.execute(CreateTable(table))
                    logger.info(f"✅ Created table: {table.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            return False
    
    async def add_missing_columns(self, new_columns: Dict[str, Set[str]]) -> bool:
        """Add missing columns to existing tables."""
        if not new_columns:
            return True
        
        try:
            async with AsyncSessionLocal() as session:
                for table_name, columns in new_columns.items():
                    logger.info(f"🔧 Adding columns to {table_name}: {', '.join(sorted(columns))}")
                    
                    # Get the SQLAlchemy table definition
                    if table_name not in Base.metadata.tables:
                        logger.warning(f"Table {table_name} not found in models")
                        continue
                    
                    table = Base.metadata.tables[table_name]
                    
                    for column_name in columns:
                        if column_name not in table.columns:
                            logger.warning(f"Column {column_name} not found in model")
                            continue
                        
                        column = table.columns[column_name]
                        
                        # Build ALTER TABLE statement
                        column_type = column.type.compile(dialect=engine.dialect)
                        nullable = "NULL" if column.nullable else "NOT NULL"
                        
                        # Handle default values
                        default_clause = ""
                        if column.default is not None:
                            if hasattr(column.default, 'arg'):
                                if callable(column.default.arg):
                                    # Skip callable defaults for now
                                    default_clause = ""
                                else:
                                    default_clause = f" DEFAULT '{column.default.arg}'"
                            else:
                                default_clause = f" DEFAULT '{column.default}'"
                        
                        alter_sql = f"""
                            ALTER TABLE {table_name} 
                            ADD COLUMN {column_name} {column_type} {nullable}{default_clause}
                        """
                        
                        try:
                            await session.execute(text(alter_sql))
                            logger.info(f"✅ Added column: {table_name}.{column_name}")
                        except Exception as e:
                            logger.error(f"❌ Failed to add column {table_name}.{column_name}: {e}")
                
                await session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding columns: {e}")
            return False
    
    async def update_schema(self, force_recreate: bool = False) -> bool:
        """
        Update database schema to match models.
        
        Args:
            force_recreate: If True, drop and recreate all tables
            
        Returns:
            bool: True if successful
        """
        try:
            if force_recreate:
                logger.warning("🔥 FORCE RECREATE: Dropping all tables...")
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
                    await conn.run_sync(Base.metadata.create_all)
                logger.info("✅ All tables recreated")
                return True
            
            # Detect changes
            new_tables, new_columns = await self.detect_schema_changes()
            
            if not new_tables and not new_columns:
                logger.info("✅ Database schema is up to date")
                return True
            
            # Apply changes
            success = True
            
            if new_tables:
                success &= await self.create_missing_tables(new_tables)
            
            if new_columns:
                success &= await self.add_missing_columns(new_columns)
            
            if success:
                logger.info("✅ Schema update completed successfully")
            else:
                logger.error("❌ Some schema updates failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating schema: {e}")
            return False
    
    async def show_schema_status(self):
        """Show current schema status."""
        try:
            logger.info("📊 Current Schema Status:")
            
            db_tables = await self.get_database_tables()
            model_tables = self.get_model_tables()
            
            logger.info(f"📋 Models define: {len(model_tables)} tables")
            logger.info(f"🗄️  Database has: {len(db_tables)} tables")
            
            # Show table details
            for table_name in sorted(model_tables.keys()):
                model_columns = model_tables[table_name]
                
                if table_name in db_tables:
                    db_columns = db_tables[table_name]
                    missing_columns = model_columns - db_columns
                    
                    if missing_columns:
                        logger.info(f"⚠️  {table_name}: Missing columns: {', '.join(sorted(missing_columns))}")
                    else:
                        logger.info(f"✅ {table_name}: Up to date ({len(model_columns)} columns)")
                else:
                    logger.info(f"❌ {table_name}: Table missing ({len(model_columns)} columns)")
            
        except Exception as e:
            logger.error(f"Error showing schema status: {e}")


async def main():
    """Main function."""
    settings = get_settings()
    
    if settings.ENVIRONMENT != "development":
        logger.error("❌ Schema manager should only be used in development!")
        logger.error("For production, use: alembic upgrade head")
        sys.exit(1)
    
    manager = SchemaManager()
    
    # Parse command line arguments
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
Smart Schema Manager for Development

Usage:
    python scripts/schema_manager.py [OPTIONS]

Options:
    --status       Show current schema status
    --update       Update schema (add missing tables/columns)
    --force        Force recreate all tables (DESTRUCTIVE!)
    --help, -h     Show this help message

Examples:
    python scripts/schema_manager.py --status    # Check schema status
    python scripts/schema_manager.py --update    # Apply schema changes
    python scripts/schema_manager.py --force     # Recreate everything
        """)
        sys.exit(0)
    
    try:
        if "--status" in sys.argv:
            await manager.show_schema_status()
        elif "--force" in sys.argv:
            logger.warning("🔥 Force recreate mode - this will delete all data!")
            await manager.update_schema(force_recreate=True)
        else:
            # Default: update schema
            await manager.update_schema()
        
    except Exception as e:
        logger.error(f"❌ Schema management failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())