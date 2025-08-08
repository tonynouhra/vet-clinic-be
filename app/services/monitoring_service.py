"""
Monitoring and observability service for the Veterinary Clinic Backend.
Provides authentication metrics collection, health checks, and system monitoring.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, engine
from app.core.redis import redis_client
from app.services.clerk_service import get_clerk_service
from app.core.logging_config import get_auth_logger

logger = logging.getLogger(__name__)
auth_logger = get_auth_logger()
settings = get_settings()


@dataclass
class AuthenticationMetrics:
    """Authentication metrics data structure."""
    
    total_attempts: int = 0
    successful_authentications: int = 0
    failed_authentications: int = 0
    token_validation_errors: int = 0
    authorization_failures: int = 0
    suspicious_activities: int = 0
    
    # Performance metrics
    avg_token_validation_time: float = 0.0
    avg_user_sync_time: float = 0.0
    
    # Time-based metrics (last hour)
    recent_attempts: deque = field(default_factory=lambda: deque(maxlen=3600))
    recent_successes: deque = field(default_factory=lambda: deque(maxlen=3600))
    recent_failures: deque = field(default_factory=lambda: deque(maxlen=3600))
    
    # Error breakdown
    error_types: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    def success_rate(self) -> float:
        """Calculate authentication success rate."""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_authentications / self.total_attempts) * 100
    
    def recent_success_rate(self) -> float:
        """Calculate recent authentication success rate (last hour)."""
        if not self.recent_attempts:
            return 0.0
        return (len(self.recent_successes) / len(self.recent_attempts)) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_attempts": self.total_attempts,
            "successful_authentications": self.successful_authentications,
            "failed_authentications": self.failed_authentications,
            "token_validation_errors": self.token_validation_errors,
            "authorization_failures": self.authorization_failures,
            "suspicious_activities": self.suspicious_activities,
            "success_rate": round(self.success_rate(), 2),
            "recent_success_rate": round(self.recent_success_rate(), 2),
            "avg_token_validation_time": round(self.avg_token_validation_time, 3),
            "avg_user_sync_time": round(self.avg_user_sync_time, 3),
            "recent_attempts_count": len(self.recent_attempts),
            "error_types": dict(self.error_types)
        }


@dataclass
class HealthCheckResult:
    """Health check result data structure."""
    
    service: str
    status: str  # "healthy", "unhealthy", "degraded"
    response_time: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health check result to dictionary."""
        return {
            "service": self.service,
            "status": self.status,
            "response_time": round(self.response_time, 3),
            "details": self.details,
            "error": self.error,
            "timestamp": self.timestamp.isoformat() + "Z"
        }


