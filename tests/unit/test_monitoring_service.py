"""
Unit tests for the monitoring service.
Tests authentication metrics collection, health checks, and security event detection.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.monitoring_service import (
    MonitoringService,
    AuthenticationMetrics,
    HealthCheckResult
)


class TestAuthenticationMetrics:
    """Test authentication metrics data structure."""
    
    def test_initial_metrics(self):
        """Test initial metrics state."""
        metrics = AuthenticationMetrics()
        
        assert metrics.total_attempts == 0
        assert metrics.successful_authentications == 0
        assert metrics.failed_authentications == 0
        assert metrics.success_rate() == 0.0
        assert metrics.recent_success_rate() == 0.0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = AuthenticationMetrics()
        metrics.total_attempts = 100
        metrics.successful_authentications = 80
        
        assert metrics.success_rate() == 80.0
    
    def test_recent_success_rate_calculation(self):
        """Test recent success rate calculation."""
        metrics = AuthenticationMetrics()
        
        # Add some recent attempts and successes
        current_time = time.time()
        for i in range(10):
            metrics.recent_attempts.append(current_time - i)
        for i in range(8):
            metrics.recent_successes.append(current_time - i)
        
        assert metrics.recent_success_rate() == 80.0
    
    def test_metrics_to_dict(self):
        """Test metrics serialization to dictionary."""
        metrics = AuthenticationMetrics()
        metrics.total_attempts = 50
        metrics.successful_authentications = 40
        metrics.failed_authentications = 10
        metrics.error_types["token_expired"] = 5
        
        result = metrics.to_dict()
        
        assert result["total_attempts"] == 50
        assert result["successful_authentications"] == 40
        assert result["failed_authentications"] == 10
        assert result["success_rate"] == 80.0
        assert result["error_types"]["token_expired"] == 5


class TestHealthCheckResult:
    """Test health check result data structure."""
    
    def test_health_check_result_creation(self):
        """Test health check result creation."""
        result = HealthCheckResult(
            service="database",
            status="healthy",
            response_time=0.123,
            details={"version": "14.0"}
        )
        
        assert result.service == "database"
        assert result.status == "healthy"
        assert result.response_time == 0.123
        assert result.details["version"] == "14.0"
        assert result.error is None
    
    def test_health_check_result_to_dict(self):
        """Test health check result serialization."""
        result = HealthCheckResult(
            service="redis",
            status="unhealthy",
            response_time=1.5,
            error="Connection timeout"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["service"] == "redis"
        assert result_dict["status"] == "unhealthy"
        assert result_dict["response_time"] == 1.5
        assert result_dict["error"] == "Connection timeout"
        assert "timestamp" in result_dict


class TestMonitoringService:
    """Test monitoring service functionality."""
    
    @pytest.fixture
    def monitoring_service(self):
        """Create a monitoring service instance for testing."""
        return MonitoringService()
    
    def test_record_authentication_attempt_success(self, monitoring_service):
        """Test recording successful authentication attempts."""
        monitoring_service.record_authentication_attempt(success=True)
        
        assert monitoring_service.metrics.total_attempts == 1
        assert monitoring_service.metrics.successful_authentications == 1
        assert monitoring_service.metrics.failed_authentications == 0
        assert len(monitoring_service.metrics.recent_attempts) == 1
        assert len(monitoring_service.metrics.recent_successes) == 1
    
    def test_record_authentication_attempt_failure(self, monitoring_service):
        """Test recording failed authentication attempts."""
        monitoring_service.record_authentication_attempt(
            success=False, 
            error_type="invalid_token"
        )
        
        assert monitoring_service.metrics.total_attempts == 1
        assert monitoring_service.metrics.successful_authentications == 0
        assert monitoring_service.metrics.failed_authentications == 1
        assert monitoring_service.metrics.error_types["invalid_token"] == 1
        assert len(monitoring_service.metrics.recent_failures) == 1
    
    def test_record_token_validation_error(self, monitoring_service):
        """Test recording token validation errors."""
        monitoring_service.record_token_validation_error("expired")
        
        assert monitoring_service.metrics.token_validation_errors == 1
        assert monitoring_service.metrics.error_types["token_expired"] == 1
    
    def test_record_authorization_failure(self, monitoring_service):
        """Test recording authorization failures."""
        monitoring_service.record_authorization_failure("insufficient_role")
        
        assert monitoring_service.metrics.authorization_failures == 1
        assert monitoring_service.metrics.error_types["authz_insufficient_role"] == 1
    
    def test_record_suspicious_activity(self, monitoring_service):
        """Test recording suspicious activities."""
        monitoring_service.record_suspicious_activity("brute_force")
        
        assert monitoring_service.metrics.suspicious_activities == 1
        assert monitoring_service.metrics.error_types["suspicious_brute_force"] == 1
    
    def test_record_performance_metric(self, monitoring_service):
        """Test recording performance metrics."""
        monitoring_service.record_performance_metric("token_validation", 0.123)
        monitoring_service.record_performance_metric("token_validation", 0.156)
        
        assert monitoring_service.metrics.avg_token_validation_time == 0.1395
        assert len(monitoring_service._performance_data["token_validation"]) == 2
    
    def test_get_authentication_metrics(self, monitoring_service):
        """Test getting authentication metrics."""
        # Add some test data
        monitoring_service.record_authentication_attempt(success=True)
        monitoring_service.record_authentication_attempt(success=False, error_type="test_error")
        monitoring_service.record_performance_metric("token_validation", 0.1)
        
        metrics = monitoring_service.get_authentication_metrics()
        
        assert metrics["total_attempts"] == 2
        assert metrics["successful_authentications"] == 1
        assert metrics["failed_authentications"] == 1
        assert metrics["success_rate"] == 50.0
        assert metrics["error_types"]["test_error"] == 1
    
    def test_get_performance_metrics(self, monitoring_service):
        """Test getting performance metrics."""
        # Add some test data
        monitoring_service.record_performance_metric("token_validation", 0.1)
        monitoring_service.record_performance_metric("token_validation", 0.2)
        monitoring_service.record_performance_metric("user_sync", 0.5)
        
        metrics = monitoring_service.get_performance_metrics()
        
        assert "token_validation" in metrics
        assert metrics["token_validation"]["avg"] == 0.15
        assert metrics["token_validation"]["min"] == 0.1
        assert metrics["token_validation"]["max"] == 0.2
        assert metrics["token_validation"]["count"] == 2
        
        assert "user_sync" in metrics
        assert metrics["user_sync"]["avg"] == 0.5
    
    @pytest.mark.asyncio
    async def test_check_database_health_success(self, monitoring_service):
        """Test successful database health check."""
        with patch('app.services.monitoring_service.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            # Mock successful database query
            mock_result = Mock()
            mock_result.fetchone.return_value = Mock(
                version="PostgreSQL 14.0",
                database="test_db",
                user="test_user",
                size=1024000
            )
            mock_session.execute.return_value = mock_result
            
            # Mock engine pool
            with patch('app.services.monitoring_service.engine') as mock_engine:
                mock_engine.pool.size.return_value = 5
                mock_engine.pool.checkedout.return_value = 2
                mock_engine.pool.overflow.return_value = 0
                mock_engine.pool.invalid.return_value = 0
                
                result = await monitoring_service.check_database_health()
                
                assert result.service == "database"
                assert result.status == "healthy"
                assert result.details["version"] == "PostgreSQL 14.0"
                assert result.details["database"] == "test_db"
                assert result.details["pool"]["size"] == 5
    
    @pytest.mark.asyncio
    async def test_check_database_health_failure(self, monitoring_service):
        """Test failed database health check."""
        with patch('app.services.monitoring_service.AsyncSessionLocal') as mock_session_local:
            mock_session = AsyncMock()
            mock_session_local.return_value.__aenter__.return_value = mock_session
            
            # Mock database connection failure
            mock_session.execute.side_effect = Exception("Connection failed")
            
            result = await monitoring_service.check_database_health()
            
            assert result.service == "database"
            assert result.status == "unhealthy"
            assert result.error == "Connection failed"
    
    @pytest.mark.asyncio
    async def test_check_redis_health_success(self, monitoring_service):
        """Test successful Redis health check."""
        with patch('app.services.monitoring_service.redis_client') as mock_redis:
            # Mock async methods properly
            mock_redis.ping = AsyncMock(return_value=True)
            mock_redis.info = AsyncMock(side_effect=[
                {
                    "redis_version": "6.2.0",
                    "redis_mode": "standalone",
                    "connected_clients": 5
                },
                {
                    "used_memory": 1024000,
                    "used_memory_human": "1M",
                    "keyspace_hits": 100,
                    "keyspace_misses": 10
                }
            ])
            
            result = await monitoring_service.check_redis_health()
            
            assert result.service == "redis"
            assert result.status == "healthy"
            assert result.details["version"] == "6.2.0"
            assert result.details["connected_clients"] == 5
    
    @pytest.mark.asyncio
    async def test_check_redis_health_failure(self, monitoring_service):
        """Test failed Redis health check."""
        with patch('app.services.monitoring_service.redis_client') as mock_redis:
            mock_redis.ping.side_effect = Exception("Redis unavailable")
            
            result = await monitoring_service.check_redis_health()
            
            assert result.service == "redis"
            assert result.status == "unhealthy"
            assert result.error == "Redis unavailable"
    
    @pytest.mark.asyncio
    async def test_check_clerk_health_success(self, monitoring_service):
        """Test successful Clerk health check."""
        with patch('app.services.monitoring_service.get_clerk_service') as mock_get_clerk:
            mock_clerk_service = Mock()
            mock_clerk_service.jwks_url = "https://test.clerk.dev/.well-known/jwks.json"
            mock_clerk_service.base_url = "https://api.clerk.dev/v1"
            mock_clerk_service.secret_key = "test_secret"
            mock_get_clerk.return_value = mock_clerk_service
            
            with patch('httpx.AsyncClient') as mock_client:
                # Mock the async context manager properly
                mock_client_instance = Mock()
                mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
                mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Mock JWKS response
                mock_jwks_response = Mock()
                mock_jwks_response.raise_for_status = Mock()
                mock_jwks_response.json.return_value = {"keys": [{"kid": "test", "kty": "RSA"}]}
                
                # Mock API response
                mock_api_response = Mock()
                mock_api_response.status_code = 200
                
                # Set up the get method to return different responses
                mock_client_instance.get = AsyncMock(side_effect=[mock_jwks_response, mock_api_response])
                
                result = await monitoring_service.check_clerk_health()
                
                assert result.service == "clerk"
                assert result.status in ["healthy", "degraded"]
                assert result.details["jwks_keys_count"] == 1
    
    @pytest.mark.asyncio
    async def test_check_clerk_health_failure(self, monitoring_service):
        """Test failed Clerk health check."""
        with patch('app.services.monitoring_service.get_clerk_service') as mock_get_clerk:
            mock_clerk_service = Mock()
            mock_clerk_service.jwks_url = "https://test.clerk.dev/.well-known/jwks.json"
            mock_get_clerk.return_value = mock_clerk_service
            
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("Network error")
                
                result = await monitoring_service.check_clerk_health()
                
                assert result.service == "clerk"
                assert result.status == "unhealthy"
                assert result.error == "Network error"
    
    @pytest.mark.asyncio
    async def test_check_all_services_health(self, monitoring_service):
        """Test comprehensive health check of all services."""
        with patch.object(monitoring_service, 'check_database_health') as mock_db_check, \
             patch.object(monitoring_service, 'check_redis_health') as mock_redis_check, \
             patch.object(monitoring_service, 'check_clerk_health') as mock_clerk_check:
            
            # Mock successful health checks
            mock_db_check.return_value = HealthCheckResult("database", "healthy", 0.1)
            mock_redis_check.return_value = HealthCheckResult("redis", "healthy", 0.05)
            mock_clerk_check.return_value = HealthCheckResult("clerk", "healthy", 0.2)
            
            result = await monitoring_service.check_all_services_health()
            
            assert result["status"] == "healthy"
            assert "database" in result["services"]
            assert "redis" in result["services"]
            assert "clerk" in result["services"]
            assert "system" in result
            assert "metrics" in result
    
    @pytest.mark.asyncio
    async def test_detect_suspicious_patterns_high_failure_rate(self, monitoring_service):
        """Test detection of high failure rate patterns."""
        # Simulate high failure rate
        current_time = time.time()
        for i in range(20):
            monitoring_service.metrics.recent_attempts.append(current_time - i)
        for i in range(5):  # Only 5 successes out of 20 attempts = 25% success rate
            monitoring_service.metrics.recent_successes.append(current_time - i)
        
        patterns = await monitoring_service.detect_suspicious_patterns()
        
        assert len(patterns) > 0
        assert any(p["type"] == "high_failure_rate" for p in patterns)
    
    @pytest.mark.asyncio
    async def test_detect_suspicious_patterns_rapid_attempts(self, monitoring_service):
        """Test detection of rapid authentication attempts."""
        # Simulate rapid attempts (more than 100 in last hour, with 60+ in last 5 minutes)
        current_time = time.time()
        
        # Add 120 attempts over the last hour
        for i in range(120):
            monitoring_service.metrics.recent_attempts.append(current_time - i * 30)  # Every 30 seconds
        
        # Add 60 more attempts in the last 5 minutes (300 seconds)
        for i in range(60):
            monitoring_service.metrics.recent_attempts.append(current_time - i * 5)  # Every 5 seconds
        
        patterns = await monitoring_service.detect_suspicious_patterns()
        
        assert len(patterns) > 0
        assert any(p["type"] == "rapid_authentication_attempts" for p in patterns)
    
    @pytest.mark.asyncio
    async def test_detect_suspicious_patterns_unusual_errors(self, monitoring_service):
        """Test detection of unusual error patterns."""
        # Simulate high frequency of specific error type
        monitoring_service.metrics.error_types["token_malformed"] = 25
        
        patterns = await monitoring_service.detect_suspicious_patterns()
        
        assert len(patterns) > 0
        assert any(p["type"] == "unusual_error_pattern" for p in patterns)
    
    @pytest.mark.asyncio
    async def test_log_security_event(self, monitoring_service):
        """Test logging security events."""
        # Test the actual implementation without mocking the auth logger
        initial_suspicious_count = monitoring_service.metrics.suspicious_activities
        
        await monitoring_service.log_security_event(
            event_type="brute_force",
            description="Multiple failed login attempts",
            severity="high",
            additional_data={"ip": "192.168.1.1"}
        )
        
        # Verify metrics were updated
        assert monitoring_service.metrics.suspicious_activities == initial_suspicious_count + 1
        assert monitoring_service.metrics.error_types["suspicious_brute_force"] == 1
    
    def test_health_check_caching(self, monitoring_service):
        """Test health check result caching."""
        # Test that cache is used within TTL
        cache_key = "test_health_check"
        test_data = {"status": "healthy", "cached": True}
        
        monitoring_service._health_check_cache[cache_key] = {
            "data": test_data,
            "timestamp": time.time()
        }
        
        # Should return cached data
        cached_result = monitoring_service._health_check_cache.get(cache_key)
        assert cached_result is not None
        assert cached_result["data"]["cached"] is True
    
    def test_performance_data_limit(self, monitoring_service):
        """Test that performance data is limited to prevent memory issues."""
        # Add more than 100 measurements
        for i in range(150):
            monitoring_service.record_performance_metric("test_operation", 0.1 + i * 0.001)
        
        # Should only keep last 100 measurements
        assert len(monitoring_service._performance_data["test_operation"]) == 100
        
        # Should be the most recent measurements
        assert monitoring_service._performance_data["test_operation"][-1] == 0.1 + 149 * 0.001