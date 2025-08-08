"""
Logging configuration for the Veterinary Clinic Backend.
Provides structured logging for authentication events, errors, and security monitoring.
"""

import logging
import logging.config
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs for better parsing and analysis.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        extra_fields = [
            'user_id', 'clerk_id', 'request_id', 'event_type', 'ip_address', 
            'user_agent', 'endpoint', 'method', 'status_code', 'response_time', 
            'error_code', 'security_event', 'operation'
        ]
        
        for field in extra_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_entry, ensure_ascii=False)


class AuthenticationLogger:
    """
    Specialized logger for authentication events and security monitoring.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("auth")
        self.security_logger = logging.getLogger("security")
    
    def log_authentication_success(
        self,
        user_id: str,
        clerk_id: str,
        email: Optional[str] = None,
        role: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log successful authentication event."""
        self.logger.info(
            "User authentication successful",
            extra={
                "event_type": "auth_success",
                "user_id": user_id,
                "clerk_id": clerk_id,
                "email": email,
                "role": role,
                "request_id": request_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "security_event": True
            }
        )
    
    def log_authentication_failure(
        self,
        reason: str,
        clerk_id: Optional[str] = None,
        email: Optional[str] = None,
        error_code: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        token_info: Optional[Dict[str, Any]] = None
    ):
        """Log failed authentication attempt."""
        extra_data = {
            "event_type": "auth_failure",
            "reason": reason,
            "clerk_id": clerk_id,
            "email": email,
            "error_code": error_code,
            "request_id": request_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "security_event": True
        }
        
        if token_info:
            extra_data["token_info"] = token_info
        
        self.security_logger.warning(
            f"Authentication failed: {reason}",
            extra=extra_data
        )
    
    def log_authorization_failure(
        self,
        user_id: str,
        clerk_id: str,
        required_role: Optional[str] = None,
        required_permission: Optional[str] = None,
        user_role: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log authorization failure."""
        self.security_logger.warning(
            "Authorization denied",
            extra={
                "event_type": "auth_denied",
                "user_id": user_id,
                "clerk_id": clerk_id,
                "required_role": required_role,
                "required_permission": required_permission,
                "user_role": user_role,
                "endpoint": endpoint,
                "method": method,
                "request_id": request_id,
                "ip_address": ip_address,
                "security_event": True
            }
        )
    
    def log_token_validation_error(
        self,
        error_type: str,
        error_message: str,
        token_info: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log JWT token validation errors."""
        extra_data = {
            "event_type": "token_validation_error",
            "error_type": error_type,
            "error_message": error_message,
            "request_id": request_id,
            "ip_address": ip_address,
            "security_event": True
        }
        
        if token_info:
            extra_data["token_info"] = token_info
        
        self.security_logger.error(
            f"Token validation failed: {error_type}",
            extra=extra_data
        )
    
    def log_clerk_api_error(
        self,
        operation: str,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        clerk_id: Optional[str] = None,
        request_id: Optional[str] = None,
        response_time: Optional[float] = None
    ):
        """Log Clerk API errors."""
        self.logger.error(
            f"Clerk API error during {operation}",
            extra={
                "event_type": "clerk_api_error",
                "operation": operation,
                "status_code": status_code,
                "error_message": error_message,
                "clerk_id": clerk_id,
                "request_id": request_id,
                "response_time": response_time
            }
        )
    
    def log_webhook_event(
        self,
        event_type: str,
        clerk_id: str,
        success: bool,
        error_message: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log webhook processing events."""
        level = logging.INFO if success else logging.ERROR
        message = f"Webhook {event_type} processed {'successfully' if success else 'with error'}"
        
        extra_data = {
            "event_type": "webhook_processing",
            "webhook_event_type": event_type,
            "clerk_id": clerk_id,
            "success": success,
            "request_id": request_id
        }
        
        if error_message:
            extra_data["error_message"] = error_message
        
        self.logger.log(level, message, extra=extra_data)
    
    def log_suspicious_activity(
        self,
        activity_type: str,
        description: str,
        user_id: Optional[str] = None,
        clerk_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log suspicious security activities."""
        extra_data = {
            "event_type": "suspicious_activity",
            "activity_type": activity_type,
            "description": description,
            "user_id": user_id,
            "clerk_id": clerk_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": request_id,
            "security_event": True
        }
        
        if additional_data:
            extra_data.update(additional_data)
        
        self.security_logger.critical(
            f"Suspicious activity detected: {activity_type}",
            extra=extra_data
        )
    
    def log_service_unavailable(
        self,
        service_name: str,
        error_message: str,
        fallback_used: bool = False,
        request_id: Optional[str] = None
    ):
        """Log external service unavailability."""
        self.logger.error(
            f"Service {service_name} unavailable",
            extra={
                "event_type": "service_unavailable",
                "service_name": service_name,
                "error_message": error_message,
                "fallback_used": fallback_used,
                "request_id": request_id
            }
        )


def setup_logging():
    """
    Configure application logging with structured output and appropriate levels.
    """
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Determine log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": StructuredFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "structured" if settings.ENVIRONMENT == "production" else "simple",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "structured",
                "filename": "logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "security_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": logging.WARNING,
                "formatter": "structured",
                "filename": "logs/security.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": log_level,
                "handlers": ["console", "file"]
            },
            "auth": {
                "level": logging.INFO,
                "handlers": ["console", "file"],
                "propagate": False
            },
            "security": {
                "level": logging.WARNING,
                "handlers": ["console", "security_file"],
                "propagate": False
            },
            "uvicorn": {
                "level": logging.INFO,
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": logging.INFO,
                "handlers": ["console"],
                "propagate": False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)


# Global authentication logger instance
auth_logger = AuthenticationLogger()


def get_auth_logger() -> AuthenticationLogger:
    """Get the global authentication logger instance."""
    return auth_logger