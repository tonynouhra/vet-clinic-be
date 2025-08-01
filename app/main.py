"""
Main FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.redis import redis_client
from app.api.v1 import api_router as v1_router
from app.api.v2 import api_router as v2_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_db()
    await redis_client.connect()
    yield
    # Shutdown
    await redis_client.disconnect()
    await close_db()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Veterinary Clinic Platform API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(v1_router, prefix=settings.API_V1_STR)
app.include_router(v2_router, prefix="/api/v2")


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"message": "Veterinary Clinic Platform API", "version": settings.VERSION}


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    from app.services.system_service import system_service
    return await system_service.get_health_status()


@app.get("/info")
async def system_info():
    """System information endpoint."""
    from app.services.system_service import system_service
    return await system_service.get_system_info()