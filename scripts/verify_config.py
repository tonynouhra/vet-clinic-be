#!/usr/bin/env python3
"""
Configuration verification script for Veterinary Clinic Backend.
Validates that all required environment variables are properly set.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
import logging

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class ConfigVerifier:
    """Verifies configuration settings and environment variables."""
    
    def __init__(self):
        self.project_root = project_root
        self.env_file = self.project_root / ".env"
        self.env_example_file = self.project_root / ".env.example"
        
        # Define required fields from config.py
        self.required_fields = {
            # Critical fields that must be set
            "DATABASE_URL": {
                "description": "PostgreSQL database connection string",
                "example": "postgresql+asyncpg://user:pass@host:port/db",
                "critical": True
            },
            "DEBUG": {
                "description": "Debug mode flag",
                "example": "true",
                "critical": True
            },
            "ENVIRONMENT": {
                "description": "Application environment",
                "example": "development",
                "critical": True,
                "valid_values": ["development", "staging", "production"]
            },
            "JWT_SECRET_KEY": {
                "description": "JWT token signing secret",
                "example": "your-secure-secret-key",
                "critical": True
            },
            
            # Important fields that should be set
            "DATABASE_POOL_SIZE": {
                "description": "Database connection pool size",
                "example": "10",
                "critical": False
            },
            "DATABASE_MAX_OVERFLOW": {
                "description": "Database connection pool overflow",
                "example": "20",
                "critical": False
            },
            "REDIS_URL": {
                "description": "Redis connection string",
                "example": "redis://localhost:6379/0",
                "critical": False
            },
            "CELERY_BROKER_URL": {
                "description": "Celery message broker URL",
                "example": "redis://localhost:6379/0",
                "critical": False
            },
            "CELERY_RESULT_BACKEND": {
                "description": "Celery result backend URL",
                "example": "redis://localhost:6379/0",
                "critical": False
            },
            "CLERK_SECRET_KEY": {
                "description": "Clerk authentication secret key",
                "example": "your-clerk-secret-key",
                "critical": False
            },
            "CLERK_PUBLISHABLE_KEY": {
                "description": "Clerk publishable key",
                "example": "your-clerk-publishable-key",
                "critical": False
            },
            "SUPABASE_STORAGE_ENDPOINT": {
                "description": "Supabase storage endpoint URL",
                "example": "https://your-project.storage.supabase.co/storage/v1/s3",
                "critical": False
            },
            "SUPABASE_STORAGE_BUCKET": {
                "description": "Supabase storage bucket name",
                "example": "your-bucket-name",
                "critical": False
            },
            "SUPABASE_ACCESS_KEY_ID": {
                "description": "Supabase storage access key ID",
                "example": "your-access-key-id",
                "critical": False
            },
            "SUPABASE_SECRET_ACCESS_KEY": {
                "description": "Supabase storage secret access key",
                "example": "your-secret-access-key",
                "critical": False
            },
            "ALLOWED_ORIGINS": {
                "description": "CORS allowed origins (comma-separated)",
                "example": "http://localhost:3000,http://localhost:3001",
                "critical": False
            },
            "RATE_LIMIT_PER_MINUTE": {
                "description": "API rate limit per minute",
                "example": "60",
                "critical": False
            },
            "LOG_LEVEL": {
                "description": "Application log level",
                "example": "INFO",
                "critical": False,
                "valid_values": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            }
        }
    
    def check_env_file_exists(self) -> bool:
        """Check if .env file exists."""
        if not self.env_file.exists():
            logger.error("❌ .env file not found!")
            
            if self.env_example_file.exists():
                logger.info("💡 Found .env.example file. You can copy it:")
                logger.info(f"   cp .env.example .env")
            else:
                logger.error("❌ .env.example file also not found!")
            
            return False
        
        logger.info("✅ .env file found")
        return True
    
    def load_env_variables(self) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}
        
        try:
            with open(self.env_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        env_vars[key] = value
                    else:
                        logger.warning(f"⚠️  Invalid line {line_num} in .env: {line}")
            
            logger.info(f"📊 Loaded {len(env_vars)} environment variables from .env")
            return env_vars
            
        except Exception as e:
            logger.error(f"❌ Error reading .env file: {e}")
            return {}
    
    def validate_field_value(self, key: str, value: str, field_config: Dict[str, Any]) -> List[str]:
        """Validate a specific field value."""
        issues = []
        
        # Check if value is empty
        if not value or value.strip() == "":
            issues.append(f"Value is empty")
            return issues
        
        # Check valid values if specified
        if "valid_values" in field_config:
            if value not in field_config["valid_values"]:
                valid_values = ", ".join(field_config["valid_values"])
                issues.append(f"Invalid value '{value}'. Valid values: {valid_values}")
        
        # Specific validations
        if key == "DATABASE_URL":
            if not value.startswith(("postgresql://", "postgresql+asyncpg://")):
                issues.append("Should start with 'postgresql://' or 'postgresql+asyncpg://'")
            if "localhost" in value and "development" not in os.getenv("ENVIRONMENT", ""):
                issues.append("Using localhost in non-development environment")
        
        elif key == "DEBUG":
            if value.lower() not in ["true", "false"]:
                issues.append("Should be 'true' or 'false'")
        
        elif key.endswith("_URL") and key != "DATABASE_URL":
            if not (value.startswith("http://") or value.startswith("https://") or value.startswith("redis://")):
                issues.append("Should be a valid URL")
        
        elif key.endswith("_PORT"):
            try:
                port = int(value)
                if not (1 <= port <= 65535):
                    issues.append("Port should be between 1 and 65535")
            except ValueError:
                issues.append("Should be a valid port number")
        
        elif key in ["DATABASE_POOL_SIZE", "DATABASE_MAX_OVERFLOW", "RATE_LIMIT_PER_MINUTE"]:
            try:
                num = int(value)
                if num <= 0:
                    issues.append("Should be a positive integer")
            except ValueError:
                issues.append("Should be a valid integer")
        
        return issues
    
    def verify_configuration(self) -> Tuple[bool, Dict[str, List[str]]]:
        """Verify all configuration settings."""
        logger.info("🔍 Verifying configuration settings...")
        
        # Check if .env file exists
        if not self.check_env_file_exists():
            return False, {"env_file": ["File not found"]}
        
        # Load environment variables
        env_vars = self.load_env_variables()
        if not env_vars:
            return False, {"env_file": ["Could not load environment variables"]}
        
        # Verify each required field
        issues = {}
        critical_missing = []
        
        for key, field_config in self.required_fields.items():
            field_issues = []
            
            if key not in env_vars:
                field_issues.append("Missing from .env file")
                if field_config["critical"]:
                    critical_missing.append(key)
            else:
                value = env_vars[key]
                validation_issues = self.validate_field_value(key, value, field_config)
                field_issues.extend(validation_issues)
            
            if field_issues:
                issues[key] = field_issues
        
        # Check for unknown variables (optional warning)
        unknown_vars = set(env_vars.keys()) - set(self.required_fields.keys())
        if unknown_vars:
            logger.info(f"ℹ️  Unknown environment variables (not used by config): {', '.join(sorted(unknown_vars))}")
        
        # Summary
        success = len(critical_missing) == 0 and not any(
            any("Invalid value" in issue for issue in field_issues) 
            for field_issues in issues.values()
        )
        
        return success, issues
    
    def test_configuration_loading(self) -> bool:
        """Test if configuration can be loaded successfully."""
        logger.info("🧪 Testing configuration loading...")
        
        try:
            from app.core.config import get_settings
            settings = get_settings()
            
            logger.info("✅ Configuration loaded successfully")
            logger.info(f"   Environment: {settings.ENVIRONMENT}")
            logger.info(f"   Debug Mode: {settings.DEBUG}")
            logger.info(f"   Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Hidden'}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            return False
    
    def show_configuration_report(self, issues: Dict[str, List[str]]):
        """Show detailed configuration report."""
        if not issues:
            logger.info("🎉 All configuration settings are valid!")
            return
        
        logger.error("⚠️  Configuration issues found:")
        
        # Group by critical vs non-critical
        critical_issues = {}
        warning_issues = {}
        
        for key, field_issues in issues.items():
            if key in self.required_fields and self.required_fields[key]["critical"]:
                critical_issues[key] = field_issues
            else:
                warning_issues[key] = field_issues
        
        # Show critical issues first
        if critical_issues:
            logger.error("\n🚨 CRITICAL ISSUES (must be fixed):")
            for key, field_issues in critical_issues.items():
                field_config = self.required_fields.get(key, {})
                logger.error(f"\n   {key}:")
                logger.error(f"     Description: {field_config.get('description', 'N/A')}")
                logger.error(f"     Example: {field_config.get('example', 'N/A')}")
                for issue in field_issues:
                    logger.error(f"     ❌ {issue}")
        
        # Show warnings
        if warning_issues:
            logger.warning("\n⚠️  WARNINGS (recommended to fix):")
            for key, field_issues in warning_issues.items():
                field_config = self.required_fields.get(key, {})
                logger.warning(f"\n   {key}:")
                logger.warning(f"     Description: {field_config.get('description', 'N/A')}")
                logger.warning(f"     Example: {field_config.get('example', 'N/A')}")
                for issue in field_issues:
                    logger.warning(f"     ⚠️  {issue}")
    
    def generate_env_template(self):
        """Generate a template .env file with all required variables."""
        logger.info("📝 Generating .env template...")
        
        template_content = [
            "# Veterinary Clinic Backend Configuration",
            "# Copy this file to .env and update the values",
            "",
            "# CRITICAL SETTINGS (must be configured)",
        ]
        
        # Add critical settings first
        for key, config in self.required_fields.items():
            if config["critical"]:
                template_content.extend([
                    f"# {config['description']}",
                    f"{key}={config['example']}",
                    ""
                ])
        
        template_content.append("# OPTIONAL SETTINGS (recommended)")
        
        # Add optional settings
        for key, config in self.required_fields.items():
            if not config["critical"]:
                template_content.extend([
                    f"# {config['description']}",
                    f"{key}={config['example']}",
                    ""
                ])
        
        template_file = self.project_root / ".env.template"
        with open(template_file, 'w') as f:
            f.write('\n'.join(template_content))
        
        logger.info(f"✅ Template saved to: {template_file}")
        logger.info("💡 Copy and customize: cp .env.template .env")


def main():
    """Main verification function."""
    logger.info("🔧 Configuration Verification")
    logger.info("=" * 50)
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
Configuration Verification Script

Usage:
    python scripts/verify_config.py [OPTIONS]

Options:
    --template     Generate .env template file
    --help, -h     Show this help message

This script verifies that all required environment variables
are properly configured in the .env file.
        """)
        sys.exit(0)
    
    verifier = ConfigVerifier()
    
    if "--template" in sys.argv:
        verifier.generate_env_template()
        sys.exit(0)
    
    try:
        # Verify configuration
        success, issues = verifier.verify_configuration()
        
        # Show report
        verifier.show_configuration_report(issues)
        
        if success:
            # Test configuration loading
            config_loads = verifier.test_configuration_loading()
            
            if config_loads:
                logger.info("\n🎉 Configuration verification passed!")
                logger.info("✅ All required settings are properly configured")
                logger.info("🚀 You can now start the application")
            else:
                logger.error("\n❌ Configuration verification failed!")
                logger.error("🔧 Fix the configuration loading issues above")
                sys.exit(1)
        else:
            logger.error("\n❌ Configuration verification failed!")
            logger.error("🔧 Fix the critical issues above before starting the application")
            logger.info("\n💡 Need help? Run: python scripts/verify_config.py --template")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"❌ Verification failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()