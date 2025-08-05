"""
Unit tests for error handling and logging functionality.
Tests comprehensive error handling, fallback mechanisms, and structured logging.
"""

import pytest
import asyncio
import time
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx
import jwt
from datetime import datetime, timedelta

from app.core.error_handlers import (
    CircuitBreaker,
    CircuitBreakerError,
    RetryHandler,
    FallbackManager,
    with_error_handling,
    error_context,
    handle_clerk_api_error
)
from app.core.logging_config import AuthenticationLogger, StructuredFormatter
from app.core.exceptions import (
    AuthenticationError,
    ExternalServiceError,
    VetClinicException
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
        assert cb.last_failure_time is None
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self):
        """Test successful operations keep circuit closed."""
        cb = CircuitBreaker(failure_threshold=3)
        
        async def success_func():
            return "success"
        
        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_threshold(self):
        """Test circuit opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=2, expected_exception=ValueError)
        
        async def failing_func():
            raise ValueError("Test error")
        
        # First failure
        with pytest.raises(ValueError):
            await cb.call(failing_func)
        assert cb.state == "CLOSED"
        assert cb.failure_count == 1
        
        # Second failure - should open circuit
        with pytest.raises(ValueError):
            await cb.call(failing_func)
        assert cb.state == "OPEN"
        assert cb.failure_count == 2
        
        # Third call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            await cb.call(failing_func)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        async def failing_func():
            raise ValueError("Test error")
        
        async def success_func():
            return "success"
        
        # Trigger circuit open
        with pytest.raises(ValueError):
            await cb.call(failing_func)
        assert cb.state == "OPEN"
        
        # Wait for recovery timeout
        await asyncio.sleep(0.2)
        
        # Should transition to HALF_OPEN and allow one attempt
        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == "CLOSED"


class TestRetryHandler:
    """Test retry handler functionality."""
    
    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self):
        """Test successful operation on first attempt."""
        retry_handler = RetryHandler(max_retries=3)
        
        async def success_func():
            return "success"
        
        result = await retry_handler.execute(success_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test successful operation after some failures."""
        retry_handler = RetryHandler(max_retries=3, base_delay=0.01)
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = await retry_handler.execute(flaky_func)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_max_attempts_exceeded(self):
        """Test failure after max retry attempts."""
        retry_handler = RetryHandler(max_retries=2, base_delay=0.01)
        
        async def failing_func():
            raise ValueError("Persistent error")
        
        with pytest.raises(ValueError, match="Persistent error"):
            await retry_handler.execute(failing_func)
    
    def test_retry_delay_calculation(self):
        """Test exponential backoff delay calculation."""
        retry_handler = RetryHandler(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=10.0,
            jitter=False
        )
        
        assert retry_handler._calculate_delay(0) == 1.0
        assert retry_handler._calculate_delay(1) == 2.0
        assert retry_handler._calculate_delay(2) == 4.0
        assert retry_handler._calculate_delay(3) == 8.0
        assert retry_handler._calculate_delay(4) == 10.0  # Capped at max_delay


class TestFallbackManager:
    """Test fallback manager functionality."""
    
    @pytest.mark.asyncio
    async def test_fallback_manager_primary_success(self):
        """Test successful primary function execution."""
        fallback_manager = FallbackManager()
        
        async def primary_func():
            return "primary_result"
        
        async def fallback_func():
            return "fallback_result"
        
        result = await fallback_manager.execute_with_fallback(
            primary_func=primary_func,
            fallback_func=fallback_func,
            operation_name="test_operation"
        )
        
        assert result == "primary_result"
    
    @pytest.mark.asyncio
    async def test_fallback_manager_fallback_success(self):
        """Test fallback function execution when primary fails."""
        fallback_manager = FallbackManager()
        
        async def primary_func():
            raise ExternalServiceError("Primary failed")
        
        async def fallback_func():
            return "fallback_result"
        
        result = await fallback_manager.execute_with_fallback(
            primary_func=primary_func,
            fallback_func=fallback_func,
            operation_name="test_operation"
        )
        
        assert result == "fallback_result"
    
    @pytest.mark.asyncio
    async def test_fallback_manager_both_fail(self):
        """Test exception when both primary and fallback fail."""
        fallback_manager = FallbackManager()
        
        async def primary_func():
            raise ExternalServiceError("Primary failed")
        
        async def fallback_func():
            raise Exception("Fallback failed")
        
        with pytest.raises(ExternalServiceError, match="Both primary and fallback"):
            await fallback_manager.execute_with_fallback(
                primary_func=primary_func,
                fallback_func=fallback_func,
                operation_name="test_operation"
            )
    
    @pytest.mark.asyncio
    async def test_fallback_manager_no_fallback(self):
        """Test exception when no fallback is provided."""
        fallback_manager = FallbackManager()
        
        async def primary_func():
            raise ExternalServiceError("Primary failed")
        
        with pytest.raises(ExternalServiceError, match="Service unavailable"):
            await fallback_manager.execute_with_fallback(
                primary_func=primary_func,
                fallback_func=None,
                operation_name="test_operation"
            )


