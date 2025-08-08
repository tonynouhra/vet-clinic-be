"""
Integration tests for monitoring endpoints.
Tests health checks, metrics collection, and security monitoring.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.services.monitoring_service import get_monitoring_service
from app.models.user import UserRole


class TestHealthCheckEndpoints:
    """Test health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_basic_health_endpoint(self):
        """Test basic /health endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.monitoring_service.MonitoringService.check_database_health') as mock_db_check:
                from app.services.monitoring_service import HealthCheckResult
                mock_db_check.return_value = HealthCheckResult("database", "healthy", 0.1)
                
                response = await client.get("/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert "environment" in data
                assert "version" in data
                assert "database" in data
    
    @pytest.mark.asyncio
    async def test_comprehensive_health_endpoint(self):
        """Test comprehensive /monitoring/health endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.monitoring_service.MonitoringService.check_all_services_health') as mock_health_check:
                mock_health_check.return_value = {
                    "status": "healthy",
                    "services": {
                        "database": {"status": "healthy", "response_time": 0.1},
                        "redis": {"status": "healthy", "response_time": 0.05},
                        "clerk": {"status": "healthy", "response_time": 0.2}
                    },
                    "system": {"environment": "test", "version": "1.0.0"},
                    "metrics": {"authentication": {}, "performance": {}}
                }
                
                response = await client.get("/monitoring/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert "services" in data
                assert "database" in data["services"]
                assert "redis" in data["services"]
                assert "clerk" in data["services"]
    
    @pytest.mark.asyncio
    async def test_database_health_endpoint(self):
        """Test database-specific health endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.monitoring_service.MonitoringService.check_database_health') as mock_db_check:
                from app.services.monitoring_service import HealthCheckResult
                mock_db_check.return_value = HealthCheckResult(
                    service="database",
                    status="healthy",
                    response_time=0.123,
                    details={"version": "PostgreSQL 14.0", "pool": {"size": 5}}
                )
                
                response = await client.get("/monitoring/health/database")
                
                assert response.status_code == 200
                data = response.json()
                assert data["service"] == "database"
                assert data["status"] == "healthy"
                assert data["response_time"] == 0.123
                assert data["details"]["version"] == "PostgreSQL 14.0"
    
    @pytest.mark.asyncio
    async def test_redis_health_endpoint(self):
        """Test Redis-specific health endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.monitoring_service.MonitoringService.check_redis_health') as mock_redis_check:
                from app.services.monitoring_service import HealthCheckResult
                mock_redis_check.return_value = HealthCheckResult(
                    service="redis",
                    status="healthy",
                    response_time=0.05,
                    details={"version": "6.2.0", "connected_clients": 3}
                )
                
                response = await client.get("/monitoring/health/redis")
                
                assert response.status_code == 200
                data = response.json()
                assert data["service"] == "redis"
                assert data["status"] == "healthy"
                assert data["details"]["version"] == "6.2.0"
    
    @pytest.mark.asyncio
    async def test_clerk_health_endpoint(self):
        """Test Clerk-specific health endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.monitoring_service.MonitoringService.check_clerk_health') as mock_clerk_check:
                from app.services.monitoring_service import HealthCheckResult
                mock_clerk_check.return_value = HealthCheckResult(
                    service="clerk",
                    status="healthy",
                    response_time=0.2,
                    details={"jwks_keys_count": 2, "api_status": "healthy"}
                )
                
                response = await client.get("/monitoring/health/clerk")
                
                assert response.status_code == 200
                data = response.json()
                assert data["service"] == "clerk"
                assert data["status"] == "healthy"
                assert data["details"]["jwks_keys_count"] == 2
    
    @pytest.mark.asyncio
    async def test_simple_status_endpoint(self):
        """Test simple status endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.monitoring_service.MonitoringService.check_database_health') as mock_db_check:
                from app.services.monitoring_service import HealthCheckResult
                mock_db_check.return_value = HealthCheckResult("database", "healthy", 0.1)
                
                response = await client.get("/monitoring/status")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert "timestamp" in data
                assert "version" in data
    
    @pytest.mark.asyncio
    async def test_health_check_failure_handling(self):
        """Test health check failure handling."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.monitoring_service.MonitoringService.check_database_health') as mock_db_check:
                mock_db_check.side_effect = Exception("Database connection failed")
                
                response = await client.get("/monitoring/health/database")
                
                assert response.status_code == 500
                data = response.json()
                assert "detail" in data


class TestMetricsEndpoints:
    """Test metrics endpoints."""
    
    @pytest.fixture
    def admin_token_headers(self):
        """Mock admin token headers."""
        return {"Authorization": "Bearer admin_token"}
    
    @pytest.mark.asyncio
    async def test_authentication_metrics_endpoint(self, admin_token_headers):
        """Test authentication metrics endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.api.deps.verify_clerk_token') as mock_verify, \
                 patch('app.api.deps.sync_clerk_user') as mock_sync, \
                 patch('app.services.monitoring_service.MonitoringService.get_authentication_metrics') as mock_metrics:
                
                # Mock admin user authentication
                from app.models.user import User, UserRole
                mock_admin_user = Mock(spec=User)
                mock_admin_user.role = UserRole.ADMIN
                mock_admin_user.is_active = True
                mock_sync.return_value = mock_admin_user
                
                # Mock metrics
                mock_metrics.return_value = {
                    "total_attempts": 100,
                    "successful_authentications": 85,
                    "failed_authentications": 15,
                    "success_rate": 85.0,
                    "error_types": {"token_expired": 5, "invalid_signature": 3}
                }
                
                response = await client.get("/monitoring/metrics/authentication", headers=admin_token_headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["metrics"]["total_attempts"] == 100
                assert data["metrics"]["success_rate"] == 85.0
                assert "error_types" in data["metrics"]
    
    @pytest.mark.asyncio
    async def test_performance_metrics_endpoint(self, admin_token_headers):
        """Test performance metrics endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.api.deps.verify_clerk_token') as mock_verify, \
                 patch('app.api.deps.sync_clerk_user') as mock_sync, \
                 patch('app.services.monitoring_service.MonitoringService.get_performance_metrics') as mock_metrics:
                
                # Mock admin user authentication
                from app.models.user import User, UserRole
                mock_admin_user = Mock(spec=User)
                mock_admin_user.role = UserRole.ADMIN
                mock_admin_user.is_active = True
                mock_sync.return_value = mock_admin_user
                
                # Mock performance metrics
                mock_metrics.return_value = {
                    "token_validation": {"avg": 0.123, "min": 0.05, "max": 0.2, "count": 50},
                    "user_sync": {"avg": 0.456, "min": 0.1, "max": 0.8, "count": 30}
                }
                
                response = await client.get("/monitoring/metrics/performance", headers=admin_token_headers)
                
                assert response.status_code == 200
                data = response.json()
                assert "token_validation" in data["metrics"]
                assert data["metrics"]["token_validation"]["avg"] == 0.123
                assert data["metrics"]["user_sync"]["count"] == 30
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint_requires_admin(self):
        """Test that metrics endpoints require admin role."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.api.deps.verify_clerk_token') as mock_verify, \
                 patch('app.api.deps.sync_clerk_user') as mock_sync:
                
                # Mock non-admin user
                from app.models.user import User, UserRole
                mock_user = Mock(spec=User)
                mock_user.role = UserRole.PET_OWNER
                mock_user.is_active = True
                mock_sync.return_value = mock_user
                
                response = await client.get("/monitoring/metrics/authentication", headers={"Authorization": "Bearer user_token"})
                
                assert response.status_code == 403
                data = response.json()
                assert "Access denied" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint_without_auth(self):
        """Test that metrics endpoints require authentication."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/monitoring/metrics/authentication")
            
            assert response.status_code == 401


class TestSecurityEndpoints:
    """Test security monitoring endpoints."""
    
    @pytest.fixture
    def admin_token_headers(self):
        """Mock admin token headers."""
        return {"Authorization": "Bearer admin_token"}
    
    @pytest.mark.asyncio
    async def test_suspicious_patterns_endpoint(self, admin_token_headers):
        """Test suspicious patterns detection endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.api.deps.verify_clerk_token') as mock_verify, \
                 patch('app.api.deps.sync_clerk_user') as mock_sync, \
                 patch('app.services.monitoring_service.MonitoringService.detect_suspicious_patterns') as mock_detect:
                
                # Mock admin user authentication
                from app.models.user import User, UserRole
                mock_admin_user = Mock(spec=User)
                mock_admin_user.role = UserRole.ADMIN
                mock_admin_user.is_active = True
                mock_sync.return_value = mock_admin_user
                
                # Mock suspicious patterns
                mock_detect.return_value = [
                    {
                        "type": "high_failure_rate",
                        "description": "Authentication success rate is 30.0%",
                        "severity": "medium",
                        "timestamp": "2023-01-01T12:00:00Z"
                    },
                    {
                        "type": "rapid_authentication_attempts",
                        "description": "60 authentication attempts in last 5 minutes",
                        "severity": "high",
                        "timestamp": "2023-01-01T12:05:00Z"
                    }
                ]
                
                response = await client.get("/monitoring/security/suspicious-patterns", headers=admin_token_headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["count"] == 2
                assert len(data["suspicious_events"]) == 2
                assert data["suspicious_events"][0]["type"] == "high_failure_rate"
                assert data["suspicious_events"][1]["severity"] == "high"
    
    @pytest.mark.asyncio
    async def test_monitoring_alert_webhook(self, admin_token_headers):
        """Test monitoring alert webhook endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.api.deps.verify_clerk_token') as mock_verify, \
                 patch('app.api.deps.sync_clerk_user') as mock_sync, \
                 patch('app.services.monitoring_service.MonitoringService.log_security_event') as mock_log:
                
                # Mock admin user authentication
                from app.models.user import User, UserRole
                mock_admin_user = Mock(spec=User)
                mock_admin_user.role = UserRole.ADMIN
                mock_admin_user.is_active = True
                mock_sync.return_value = mock_admin_user
                
                alert_data = {
                    "message": "High CPU usage detected",
                    "severity": "high",
                    "source": "external_monitor",
                    "timestamp": "2023-01-01T12:00:00Z"
                }
                
                response = await client.post("/monitoring/webhook/alert", json=alert_data, headers=admin_token_headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "received"
                
                # Verify security event was logged
                mock_log.assert_called_once_with(
                    event_type="external_alert",
                    description="External monitoring alert: High CPU usage detected",
                    severity="high",
                    additional_data=alert_data
                )


class TestMonitoringIntegration:
    """Test monitoring integration with authentication flow."""
    
    @pytest.mark.asyncio
    async def test_authentication_metrics_collection_on_success(self):
        """Test that successful authentication is recorded in metrics."""
        monitoring_service = get_monitoring_service()
        initial_attempts = monitoring_service.metrics.total_attempts
        initial_successes = monitoring_service.metrics.successful_authentications
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.clerk_service.ClerkService.verify_jwt_token') as mock_verify, \
                 patch('app.services.user_sync_service.UserSyncService') as mock_sync_service:
                
                # Mock successful token verification
                mock_verify.return_value = {
                    "user_id": "test_user_id",
                    "clerk_id": "test_clerk_id",
                    "email": "test@example.com",
                    "role": "pet_owner"
                }
                
                # Mock user sync
                from app.models.user import User, UserRole
                mock_user = Mock(spec=User)
                mock_user.role = UserRole.PET_OWNER
                mock_user.is_active = True
                
                mock_sync_instance = Mock()
                mock_sync_instance.get_user_by_clerk_id.return_value = mock_user
                mock_sync_service.return_value = mock_sync_instance
                
                # Make authenticated request
                response = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer valid_token"})
                
                # Verify metrics were updated
                assert monitoring_service.metrics.total_attempts > initial_attempts
                assert monitoring_service.metrics.successful_authentications > initial_successes
    
    @pytest.mark.asyncio
    async def test_authentication_metrics_collection_on_failure(self):
        """Test that failed authentication is recorded in metrics."""
        monitoring_service = get_monitoring_service()
        initial_attempts = monitoring_service.metrics.total_attempts
        initial_failures = monitoring_service.metrics.failed_authentications
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.clerk_service.ClerkService.verify_jwt_token') as mock_verify:
                from app.core.exceptions import AuthenticationError
                
                # Mock failed token verification
                mock_verify.side_effect = AuthenticationError("Invalid token")
                
                # Make request with invalid token
                response = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid_token"})
                
                assert response.status_code == 401
                
                # Verify metrics were updated
                assert monitoring_service.metrics.total_attempts > initial_attempts
                assert monitoring_service.metrics.failed_authentications > initial_failures
    
    @pytest.mark.asyncio
    async def test_authorization_failure_metrics_collection(self):
        """Test that authorization failures are recorded in metrics."""
        monitoring_service = get_monitoring_service()
        initial_authz_failures = monitoring_service.metrics.authorization_failures
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.api.deps.verify_clerk_token') as mock_verify, \
                 patch('app.api.deps.sync_clerk_user') as mock_sync:
                
                # Mock successful authentication but insufficient role
                from app.models.user import User, UserRole
                mock_user = Mock(spec=User)
                mock_user.role = UserRole.PET_OWNER  # Not admin
                mock_user.is_active = True
                mock_sync.return_value = mock_user
                
                # Try to access admin endpoint
                response = await client.get("/monitoring/metrics/authentication", headers={"Authorization": "Bearer user_token"})
                
                assert response.status_code == 403
                
                # Verify authorization failure was recorded
                assert monitoring_service.metrics.authorization_failures > initial_authz_failures
    
    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self):
        """Test that performance metrics are collected during authentication."""
        monitoring_service = get_monitoring_service()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch('app.services.clerk_service.ClerkService.verify_jwt_token') as mock_verify, \
                 patch('app.services.user_sync_service.UserSyncService') as mock_sync_service:
                
                # Mock successful but slow token verification
                async def slow_verify(token):
                    await asyncio.sleep(0.1)  # Simulate slow verification
                    return {
                        "user_id": "test_user_id",
                        "clerk_id": "test_clerk_id",
                        "email": "test@example.com",
                        "role": "pet_owner"
                    }
                
                mock_verify.side_effect = slow_verify
                
                # Mock user sync
                from app.models.user import User, UserRole
                mock_user = Mock(spec=User)
                mock_user.role = UserRole.PET_OWNER
                mock_user.is_active = True
                
                mock_sync_instance = Mock()
                mock_sync_instance.get_user_by_clerk_id.return_value = mock_user
                mock_sync_service.return_value = mock_sync_instance
                
                # Make authenticated request
                response = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer valid_token"})
                
                # Verify performance metrics were collected
                performance_metrics = monitoring_service.get_performance_metrics()
                assert "token_validation" in performance_metrics
                assert performance_metrics["token_validation"]["count"] > 0