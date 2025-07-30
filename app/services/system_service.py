"""
System-related services for health checks and monitoring.
"""
from typing import Dict, Any
from datetime import datetime
import asyncio

from app.core.config import settings
from app.core.database import engine
from app.core.redis import redis_client


class SystemService:
    """Service for system health checks and monitoring."""
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status of all system components.
        
        Returns:
            Dict: Health status information
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "components": {}
        }
        
        # Check database health
        try:
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
            health_status["components"]["database"] = {
                "status": "healthy",
                "message": "Database connection successful"
            }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}"
            }
        
        # Check Redis health
        try:
            await redis_client.set("health_check", "ok", ttl=60)
            result = await redis_client.get("health_check")
            if result == "ok":
                health_status["components"]["redis"] = {
                    "status": "healthy",
                    "message": "Redis connection successful"
                }
            else:
                raise Exception("Redis health check failed")
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["components"]["redis"] = {
                "status": "unhealthy",
                "message": f"Redis connection failed: {str(e)}"
            }
        
        return health_status
    
    async def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information and configuration.
        
        Returns:
            Dict: System information
        """
        return {
            "project_name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "api_version": settings.API_V1_STR,
            "features": {
                "authentication": bool(settings.CLERK_SECRET_KEY),
                "file_storage": bool(settings.SUPABASE_URL),
                "email": bool(settings.SMTP_HOST),
                "redis_cache": True,
                "background_tasks": True
            }
        }
    
    async def check_external_services(self) -> Dict[str, Any]:
        """
        Check status of external services.
        
        Returns:
            Dict: External services status
        """
        services_status = {}
        
        # Check Supabase (if configured)
        if settings.SUPABASE_URL:
            try:
                # This would be a real health check to Supabase
                # For now, just mark as configured
                services_status["supabase"] = {
                    "status": "configured",
                    "message": "Supabase URL configured"
                }
            except Exception as e:
                services_status["supabase"] = {
                    "status": "error",
                    "message": f"Supabase check failed: {str(e)}"
                }
        else:
            services_status["supabase"] = {
                "status": "not_configured",
                "message": "Supabase URL not configured"
            }
        
        # Check Clerk (if configured)
        if settings.CLERK_SECRET_KEY:
            services_status["clerk"] = {
                "status": "configured",
                "message": "Clerk authentication configured"
            }
        else:
            services_status["clerk"] = {
                "status": "not_configured",
                "message": "Clerk authentication not configured"
            }
        
        # Check SMTP (if configured)
        if settings.SMTP_HOST:
            services_status["smtp"] = {
                "status": "configured",
                "message": "SMTP server configured"
            }
        else:
            services_status["smtp"] = {
                "status": "not_configured",
                "message": "SMTP server not configured"
            }
        
        return services_status


# Global system service instance
system_service = SystemService()