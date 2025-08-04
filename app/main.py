"""
Main FastAPI application for Veterinary Clinic Backend.
Handles application startup, middleware, and route registration.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import init_db, close_db, ensure_tables_exist
from app.core.exceptions import VetClinicException, create_http_exception
from app.app_helpers.response_helpers import error_response, generate_request_id

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"🚀 Starting Veterinary Clinic Backend")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")

    try:
        # Verify configuration on startup
        logger.info("🔍 Verifying configuration...")
        try:
            from scripts.verify_config import ConfigVerifier
            verifier = ConfigVerifier()
            success, issues = verifier.verify_configuration()
            
            if not success:
                logger.error("❌ Configuration verification failed!")
                for key, field_issues in issues.items():
                    if key in verifier.required_fields and verifier.required_fields[key]["critical"]:
                        logger.error(f"   {key}: {', '.join(field_issues)}")
                logger.error("🔧 Run 'python scripts/verify_config.py' for detailed information")
                raise RuntimeError("Configuration verification failed")
            else:
                logger.info("✅ Configuration verified successfully")
        except ImportError:
            logger.warning("⚠️  Configuration verifier not available, skipping verification")
        except Exception as e:
            if settings.ENVIRONMENT == "development":
                logger.warning(f"⚠️  Configuration verification failed: {e}")
                logger.warning("🔧 Run 'python scripts/verify_config.py' to fix configuration issues")
            else:
                # In production, configuration issues should be fatal
                raise
        # Initialize database (development only)
        if settings.ENVIRONMENT == "development":
            logger.info("🔧 Development mode: Checking database schema...")

            # Use smart schema detection
            try:
                from scripts.schema_manager import SchemaManager
                schema_manager = SchemaManager()
                
                # Check for schema changes (new tables or columns)
                new_tables, new_columns = await schema_manager.detect_schema_changes()
                
                if new_tables or new_columns:
                    if new_tables:
                        logger.info(f"🆕 New tables detected: {', '.join(sorted(new_tables))}")
                    if new_columns:
                        for table, columns in new_columns.items():
                            logger.info(f"🔧 New columns in {table}: {', '.join(sorted(columns))}")
                    
                    logger.info("⚡ Auto-updating schema in development mode...")
                    success = await schema_manager.update_schema()
                    
                    if success:
                        logger.info("✅ Database schema updated successfully")
                    else:
                        logger.warning("⚠️  Some schema updates failed")
                else:
                    logger.info("✅ Database schema is up to date")
                    
            except ImportError:
                # Fallback to basic table creation if schema_manager not available
                logger.info("📝 Using basic table creation...")
                tables_exist = await ensure_tables_exist()
                if not tables_exist:
                    logger.warning("⚠️  Database tables not found. Auto-creating...")
                    await init_db()
                else:
                    logger.info("✅ Database tables already exist")
        else:
            logger.info(
                f"🏭 {settings.ENVIRONMENT.title()} mode: Skipping auto table creation"
            )
            logger.info(
                "💡 Ensure database migrations are applied: alembic upgrade head"
            )

        logger.info("✅ Application startup completed")

    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("🛑 Shutting down Veterinary Clinic Backend")
    try:
        await close_db()
        logger.info("✅ Application shutdown completed")
    except Exception as e:
        logger.error(f"❌ Application shutdown error: {e}")


# Create FastAPI application
app = FastAPI(
    title="Veterinary Clinic Backend",
    description="Comprehensive REST API for veterinary clinic management",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(VetClinicException)
async def vet_clinic_exception_handler(request: Request, exc: VetClinicException):
    """Handle custom VetClinicException."""
    request_id = generate_request_id()
    logger.error(f"VetClinicException [{request_id}]: {exc.message}")

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
            request_id=request_id,
        ),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    request_id = generate_request_id()
    logger.error(f"Unhandled exception [{request_id}]: {exc}")

    return JSONResponse(
        status_code=500,
        content=error_response(
            message="Internal server error" if not settings.DEBUG else str(exc),
            error_code="INTERNAL_ERROR",
            request_id=request_id,
        ),
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from app.core.database import DatabaseHealthCheck

    db_health = DatabaseHealthCheck()
    db_status = await db_health.check_connection()

    return {
        "status": "healthy" if db_status else "unhealthy",
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION,
        "database": "connected" if db_status else "disconnected",
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Veterinary Clinic Backend API",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else "disabled",
        "health": "/health",
    }


# Add API routes
from app.api import auth
from app.api.v1 import api_router as v1_router

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(v1_router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
