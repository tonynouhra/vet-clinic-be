"""
Monitoring and health check API endpoints.
Provides comprehensive system health information and authentication metrics.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional
import logging

from app.services.monitoring_service import get_monitoring_service, MonitoringService
from app.api.deps import require_admin_role, get_optional_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health", response_model=Dict[str, Any])
async def comprehensive_health_check():
    """
    Comprehensive health check endpoint for all services.
    
    Returns detailed health information for:
    - Database connectivity
    - Redis cache
    - Clerk authentication service
    - System metrics
    """
    monitoring_service = get_monitoring_service()
    
    try:
        health_data = await monitoring_service.check_all_services_health()
        
        # Return appropriate HTTP status based on overall health
        if health_data["status"] == "unhealthy":
            # Still return 200 but with unhealthy status for monitoring tools
            # Some monitoring systems expect 200 with status field
            pass
        
        return health_data
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )


@router.get("/health/database", response_model=Dict[str, Any])
async def database_health_check():
    """Database-specific health check."""
    monitoring_service = get_monitoring_service()
    
    try:
        result = await monitoring_service.check_database_health()
        return result.to_dict()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database health check failed"
        )


@router.get("/health/redis", response_model=Dict[str, Any])
async def redis_health_check():
    """Redis-specific health check."""
    monitoring_service = get_monitoring_service()
    
    try:
        result = await monitoring_service.check_redis_health()
        return result.to_dict()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Redis health check failed"
        )


@router.get("/health/clerk", response_model=Dict[str, Any])
async def clerk_health_check():
    """Clerk authentication service health check."""
    monitoring_service = get_monitoring_service()
    
    try:
        result = await monitoring_service.check_clerk_health()
        return result.to_dict()
    except Exception as e:
        logger.error(f"Clerk health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk health check failed"
        )


@router.get("/metrics/authentication", response_model=Dict[str, Any])
async def authentication_metrics(
    current_user: User = Depends(require_admin_role())
):
    """
    Get authentication metrics.
    Requires admin role for security.
    """
    monitoring_service = get_monitoring_service()
    
    try:
        metrics = monitoring_service.get_authentication_metrics()
        return {
            "metrics": metrics,
            "timestamp": monitoring_service.metrics.recent_attempts[-1] if monitoring_service.metrics.recent_attempts else None
        }
    except Exception as e:
        logger.error(f"Failed to get authentication metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve authentication metrics"
        )


@router.get("/metrics/performance", response_model=Dict[str, Any])
async def performance_metrics(
    current_user: User = Depends(require_admin_role())
):
    """
    Get performance metrics.
    Requires admin role for security.
    """
    monitoring_service = get_monitoring_service()
    
    try:
        metrics = monitoring_service.get_performance_metrics()
        return {
            "metrics": metrics,
            "description": "Performance metrics for various operations"
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )


@router.get("/security/suspicious-patterns", response_model=Dict[str, Any])
async def suspicious_patterns(
    current_user: User = Depends(require_admin_role())
):
    """
    Get detected suspicious authentication patterns.
    Requires admin role for security.
    """
    monitoring_service = get_monitoring_service()
    
    try:
        patterns = await monitoring_service.detect_suspicious_patterns()
        return {
            "suspicious_events": patterns,
            "count": len(patterns),
            "description": "Detected suspicious authentication patterns"
        }
    except Exception as e:
        logger.error(f"Failed to detect suspicious patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze suspicious patterns"
        )


@router.get("/status", response_model=Dict[str, Any])
async def simple_status_check():
    """
    Simple status check endpoint for basic monitoring.
    Returns minimal information without authentication requirements.
    """
    monitoring_service = get_monitoring_service()
    
    try:
        # Quick health check without detailed information
        db_result = await monitoring_service.check_database_health()
        
        return {
            "status": "healthy" if db_result.status == "healthy" else "unhealthy",
            "timestamp": db_result.timestamp.isoformat() + "Z",
            "version": "1.0.0"  # Could be from settings
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "status": "unhealthy",
            "error": "Status check failed"
        }


# Webhook endpoint for external monitoring systems
@router.post("/webhook/alert", response_model=Dict[str, Any])
async def receive_monitoring_alert(
    alert_data: Dict[str, Any],
    current_user: User = Depends(require_admin_role())
):
    """
    Receive alerts from external monitoring systems.
    Requires admin role for security.
    """
    monitoring_service = get_monitoring_service()
    
    try:
        # Log the alert
        await monitoring_service.log_security_event(
            event_type="external_alert",
            description=f"External monitoring alert: {alert_data.get('message', 'Unknown')}",
            severity=alert_data.get('severity', 'medium'),
            additional_data=alert_data
        )
        
        return {
            "status": "received",
            "message": "Alert logged successfully"
        }
    except Exception as e:
        logger.error(f"Failed to process monitoring alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process alert"
        )