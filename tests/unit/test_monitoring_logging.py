"""
Unit tests for monitoring and security logging functionality.
Tests structured logging, security event detection, and log formatting.
"""

import pytest
import json
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.core.logging_config import (
    StructuredFormatter,
    AuthenticationLogger,
    get_auth_logger
)


class TestStructuredFormatter:
    """Test structured JSON log formatter."""
    
    def test_basic_log_formatting(self):
        """Test basic log record formatting."""
        formatter = StructuredFormatter()
        
        # Create a mock log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42
        assert "timestamp" in log_data
    
    def test_log_formatting_with_extra_fields(self):
        """Test log formatting with authentication-specific extra fields."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="auth",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Authentication successful",
            args=(),
            exc_info=None
        )
        record.module = "auth_module"
        record.funcName = "authenticate"
        
        # Add authentication-specific fields
        record.user_id = "user_123"
        record.clerk_id = "clerk_456"
        record.request_id = "req_789"
        record.event_type = "auth_success"
        record.ip_address = "192.168.1.1"
        record.user_agent = "Mozilla/5.0"
        record.security_event = True
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["user_id"] == "user_123"
        assert log_data["clerk_id"] == "clerk_456"
        assert log_data["request_id"] == "req_789"
        assert log_data["event_type"] == "auth_success"
        assert log_data["ip_address"] == "192.168.1.1"
        assert log_data["user_agent"] == "Mozilla/5.0"
        assert log_data["security_event"] is True
    
    def test_log_formatting_with_exception(self):
        """Test log formatting with exception information."""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        record.module = "test_module"
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test exception"
        assert "traceback" in log_data["exception"]


class TestAuthenticationLogger:
    """Test authentication-specific logging functionality."""
    
    @pytest.fixture
    def auth_logger(self):
        """Create authentication logger for testing."""
        return AuthenticationLogger()
    
    def test_log_authentication_success(self, auth_logger):
        """Test logging successful authentication."""
        with patch.object(auth_logger.logger, 'info') as mock_info:
            auth_logger.log_authentication_success(
                user_id="user_123",
                clerk_id="clerk_456",
                email="test@example.com",
                role="pet_owner",
                request_id="req_789",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0"
            )
            
            mock_info.assert_called_once_with(
                "User authentication successful",
                extra={
                    "event_type": "auth_success",
                    "user_id": "user_123",
                    "clerk_id": "clerk_456",
                    "email": "test@example.com",
                    "role": "pet_owner",
                    "request_id": "req_789",
                    "ip_address": "192.168.1.1",
                    "user_agent": "Mozilla/5.0",
                    "security_event": True
                }
            )
    
    def test_log_authentication_failure(self, auth_logger):
        """Test logging failed authentication."""
        with patch.object(auth_logger.security_logger, 'warning') as mock_warning:
            auth_logger.log_authentication_failure(
                reason="Invalid token",
                clerk_id="clerk_456",
                email="test@example.com",
                error_code="TOKEN_INVALID",
                request_id="req_789",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                token_info={"expired": True}
            )
            
            expected_extra = {
                "event_type": "auth_failure",
                "reason": "Invalid token",
                "clerk_id": "clerk_456",
                "email": "test@example.com",
                "error_code": "TOKEN_INVALID",
                "request_id": "req_789",
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "security_event": True,
                "token_info": {"expired": True}
            }
            
            mock_warning.assert_called_once_with(
                "Authentication failed: Invalid token",
                extra=expected_extra
            )
    
    def test_log_authorization_failure(self, auth_logger):
        """Test logging authorization failure."""
        with patch.object(auth_logger.security_logger, 'warning') as mock_warning:
            auth_logger.log_authorization_failure(
                user_id="user_123",
                clerk_id="clerk_456",
                required_role="admin",
                user_role="pet_owner",
                endpoint="/admin/users",
                method="GET",
                request_id="req_789",
                ip_address="192.168.1.1"
            )
            
            mock_warning.assert_called_once_with(
                "Authorization denied",
                extra={
                    "event_type": "auth_denied",
                    "user_id": "user_123",
                    "clerk_id": "clerk_456",
                    "required_role": "admin",
                    "required_permission": None,
                    "user_role": "pet_owner",
                    "endpoint": "/admin/users",
                    "method": "GET",
                    "request_id": "req_789",
                    "ip_address": "192.168.1.1",
                    "security_event": True
                }
            )
    
    def test_log_token_validation_error(self, auth_logger):
        """Test logging token validation errors."""
        with patch.object(auth_logger.security_logger, 'error') as mock_error:
            auth_logger.log_token_validation_error(
                error_type="expired_token",
                error_message="Token has expired",
                token_info={"exp": 1234567890},
                request_id="req_789",
                ip_address="192.168.1.1"
            )
            
            expected_extra = {
                "event_type": "token_validation_error",
                "error_type": "expired_token",
                "error_message": "Token has expired",
                "request_id": "req_789",
                "ip_address": "192.168.1.1",
                "security_event": True,
                "token_info": {"exp": 1234567890}
            }
            
            mock_error.assert_called_once_with(
                "Token validation failed: expired_token",
                extra=expected_extra
            )
    
    def test_log_clerk_api_error(self, auth_logger):
        """Test logging Clerk API errors."""
        with patch.object(auth_logger.logger, 'error') as mock_error:
            auth_logger.log_clerk_api_error(
                operation="get_user",
                status_code=500,
                error_message="Internal server error",
                clerk_id="clerk_456",
                request_id="req_789",
                response_time=1.5
            )
            
            mock_error.assert_called_once_with(
                "Clerk API error during get_user",
                extra={
                    "event_type": "clerk_api_error",
                    "operation": "get_user",
                    "status_code": 500,
                    "error_message": "Internal server error",
                    "clerk_id": "clerk_456",
                    "request_id": "req_789",
                    "response_time": 1.5
                }
            )
    
    def test_log_webhook_event_success(self, auth_logger):
        """Test logging successful webhook events."""
        with patch.object(auth_logger.logger, 'log') as mock_log:
            auth_logger.log_webhook_event(
                event_type="user.created",
                clerk_id="clerk_456",
                success=True,
                request_id="req_789"
            )
            
            mock_log.assert_called_once_with(
                logging.INFO,
                "Webhook user.created processed successfully",
                extra={
                    "event_type": "webhook_processing",
                    "webhook_event_type": "user.created",
                    "clerk_id": "clerk_456",
                    "success": True,
                    "request_id": "req_789"
                }
            )
    
    def test_log_webhook_event_failure(self, auth_logger):
        """Test logging failed webhook events."""
        with patch.object(auth_logger.logger, 'log') as mock_log:
            auth_logger.log_webhook_event(
                event_type="user.updated",
                clerk_id="clerk_456",
                success=False,
                error_message="Database connection failed",
                request_id="req_789"
            )
            
            mock_log.assert_called_once_with(
                logging.ERROR,
                "Webhook user.updated processed with error",
                extra={
                    "event_type": "webhook_processing",
                    "webhook_event_type": "user.updated",
                    "clerk_id": "clerk_456",
                    "success": False,
                    "request_id": "req_789",
                    "error_message": "Database connection failed"
                }
            )
    
    def test_log_suspicious_activity(self, auth_logger):
        """Test logging suspicious activities."""
        with patch.object(auth_logger.security_logger, 'critical') as mock_critical:
            auth_logger.log_suspicious_activity(
                activity_type="brute_force",
                description="Multiple failed login attempts from same IP",
                user_id="user_123",
                clerk_id="clerk_456",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                request_id="req_789",
                additional_data={"attempt_count": 10, "time_window": "5 minutes"}
            )
            
            expected_extra = {
                "event_type": "suspicious_activity",
                "activity_type": "brute_force",
                "description": "Multiple failed login attempts from same IP",
                "user_id": "user_123",
                "clerk_id": "clerk_456",
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0",
                "request_id": "req_789",
                "security_event": True,
                "attempt_count": 10,
                "time_window": "5 minutes"
            }
            
            mock_critical.assert_called_once_with(
                "Suspicious activity detected: brute_force",
                extra=expected_extra
            )
    
    def test_log_service_unavailable(self, auth_logger):
        """Test logging service unavailability."""
        with patch.object(auth_logger.logger, 'error') as mock_error:
            auth_logger.log_service_unavailable(
                service_name="clerk",
                error_message="Connection timeout",
                fallback_used=True,
                request_id="req_789"
            )
            
            mock_error.assert_called_once_with(
                "Service clerk unavailable",
                extra={
                    "event_type": "service_unavailable",
                    "service_name": "clerk",
                    "error_message": "Connection timeout",
                    "fallback_used": True,
                    "request_id": "req_789"
                }
            )


class TestLoggingIntegration:
    """Test logging integration with monitoring service."""
    
    def test_get_auth_logger_singleton(self):
        """Test that get_auth_logger returns the same instance."""
        logger1 = get_auth_logger()
        logger2 = get_auth_logger()
        
        assert logger1 is logger2
        assert isinstance(logger1, AuthenticationLogger)
    
    @patch('app.core.logging_config.logging.config.dictConfig')
    def test_setup_logging_configuration(self, mock_dict_config):
        """Test logging setup configuration."""
        from app.core.logging_config import setup_logging
        
        with patch('app.core.logging_config.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.ENVIRONMENT = "production"
            mock_get_settings.return_value = mock_settings
            
            setup_logging()
            
            # Verify dictConfig was called
            mock_dict_config.assert_called_once()
            
            # Get the config that was passed
            config = mock_dict_config.call_args[0][0]
            
            # Verify basic structure
            assert "version" in config
            assert "formatters" in config
            assert "handlers" in config
            assert "loggers" in config
            
            # Verify structured formatter is configured
            assert "structured" in config["formatters"]
            
            # Verify security logger is configured
            assert "security" in config["loggers"]
            assert "auth" in config["loggers"]
    
    def test_logging_with_correlation_ids(self):
        """Test that correlation IDs are properly included in logs."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="auth",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test with correlation ID",
            args=(),
            exc_info=None
        )
        record.module = "auth_module"
        record.funcName = "authenticate"
        record.request_id = "req_12345"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["request_id"] == "req_12345"
    
    def test_security_event_flagging(self):
        """Test that security events are properly flagged."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="security",
            level=logging.WARNING,
            pathname="/test/path.py",
            lineno=42,
            msg="Security event detected",
            args=(),
            exc_info=None
        )
        record.module = "security_module"
        record.funcName = "detect_threat"
        record.security_event = True
        record.event_type = "suspicious_activity"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["security_event"] is True
        assert log_data["event_type"] == "suspicious_activity"
    
    def test_performance_logging(self):
        """Test performance-related logging."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="performance",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Operation completed",
            args=(),
            exc_info=None
        )
        record.module = "performance_module"
        record.funcName = "measure_operation"
        record.response_time = 0.123
        record.operation = "token_validation"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["response_time"] == 0.123
        assert "operation" in log_data