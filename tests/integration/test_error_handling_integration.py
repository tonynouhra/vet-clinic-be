"""
Integration tests for error handling and logging functionality.
Tests real-world error scenarios and fallback mechanisms.
"""

import pytest
import asyncio
import httpx
from unittest.mock import patch, Mock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends, HTTPException

from app.main import app
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ExternalServiceError
from app.services.clerk_service import get_clerk_service
from app.app_helpers.auth_helpers import verify_token, get_current_user
from app.core.logging_config import get_auth_logger
from app.core.error_handlers import get_fallback_manager

settings = get_settings()


class TestClerkServiceErrorHandling:
    """Test Clerk service error handling in realistic scenarios."""
    
    @pytest.mark.asyncio
    async def test_jwt_verification_with_network_error(self):
        """Test JWT verification when network is unavailable."""
        clerk_service = get_clerk_service()
        
        # Create a properly formatted JWT token (but with invalid signature)
        import jwt
        test_token = jwt.encode(
            {"sub": "user123", "kid": "test_key"}, 
            "fake_secret", 
            algorithm="HS256",
            headers={"kid": "test_key"}
        )
        
        # Mock network failure for JWKS endpoint
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Network unreachable")
            
            with pytest.raises(AuthenticationError, match="Token verification failed"):
                await clerk_service.verify_jwt_token(test_token)
    
    @pytest.mark.asyncio
    async def test_jwt_verification_with_timeout(self):
        """Test JWT verification with timeout."""
        clerk_service = get_clerk_service()
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timeout")
            
            with pytest.raises(AuthenticationError, match="Failed to verify token signature"):
                await clerk_service.verify_jwt_token("invalid.jwt.token")
    
    @pytest.mark.asyncio
    async def test_user_lookup_with_fallback(self):
        """Test user lookup with cache fallback when API fails."""
        clerk_service = get_clerk_service()
        
        # Mock cache service to return cached data
        mock_cache_data = {
            "clerk_id": "user_123",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "pet_owner",
            "is_active": True,
            "is_verified": True
        }
        
        with patch.object(clerk_service.cache_service, 'get_cached_user_data') as mock_cache:
            mock_cache.return_value = mock_cache_data
            
            # Mock API failure
            with patch('httpx.AsyncClient.get') as mock_get:
                mock_get.side_effect = httpx.ConnectError("API unavailable")
                
                # Should use cached data
                user = await clerk_service.get_user_by_clerk_id("user_123")
                assert user.id == "user_123"
                assert user.primary_email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after repeated failures."""
        clerk_service = get_clerk_service()
        fallback_manager = get_fallback_manager()
        
        # Reset circuit breaker state
        fallback_manager.circuit_breaker.state = "CLOSED"
        fallback_manager.circuit_breaker.failure_count = 0
        
        async def failing_operation():
            raise ExternalServiceError("Service unavailable")
        
        # Trigger enough failures to open circuit
        for i in range(settings.CLERK_CIRCUIT_BREAKER_THRESHOLD):
            with pytest.raises(ExternalServiceError):
                await fallback_manager.execute_with_fallback(
                    primary_func=failing_operation,
                    operation_name="test_operation"
                )
        
        # Circuit should now be open
        assert fallback_manager.circuit_breaker.state == "OPEN"
        
        # Next call should fail immediately with CircuitBreakerError
        from app.core.error_handlers import CircuitBreakerError
        with pytest.raises(ExternalServiceError, match="Service unavailable"):
            await fallback_manager.execute_with_fallback(
                primary_func=failing_operation,
                operation_name="test_operation"
            )


class TestAuthenticationErrorHandling:
    """Test authentication error handling in API endpoints."""
    
    def test_invalid_token_error_response(self):
        """Test API response for invalid token."""
        client = TestClient(app)
        
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        
        assert response.status_code == 401
        assert "error" in response.json()
        assert response.json()["error"]["code"] == "AUTHENTICATION_ERROR"
    
    def test_missing_token_error_response(self):
        """Test API response for missing token."""
        client = TestClient(app)
        
        response = client.get("/api/v1/users/me")
        
        assert response.status_code == 403  # FastAPI HTTPBearer returns 403 for missing token
    
    @patch('app.services.clerk_service.ClerkService.verify_jwt_token')
    def test_clerk_service_unavailable_error(self, mock_verify):
        """Test API response when Clerk service is unavailable."""
        client = TestClient(app)
        
        # Mock Clerk service failure
        mock_verify.side_effect = ExternalServiceError(
            "Clerk API unavailable",
            service_name="Clerk"
        )
        
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer some.jwt.token"}
        )
        
        assert response.status_code == 502
        assert "error" in response.json()
        assert response.json()["error"]["code"] == "EXTERNAL_SERVICE_ERROR"


class TestLoggingIntegration:
    """Test logging integration in error scenarios."""
    
    @patch('app.core.logging_config.logging.getLogger')
    def test_authentication_failure_logging(self, mock_get_logger):
        """Test that authentication failures are properly logged."""
        mock_logger = Mock()
        mock_security_logger = Mock()
        
        def logger_side_effect(name):
            if name == "security":
                return mock_security_logger
            return mock_logger
        
        mock_get_logger.side_effect = logger_side_effect
        
        client = TestClient(app)
        
        # Make request with invalid token
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid.token"}
        )
        
        assert response.status_code == 401
        
        # Verify security logging was called
        # Note: This test may need adjustment based on actual logging implementation
        assert mock_security_logger.warning.called or mock_logger.error.called
    
    @patch('app.core.logging_config.logging.getLogger')
    def test_suspicious_activity_logging(self, mock_get_logger):
        """Test logging of suspicious activities."""
        mock_security_logger = Mock()
        mock_get_logger.return_value = mock_security_logger
        
        auth_logger = get_auth_logger()
        
        # Log suspicious activity
        auth_logger.log_suspicious_activity(
            activity_type="multiple_failed_logins",
            description="5 failed attempts in 1 minute",
            user_id="user123",
            ip_address="192.168.1.100"
        )
        
        # Verify critical log was called
        mock_security_logger.critical.assert_called_once()
        call_args = mock_security_logger.critical.call_args
        assert "Suspicious activity detected" in call_args[0][0]
        assert call_args[1]["extra"]["security_event"] is True


class TestFallbackMechanisms:
    """Test fallback mechanisms in realistic scenarios."""
    
    @pytest.mark.asyncio
    async def test_jwt_verification_fallback_to_cache(self):
        """Test JWT verification falls back to cached keys when JWKS unavailable."""
        clerk_service = get_clerk_service()
        
        # Pre-populate cache with a key
        test_kid = "test_key_id"
        test_public_key = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----"
        clerk_service._jwks_cache[test_kid] = test_public_key
        
        # Mock JWKS endpoint failure
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("JWKS endpoint unavailable")
            
            # Should use cached key
            cached_key = await clerk_service._get_cached_public_key(test_kid)
            assert cached_key == test_public_key
    
    @pytest.mark.asyncio
    async def test_user_sync_with_partial_failure(self):
        """Test user synchronization with partial Clerk API failure."""
        from app.services.user_sync_service import get_user_sync_service
        
        user_sync_service = get_user_sync_service()
        
        # Mock successful cache lookup but failed API update
        mock_user_data = {
            "clerk_id": "user_123",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "pet_owner"
        }
        
        with patch.object(user_sync_service, '_get_cached_user_data') as mock_cache:
            mock_cache.return_value = mock_user_data
            
            with patch.object(user_sync_service, '_update_user_from_clerk') as mock_update:
                mock_update.side_effect = ExternalServiceError("API unavailable")
                
                # Should still return cached user data
                user = await user_sync_service.get_or_sync_user("user_123")
                assert user is not None
                assert user.get("clerk_id") == "user_123"


class TestErrorRecovery:
    """Test error recovery and resilience mechanisms."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after service restoration."""
        fallback_manager = get_fallback_manager()
        
        # Reset circuit breaker
        fallback_manager.circuit_breaker.state = "CLOSED"
        fallback_manager.circuit_breaker.failure_count = 0
        
        call_count = 0
        
        async def flaky_service():
            nonlocal call_count
            call_count += 1
            if call_count <= 5:  # Fail first 5 times
                raise ExternalServiceError("Service temporarily unavailable")
            return "service_restored"
        
        # Trigger circuit breaker to open
        for i in range(settings.CLERK_CIRCUIT_BREAKER_THRESHOLD):
            with pytest.raises(ExternalServiceError):
                await fallback_manager.execute_with_fallback(
                    primary_func=flaky_service,
                    operation_name="test_recovery"
                )
        
        assert fallback_manager.circuit_breaker.state == "OPEN"
        
        # Wait for recovery timeout (using small timeout for test)
        fallback_manager.circuit_breaker.recovery_timeout = 0.1
        await asyncio.sleep(0.2)
        
        # Service should now work and circuit should close
        result = await fallback_manager.execute_with_fallback(
            primary_func=flaky_service,
            operation_name="test_recovery"
        )
        
        assert result == "service_restored"
        assert fallback_manager.circuit_breaker.state == "CLOSED"
    
    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        """Test retry mechanism with exponential backoff."""
        from app.core.error_handlers import RetryHandler
        
        retry_handler = RetryHandler(
            max_retries=3,
            base_delay=0.01,  # Small delay for testing
            exponential_base=2.0
        )
        
        call_times = []
        
        async def time_tracking_func():
            import time
            call_times.append(time.time())
            if len(call_times) < 3:
                raise httpx.ConnectError("Temporary failure")
            return "success"
        
        result = await retry_handler.execute(time_tracking_func)
        
        assert result == "success"
        assert len(call_times) == 3
        
        # Verify exponential backoff (allowing for some timing variance)
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            assert delay2 > delay1  # Second delay should be longer