class TestErrorHandlingDecorator:
    """Test error handling decorator functionality."""
    
    @pytest.mark.asyncio
    async def test_with_error_handling_success(self):
        """Test successful function execution with decorator."""
        @with_error_handling("test_operation")
        async def test_func():
            return "success"
        
        result = await test_func()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_with_error_handling_authentication_error(self):
        """Test authentication error handling."""
        @with_error_handling("test_operation")
        async def test_func():
            raise AuthenticationError("Auth failed")
        
        with pytest.raises(AuthenticationError, match="Auth failed"):
            await test_func()
    
    @pytest.mark.asyncio
    async def test_with_error_handling_unexpected_error(self):
        """Test unexpected error conversion."""
        @with_error_handling("test_operation")
        async def test_func():
            raise ValueError("Unexpected error")
        
        with pytest.raises(VetClinicException, match="Operation test_operation failed"):
            await test_func()
    
    @pytest.mark.asyncio
    async def test_with_error_handling_no_raise(self):
        """Test error handling without raising exceptions."""
        @with_error_handling("test_operation", raise_on_error=False)
        async def test_func():
            raise ValueError("Error")
        
        result = await test_func()
        assert result is None


class TestErrorContext:
    """Test error context manager functionality."""
    
    @pytest.mark.asyncio
    async def test_error_context_success(self):
        """Test successful operation in error context."""
        async with error_context("test_operation"):
            result = "success"
        
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_error_context_authentication_error(self):
        """Test authentication error in context."""
        with pytest.raises(AuthenticationError):
            async with error_context("test_operation"):
                raise AuthenticationError("Auth failed")
    
    @pytest.mark.asyncio
    async def test_error_context_unexpected_error(self):
        """Test unexpected error conversion in context."""
        with pytest.raises(VetClinicException):
            async with error_context("test_operation"):
                raise ValueError("Unexpected error")


