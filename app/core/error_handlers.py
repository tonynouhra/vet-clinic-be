"""
Enhanced error handling and fallback mechanisms for Clerk authentication.
Provides graceful degradation when external services are unavailable.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, TypeVar, Union
from functools import wraps
import logging
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError, 
    ExternalServiceError, 
    VetClinicException
)
from app.core.logging_config import get_auth_logger

settings = get_settings()
logger = logging.getLogger(__name__)
auth_logger = get_auth_logger()

T = TypeVar('T')


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for external service calls.
    Prevents cascading failures when external services are unavailable.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def _can_attempt_reset(self) -> bool:
        """Check if we can attempt to reset the circuit breaker."""
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_failure_time = None
    
    def _record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._can_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker is OPEN. Service unavailable for {self.recovery_timeout}s"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            if self.state == "HALF_OPEN":
                self.state = "OPEN"
            raise e


class RetryHandler:
    """
    Retry handler with exponential backoff for transient failures.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
        
        return delay
    
    async def execute(self, func: Callable, *args, **kwargs):
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    break
                
                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}"
                )
                await asyncio.sleep(delay)
        
        raise last_exception


class FallbackManager:
    """
    Manages fallback mechanisms when primary services are unavailable.
    """
    
    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.CLERK_CIRCUIT_BREAKER_THRESHOLD,
            recovery_timeout=settings.CLERK_CIRCUIT_BREAKER_TIMEOUT,
            expected_exception=(ExternalServiceError, AuthenticationError)
        )
        self.retry_handler = RetryHandler(
            max_retries=settings.CLERK_MAX_RETRIES,
            base_delay=settings.CLERK_RETRY_BASE_DELAY
        )
    
    async def execute_with_fallback(
        self,
        primary_func: Callable,
        fallback_func: Optional[Callable] = None,
        operation_name: str = "unknown",
        request_id: Optional[str] = None,
        *args,
        **kwargs
    ):
        """
        Execute primary function with fallback if it fails.
        
        Args:
            primary_func: Primary function to execute
            fallback_func: Fallback function if primary fails
            operation_name: Name of the operation for logging
            request_id: Request ID for tracking
            *args, **kwargs: Arguments for the functions
        
        Returns:
            Result from primary or fallback function
        
        Raises:
            ExternalServiceError: If both primary and fallback fail
        """
        try:
            # Try primary function with circuit breaker and retry
            return await self.circuit_breaker.call(
                self.retry_handler.execute,
                primary_func,
                *args,
                **kwargs
            )
        except (CircuitBreakerError, ExternalServiceError, AuthenticationError) as e:
            auth_logger.log_service_unavailable(
                service_name="Clerk",
                error_message=str(e),
                fallback_used=fallback_func is not None,
                request_id=request_id
            )
            
            if fallback_func:
                logger.warning(
                    f"Primary {operation_name} failed, using fallback: {e}"
                )
                try:
                    return await fallback_func(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(
                        f"Fallback {operation_name} also failed: {fallback_error}"
                    )
                    raise ExternalServiceError(
                        message=f"Both primary and fallback {operation_name} failed",
                        service_name="Clerk",
                        details={
                            "primary_error": str(e),
                            "fallback_error": str(fallback_error)
                        }
                    )
            else:
                raise ExternalServiceError(
                    message=f"Service unavailable: {operation_name}",
                    service_name="Clerk",
                    details={"error": str(e)}
                )


def with_error_handling(
    operation_name: str,
    log_errors: bool = True,
    raise_on_error: bool = True
):
    """
    Decorator for adding comprehensive error handling to functions.
    
    Args:
        operation_name: Name of the operation for logging
        log_errors: Whether to log errors
        raise_on_error: Whether to raise exceptions or return None
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, None]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Union[T, None]:
            start_time = time.time()
            request_id = kwargs.get('request_id')
            
            try:
                result = await func(*args, **kwargs)
                
                if log_errors:
                    response_time = time.time() - start_time
                    logger.debug(
                        f"{operation_name} completed successfully",
                        extra={
                            "operation": operation_name,
                            "response_time": response_time,
                            "request_id": request_id
                        }
                    )
                
                return result
                
            except AuthenticationError as e:
                if log_errors:
                    auth_logger.log_authentication_failure(
                        reason=str(e),
                        error_code=e.error_code,
                        request_id=request_id
                    )
                
                if raise_on_error:
                    raise
                return None
                
            except ExternalServiceError as e:
                if log_errors:
                    auth_logger.log_clerk_api_error(
                        operation=operation_name,
                        error_message=str(e),
                        request_id=request_id,
                        response_time=time.time() - start_time
                    )
                
                if raise_on_error:
                    raise
                return None
                
            except Exception as e:
                if log_errors:
                    logger.error(
                        f"Unexpected error in {operation_name}: {e}",
                        extra={
                            "operation": operation_name,
                            "error_type": type(e).__name__,
                            "request_id": request_id
                        },
                        exc_info=True
                    )
                
                if raise_on_error:
                    # Convert unexpected errors to VetClinicException
                    raise VetClinicException(
                        message=f"Operation {operation_name} failed",
                        error_code="OPERATION_ERROR",
                        details={"original_error": str(e)}
                    )
                return None
        
        return wrapper
    return decorator


@asynccontextmanager
async def error_context(
    operation_name: str,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    clerk_id: Optional[str] = None
):
    """
    Context manager for handling errors in authentication operations.
    
    Args:
        operation_name: Name of the operation
        request_id: Request ID for tracking
        user_id: User ID if available
        clerk_id: Clerk ID if available
    """
    start_time = time.time()
    
    try:
        yield
        
        # Log successful operation
        response_time = time.time() - start_time
        logger.debug(
            f"{operation_name} completed successfully",
            extra={
                "operation": operation_name,
                "response_time": response_time,
                "request_id": request_id,
                "user_id": user_id,
                "clerk_id": clerk_id
            }
        )
        
    except AuthenticationError as e:
        auth_logger.log_authentication_failure(
            reason=str(e),
            clerk_id=clerk_id,
            error_code=e.error_code,
            request_id=request_id
        )
        raise
        
    except ExternalServiceError as e:
        auth_logger.log_clerk_api_error(
            operation=operation_name,
            error_message=str(e),
            clerk_id=clerk_id,
            request_id=request_id,
            response_time=time.time() - start_time
        )
        raise
        
    except Exception as e:
        logger.error(
            f"Unexpected error in {operation_name}: {e}",
            extra={
                "operation": operation_name,
                "error_type": type(e).__name__,
                "request_id": request_id,
                "user_id": user_id,
                "clerk_id": clerk_id
            },
            exc_info=True
        )
        
        # Convert to appropriate exception type
        raise VetClinicException(
            message=f"Operation {operation_name} failed",
            error_code="OPERATION_ERROR",
            details={"original_error": str(e)}
        )


def handle_clerk_api_error(
    error: Exception,
    operation: str,
    clerk_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> ExternalServiceError:
    """
    Convert various error types to standardized ExternalServiceError.
    
    Args:
        error: The original error
        operation: Name of the operation that failed
        clerk_id: Clerk ID if available
        request_id: Request ID for tracking
    
    Returns:
        ExternalServiceError: Standardized error
    """
    import httpx
    
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        
        if status_code == 401:
            return ExternalServiceError(
                message="Clerk API authentication failed",
                service_name="Clerk",
                details={
                    "operation": operation,
                    "status_code": status_code,
                    "clerk_id": clerk_id
                }
            )
        elif status_code == 403:
            return ExternalServiceError(
                message="Clerk API access forbidden",
                service_name="Clerk",
                details={
                    "operation": operation,
                    "status_code": status_code,
                    "clerk_id": clerk_id
                }
            )
        elif status_code == 404:
            return AuthenticationError(
                message="User not found in Clerk",
                details={
                    "operation": operation,
                    "clerk_id": clerk_id
                }
            )
        elif status_code == 429:
            return ExternalServiceError(
                message="Clerk API rate limit exceeded",
                service_name="Clerk",
                details={
                    "operation": operation,
                    "status_code": status_code,
                    "retry_after": error.response.headers.get("Retry-After")
                }
            )
        elif 500 <= status_code < 600:
            return ExternalServiceError(
                message="Clerk API server error",
                service_name="Clerk",
                details={
                    "operation": operation,
                    "status_code": status_code
                }
            )
        else:
            return ExternalServiceError(
                message=f"Clerk API error: {status_code}",
                service_name="Clerk",
                details={
                    "operation": operation,
                    "status_code": status_code,
                    "response": error.response.text
                }
            )
    
    elif isinstance(error, httpx.TimeoutException):
        return ExternalServiceError(
            message="Clerk API timeout",
            service_name="Clerk",
            details={
                "operation": operation,
                "error_type": "timeout"
            }
        )
    
    elif isinstance(error, httpx.ConnectError):
        return ExternalServiceError(
            message="Cannot connect to Clerk API",
            service_name="Clerk",
            details={
                "operation": operation,
                "error_type": "connection_error"
            }
        )
    
    else:
        return ExternalServiceError(
            message=f"Clerk API operation failed: {operation}",
            service_name="Clerk",
            details={
                "operation": operation,
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        )


# Global fallback manager instance
fallback_manager = FallbackManager()


def get_fallback_manager() -> FallbackManager:
    """Get the global fallback manager instance."""
    return fallback_manager