class MonitoringService:
    """Service for monitoring and observability features."""
    
    def __init__(self):
        self.metrics = AuthenticationMetrics()
        self._performance_data = defaultdict(list)
        self._health_check_cache = {}
        self._cache_ttl = 30  # Cache health checks for 30 seconds
        
    # Authentication Metrics Collection
    
    def record_authentication_attempt(self, success: bool, error_type: Optional[str] = None):
        """Record an authentication attempt."""
        current_time = time.time()
        
        self.metrics.total_attempts += 1
        self.metrics.recent_attempts.append(current_time)
        
        if success:
            self.metrics.successful_authentications += 1
            self.metrics.recent_successes.append(current_time)
        else:
            self.metrics.failed_authentications += 1
            self.metrics.recent_failures.append(current_time)
            
            if error_type:
                self.metrics.error_types[error_type] += 1
    
    def record_token_validation_error(self, error_type: str):
        """Record a token validation error."""
        self.metrics.token_validation_errors += 1
        self.metrics.error_types[f"token_{error_type}"] += 1
    
    def record_authorization_failure(self, reason: str):
        """Record an authorization failure."""
        self.metrics.authorization_failures += 1
        self.metrics.error_types[f"authz_{reason}"] += 1
    
    def record_suspicious_activity(self, activity_type: str):
        """Record suspicious activity."""
        self.metrics.suspicious_activities += 1
        self.metrics.error_types[f"suspicious_{activity_type}"] += 1
    
    def record_performance_metric(self, operation: str, duration: float):
        """Record performance metrics for operations."""
        self._performance_data[operation].append(duration)
        
        # Keep only last 100 measurements
        if len(self._performance_data[operation]) > 100:
            self._performance_data[operation] = self._performance_data[operation][-100:]
        
        # Update averages
        if operation == "token_validation":
            self.metrics.avg_token_validation_time = sum(self._performance_data[operation]) / len(self._performance_data[operation])
        elif operation == "user_sync":
            self.metrics.avg_user_sync_time = sum(self._performance_data[operation]) / len(self._performance_data[operation])
    
    def get_authentication_metrics(self) -> Dict[str, Any]:
        """Get current authentication metrics."""
        return self.metrics.to_dict()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        performance_stats = {}
        
        for operation, durations in self._performance_data.items():
            if durations:
                performance_stats[operation] = {
                    "avg": round(sum(durations) / len(durations), 3),
                    "min": round(min(durations), 3),
                    "max": round(max(durations), 3),
                    "count": len(durations)
                }
        
        return performance_stats
    
    # Health Check Methods
    
    async def check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and performance."""
        start_time = time.time()
        
        try:
            async with AsyncSessionLocal() as session:
                # Basic connectivity check
                await session.execute(text("SELECT 1"))
                
                # Get database info
                result = await session.execute(
                    text("""
                        SELECT 
                            version() as version,
                            current_database() as database,
                            current_user as user,
                            pg_database_size(current_database()) as size
                    """)
                )
                row = result.fetchone()
                
                # Check connection pool status
                pool_status = {
                    "size": engine.pool.size(),
                    "checked_out": engine.pool.checkedout(),
                    "overflow": engine.pool.overflow()
                }
                
                # Add invalid count if available (not all pool types support this)
                try:
                    pool_status["invalid"] = engine.pool.invalid()
                except AttributeError:
                    pool_status["invalid"] = "not_available"
                
                response_time = time.time() - start_time
                
                return HealthCheckResult(
                    service="database",
                    status="healthy",
                    response_time=response_time,
                    details={
                        "version": row.version if row else "unknown",
                        "database": row.database if row else "unknown",
                        "user": row.user if row else "unknown",
                        "size_bytes": int(row.size) if row and row.size else 0,
                        "pool": pool_status
                    }
                )
                
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Database health check failed: {e}")
            
            return HealthCheckResult(
                service="database",
                status="unhealthy",
                response_time=response_time,
                error=str(e)
            )
    
    async def check_redis_health(self) -> HealthCheckResult:
        """Check Redis connectivity and performance."""
        start_time = time.time()
        
        try:
            # Test basic connectivity
            await redis_client.ping()
            
            # Get Redis info
            info = await redis_client.info()
            memory_info = await redis_client.info("memory")
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                service="redis",
                status="healthy",
                response_time=response_time,
                details={
                    "version": info.get("redis_version", "unknown"),
                    "mode": info.get("redis_mode", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": memory_info.get("used_memory", 0),
                    "used_memory_human": memory_info.get("used_memory_human", "0B"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                }
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Redis health check failed: {e}")
            
            return HealthCheckResult(
                service="redis",
                status="unhealthy",
                response_time=response_time,
                error=str(e)
            )
    
    async def check_clerk_health(self) -> HealthCheckResult:
        """Check Clerk service connectivity and performance."""
        start_time = time.time()
        
        try:
            clerk_service = get_clerk_service()
            
            # Test JWKS endpoint
            timeout = httpx.Timeout(5.0)  # 5 second timeout for health checks
            async with httpx.AsyncClient(timeout=timeout) as client:
                jwks_response = await client.get(clerk_service.jwks_url)
                jwks_response.raise_for_status()
                jwks_data = jwks_response.json()
                
                # Test Clerk API endpoint (if we have a test user ID)
                api_status = "unknown"
                api_response_time = 0.0
                
                try:
                    api_start = time.time()
                    api_response = await client.get(
                        f"{clerk_service.base_url}/users",
                        headers={
                            "Authorization": f"Bearer {clerk_service.secret_key}",
                            "Content-Type": "application/json",
                        },
                        params={"limit": 1}  # Just get one user to test API
                    )
                    api_response_time = time.time() - api_start
                    
                    if api_response.status_code == 200:
                        api_status = "healthy"
                    else:
                        api_status = "degraded"
                        
                except Exception as api_e:
                    logger.warning(f"Clerk API test failed: {api_e}")
                    api_status = "unhealthy"
                
                response_time = time.time() - start_time
                
                return HealthCheckResult(
                    service="clerk",
                    status="healthy" if api_status in ["healthy", "degraded"] else "degraded",
                    response_time=response_time,
                    details={
                        "jwks_keys_count": len(jwks_data.get("keys", [])),
                        "jwks_response_time": round(response_time, 3),
                        "api_status": api_status,
                        "api_response_time": round(api_response_time, 3),
                        "base_url": clerk_service.base_url,
                        "jwks_url": clerk_service.jwks_url
                    }
                )
                
        except httpx.TimeoutException:
            response_time = time.time() - start_time
            return HealthCheckResult(
                service="clerk",
                status="unhealthy",
                response_time=response_time,
                error="Request timeout"
            )
        except httpx.HTTPStatusError as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                service="clerk",
                status="unhealthy",
                response_time=response_time,
                error=f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Clerk health check failed: {e}")
            
            return HealthCheckResult(
                service="clerk",
                status="unhealthy",
                response_time=response_time,
                error=str(e)
            )
    
    async def check_all_services_health(self) -> Dict[str, Any]:
        """Check health of all services."""
        # Check cache first
        cache_key = "health_check_all"
        cached_result = self._health_check_cache.get(cache_key)
        
        if cached_result and time.time() - cached_result["timestamp"] < self._cache_ttl:
            return cached_result["data"]
        
        # Run all health checks concurrently
        health_checks = await asyncio.gather(
            self.check_database_health(),
            self.check_redis_health(),
            self.check_clerk_health(),
            return_exceptions=True
        )
        
        results = {}
        overall_status = "healthy"
        
        for check in health_checks:
            if isinstance(check, Exception):
                logger.error(f"Health check failed with exception: {check}")
                continue
                
            results[check.service] = check.to_dict()
            
            # Determine overall status
            if check.status == "unhealthy":
                overall_status = "unhealthy"
            elif check.status == "degraded" and overall_status == "healthy":
                overall_status = "degraded"
        
        # Add system information
        system_info = {
            "environment": settings.ENVIRONMENT,
            "version": settings.APP_VERSION,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime": self._get_uptime()
        }
        
        result = {
            "status": overall_status,
            "services": results,
            "system": system_info,
            "metrics": {
                "authentication": self.get_authentication_metrics(),
                "performance": self.get_performance_metrics()
            }
        }
        
        # Cache the result
        self._health_check_cache[cache_key] = {
            "data": result,
            "timestamp": time.time()
        }
        
        return result
    
    def _get_uptime(self) -> str:
        """Get application uptime (placeholder implementation)."""
        # In a real implementation, you would track startup time
        return "unknown"
    
    # Security Event Detection
    
    async def detect_suspicious_patterns(self) -> List[Dict[str, Any]]:
        """Detect suspicious authentication patterns."""
        suspicious_events = []
        
        # Check for high failure rate
        if self.metrics.recent_success_rate() < 50 and len(self.metrics.recent_attempts) > 10:
            suspicious_events.append({
                "type": "high_failure_rate",
                "description": f"Authentication success rate is {self.metrics.recent_success_rate():.1f}%",
                "severity": "medium",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        
        # Check for rapid authentication attempts
        if len(self.metrics.recent_attempts) > 100:  # More than 100 attempts in last hour
            recent_window = time.time() - 300  # Last 5 minutes
            recent_count = sum(1 for t in self.metrics.recent_attempts if t > recent_window)
            
            if recent_count > 50:  # More than 50 attempts in 5 minutes
                suspicious_events.append({
                    "type": "rapid_authentication_attempts",
                    "description": f"{recent_count} authentication attempts in last 5 minutes",
                    "severity": "high",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
        
        # Check for unusual error patterns
        for error_type, count in self.metrics.error_types.items():
            if count > 20:  # More than 20 of the same error type
                suspicious_events.append({
                    "type": "unusual_error_pattern",
                    "description": f"High frequency of {error_type} errors: {count}",
                    "severity": "medium",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
        
        return suspicious_events
    
    async def log_security_event(
        self,
        event_type: str,
        description: str,
        severity: str = "medium",
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log a security event."""
        auth_logger.log_suspicious_activity(
            activity_type=event_type,
            description=description,
            additional_data={
                "severity": severity,
                **(additional_data or {})
            }
        )
        
        # Record in metrics
        self.record_suspicious_activity(event_type)


# Global monitoring service instance
monitoring_service = MonitoringService()


def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    return monitoring_service