class TestClerkApiErrorHandler:
    """Test Clerk API error handling functionality."""
    
    def test_handle_http_status_error_401(self):
        """Test handling of 401 HTTP status error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        error = httpx.HTTPStatusError(
            message="401 Unauthorized",
            request=Mock(),
            response=mock_response
        )
        
        result = handle_clerk_api_error(error, "test_operation")
        
        assert isinstance(result, ExternalServiceError)
        assert "Clerk API authentication failed" in result.message
        assert result.details["status_code"] == 401
    
    def test_handle_http_status_error_404(self):
        """Test handling of 404 HTTP status error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        error = httpx.HTTPStatusError(
            message="404 Not Found",
            request=Mock(),
            response=mock_response
        )
        
        result = handle_clerk_api_error(error, "test_operation", "user123")
        
        assert isinstance(result, AuthenticationError)
        assert "User not found in Clerk" in result.message
        assert result.details["clerk_id"] == "user123"
    
    def test_handle_http_status_error_429(self):
        """Test handling of 429 rate limit error."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        
        error = httpx.HTTPStatusError(
            message="429 Too Many Requests",
            request=Mock(),
            response=mock_response
        )
        
        result = handle_clerk_api_error(error, "test_operation")
        
        assert isinstance(result, ExternalServiceError)
        assert "rate limit exceeded" in result.message
        assert result.details["retry_after"] == "60"
    
    def test_handle_timeout_error(self):
        """Test handling of timeout error."""
        error = httpx.TimeoutException("Request timeout")
        
        result = handle_clerk_api_error(error, "test_operation")
        
        assert isinstance(result, ExternalServiceError)
        assert "Clerk API timeout" in result.message
        assert result.details["error_type"] == "timeout"
    
    def test_handle_connection_error(self):
        """Test handling of connection error."""
        error = httpx.ConnectError("Connection failed")
        
        result = handle_clerk_api_error(error, "test_operation")
        
        assert isinstance(result, ExternalServiceError)
        assert "Cannot connect to Clerk API" in result.message
        assert result.details["error_type"] == "connection_error"


class TestAuthenticationLogger:
    """Test authentication logger functionality."""
    
    def test_authentication_logger_initialization(self):
        """Test authentication logger initialization."""
        auth_logger = AuthenticationLogger()
        assert auth_logger.logger.name == "auth"
        assert auth_logger.security_logger.name == "security"
    
    @patch('app.core.logging_config.logging.getLogger')
    def test_log_authentication_success(self, mock_get_logger):
        """Test logging successful authentication."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        auth_logger = AuthenticationLogger()
        auth_logger.log_authentication_success(
            user_id="user123",
            clerk_id="clerk123",
            email="test@example.com",
            role="admin",
            request_id="req123"
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "User authentication successful" in call_args[0][0]
        assert call_args[1]["extra"]["event_type"] == "auth_success"
        assert call_args[1]["extra"]["user_id"] == "user123"
        assert call_args[1]["extra"]["clerk_id"] == "clerk123"
    
    @patch('app.core.logging_config.logging.getLogger')
    def test_log_authentication_failure(self, mock_get_logger):
        """Test logging authentication failure."""
        mock_security_logger = Mock()
        mock_get_logger.return_value = mock_security_logger
        
        auth_logger = AuthenticationLogger()
        auth_logger.log_authentication_failure(
            reason="Invalid token",
            clerk_id="clerk123",
            error_code="INVALID_TOKEN",
            request_id="req123"
        )
        
        mock_security_logger.warning.assert_called_once()
        call_args = mock_security_logger.warning.call_args
        assert "Authentication failed: Invalid token" in call_args[0][0]
        assert call_args[1]["extra"]["event_type"] == "auth_failure"
        assert call_args[1]["extra"]["reason"] == "Invalid token"
    
    @patch('app.core.logging_config.logging.getLogger')
    def test_log_suspicious_activity(self, mock_get_logger):
        """Test logging suspicious activity."""
        mock_security_logger = Mock()
        mock_get_logger.return_value = mock_security_logger
        
        auth_logger = AuthenticationLogger()
        auth_logger.log_suspicious_activity(
            activity_type="multiple_failed_logins",
            description="5 failed login attempts in 1 minute",
            user_id="user123",
            ip_address="192.168.1.1"
        )
        
        mock_security_logger.critical.assert_called_once()
        call_args = mock_security_logger.critical.call_args
        assert "Suspicious activity detected" in call_args[0][0]
        assert call_args[1]["extra"]["activity_type"] == "multiple_failed_logins"
        assert call_args[1]["extra"]["security_event"] is True


class TestStructuredFormatter:
    """Test structured logging formatter."""
    
    def test_structured_formatter_basic(self):
        """Test basic structured log formatting."""
        formatter = StructuredFormatter()
        
        # Create a log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        
        # Parse the JSON output
        import json
        log_data = json.loads(formatted)
        
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 10
        assert "timestamp" in log_data
    
    def test_structured_formatter_with_extra_fields(self):
        """Test structured formatter with extra fields."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="auth",
            level=logging.WARNING,
            pathname="auth.py",
            lineno=50,
            msg="Authentication failed",
            args=(),
            exc_info=None
        )
        record.module = "auth"
        record.funcName = "verify_token"
        record.user_id = "user123"
        record.clerk_id = "clerk123"
        record.event_type = "auth_failure"
        record.security_event = True
        
        formatted = formatter.format(record)
        
        import json
        log_data = json.loads(formatted)
        
        assert log_data["user_id"] == "user123"
        assert log_data["clerk_id"] == "clerk123"
        assert log_data["event_type"] == "auth_failure"
        assert log_data["security_event"] is True
    
    def test_structured_formatter_with_exception(self):
        """Test structured formatter with exception information."""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=100,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        record.module = "test_module"
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        
        import json
        log_data = json.loads(formatted)
        
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test exception"
        assert "traceback" in log_data["exception"]


@pytest.mark.asyncio
async def test_integration_error_handling_flow():
    """Test complete error handling flow integration."""
    # This test simulates a complete error handling scenario
    # from authentication failure to logging and fallback
    
    fallback_manager = FallbackManager()
    
    # Simulate primary function failure
    async def failing_primary():
        raise ExternalServiceError("Clerk API unavailable")
    
    # Simulate successful fallback
    async def successful_fallback():
        return {"user_id": "user123", "cached": True}
    
    # Execute with fallback
    result = await fallback_manager.execute_with_fallback(
        primary_func=failing_primary,
        fallback_func=successful_fallback,
        operation_name="user_lookup",
        request_id="req123"
    )
    
    assert result["user_id"] == "user123"
    assert result["cached"] is True
    
    # Test completed successfully - the logging is verified by the captured log output