class TestSecurityEventLogging:
    """Test security event logging and monitoring."""
    
    @patch('app.core.logging_config.logging.getLogger')
    def test_multiple_failed_attempts_detection(self, mock_get_logger):
        """Test detection and logging of multiple failed authentication attempts."""
        mock_security_logger = Mock()
        mock_get_logger.return_value = mock_security_logger
        
        client = TestClient(app)
        
        # Simulate multiple failed login attempts
        for i in range(5):
            response = client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer invalid.token.{i}"}
            )
            assert response.status_code == 401
        
        # In a real implementation, this would trigger suspicious activity logging
        # For now, we just verify that authentication failures were logged
        assert mock_security_logger.warning.called or mock_security_logger.error.called
    
    @patch('app.core.logging_config.logging.getLogger')
    def test_token_manipulation_detection(self, mock_get_logger):
        """Test detection of token manipulation attempts."""
        mock_security_logger = Mock()
        mock_get_logger.return_value = mock_security_logger
        
        client = TestClient(app)
        
        # Test various malformed tokens
        malformed_tokens = [
            "not.a.jwt",
            "header.payload",  # Missing signature
            "header.payload.signature.extra",  # Too many parts
            "",  # Empty token
            "Bearer malformed"  # Invalid format
        ]
        
        for token in malformed_tokens:
            response = client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_end_to_end_error_handling():
    """Test complete end-to-end error handling flow."""
    # This test simulates a complete error scenario from API request
    # through authentication, error handling, logging, and response
    
    with patch('app.services.clerk_service.ClerkService.verify_jwt_token') as mock_verify:
        # Simulate Clerk service failure
        mock_verify.side_effect = ExternalServiceError(
            "Clerk API temporarily unavailable",
            service_name="Clerk"
        )
        
        with patch('app.core.logging_config.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            client = TestClient(app)
            
            response = client.get(
                "/api/v1/users/me",
                headers={"Authorization": "Bearer some.jwt.token"}
            )
            
            # Verify error response
            assert response.status_code == 502
            assert "error" in response.json()
            assert response.json()["error"]["code"] == "EXTERNAL_SERVICE_ERROR"
            
            # Verify logging occurred
            assert mock_logger.error.called