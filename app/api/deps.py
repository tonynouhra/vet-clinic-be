"""
API dependencies and middleware.
"""
import logging
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import redis_client
from app.core.exceptions import AuthenticationError
from app.services.clerk_service import get_clerk_service
from app.services.user_sync_service import UserSyncService
from app.services.auth_cache_service import get_auth_cache_service
from app.models.user import User, UserRole
from app.schemas.clerk_schemas import ClerkUser

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer()


async def verify_clerk_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Verify JWT token with Clerk and extract user information.
    
    Args:
        credentials: JWT token credentials
        
    Returns:
        Dict containing user information from token
        
    Raises:
        HTTPException: If token verification fails
    """
    from app.services.monitoring_service import get_monitoring_service
    import time
    
    monitoring_service = get_monitoring_service()
    start_time = time.time()
    
    try:
        clerk_service = get_clerk_service()
        token_data = await clerk_service.verify_jwt_token(credentials.credentials)
        
        # Record successful authentication
        duration = time.time() - start_time
        monitoring_service.record_authentication_attempt(success=True)
        monitoring_service.record_performance_metric("token_validation", duration)
        
        return token_data
    except AuthenticationError as e:
        # Record failed authentication with error type
        duration = time.time() - start_time
        monitoring_service.record_authentication_attempt(success=False, error_type="authentication_error")
        monitoring_service.record_token_validation_error("authentication_failed")
        monitoring_service.record_performance_metric("token_validation", duration)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # Record failed authentication with generic error
        duration = time.time() - start_time
        monitoring_service.record_authentication_attempt(success=False, error_type="unexpected_error")
        monitoring_service.record_token_validation_error("unexpected_error")
        monitoring_service.record_performance_metric("token_validation", duration)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def sync_clerk_user(
    token_data: Dict[str, Any] = Depends(verify_clerk_token),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Ensure user exists in local database and sync with Clerk data.
    Uses caching for performance optimization.
    
    Args:
        token_data: Verified token data from Clerk
        db: Database session
        
    Returns:
        User: Local user object
        
    Raises:
        HTTPException: If user sync fails
    """
    from app.services.monitoring_service import get_monitoring_service
    import time
    
    monitoring_service = get_monitoring_service()
    start_time = time.time()
    
    try:
        clerk_service = get_clerk_service()
        user_sync_service = UserSyncService(db)
        cache_service = get_auth_cache_service()
        
        clerk_id = token_data["clerk_id"]
        
        # Try to get user from cache first
        cached_user_data = await cache_service.get_cached_user_data(clerk_id)
        if cached_user_data:
            # Get local user by ID from cached data
            local_user = await user_sync_service.get_user_by_clerk_id(clerk_id)
            if local_user and local_user.is_active:
                logger.debug("Using cached user data for authentication")
                duration = time.time() - start_time
                monitoring_service.record_performance_metric("user_sync", duration)
                return local_user
        
        # Get full user data from Clerk (this may also use cache)
        clerk_user = await clerk_service.get_user_by_clerk_id(clerk_id)
        
        # Sync user data
        sync_response = await user_sync_service.sync_user_data(clerk_user)
        
        if not sync_response.success:
            duration = time.time() - start_time
            monitoring_service.record_performance_metric("user_sync", duration)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"User synchronization failed: {sync_response.message}"
            )
        
        # Get the local user
        local_user = await user_sync_service.get_user_by_clerk_id(clerk_id)
        if not local_user:
            duration = time.time() - start_time
            monitoring_service.record_performance_metric("user_sync", duration)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User not found after synchronization"
            )
        
        duration = time.time() - start_time
        monitoring_service.record_performance_metric("user_sync", duration)
        return local_user
        
    except HTTPException:
        duration = time.time() - start_time
        monitoring_service.record_performance_metric("user_sync", duration)
        raise
    except Exception:
        duration = time.time() - start_time
        monitoring_service.record_performance_metric("user_sync", duration)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User synchronization failed"
        )


async def get_current_user(
    user: User = Depends(sync_clerk_user)
) -> User:
    """
    Get current authenticated user from JWT token with Clerk integration.
    
    Args:
        user: Synchronized user from Clerk
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (not disabled).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is disabled
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_role(required_role: UserRole):
    """
    Dependency factory for role-based access control with Clerk integration.
    
    Args:
        required_role: Required user role
        
    Returns:
        function: Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != required_role:
            from app.services.monitoring_service import get_monitoring_service
            monitoring_service = get_monitoring_service()
            monitoring_service.record_authorization_failure("insufficient_role")
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role.value}, current role: {current_user.role.value}"
            )
        return current_user
    
    return role_checker


def require_any_role(required_roles: list[UserRole]):
    """
    Dependency factory for role-based access control allowing multiple roles.
    
    Args:
        required_roles: List of acceptable user roles
        
    Returns:
        function: Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in required_roles:
            from app.services.monitoring_service import get_monitoring_service
            monitoring_service = get_monitoring_service()
            monitoring_service.record_authorization_failure("insufficient_role")
            
            role_names = [role.value for role in required_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(role_names)}, current role: {current_user.role.value}"
            )
        return current_user
    
    return role_checker


def require_permission(required_permission: str):
    """
    Dependency factory for permission-based access control.
    
    Args:
        required_permission: Required permission
        
    Returns:
        function: Dependency function
    """
    async def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.has_permission(required_permission):
            from app.services.monitoring_service import get_monitoring_service
            monitoring_service = get_monitoring_service()
            monitoring_service.record_authorization_failure("insufficient_permission")
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required permission: {required_permission}"
            )
        return current_user
    
    return permission_checker


def require_staff_role():
    """
    Dependency that requires user to be staff (admin, veterinarian, receptionist, or clinic manager).
    
    Returns:
        function: Dependency function
    """
    return require_any_role([
        UserRole.ADMIN,
        UserRole.VETERINARIAN,
        UserRole.RECEPTIONIST,
        UserRole.CLINIC_MANAGER
    ])


def require_admin_role():
    """
    Dependency that requires admin role.
    
    Returns:
        function: Dependency function
    """
    return require_role(UserRole.ADMIN)


def require_veterinarian_role():
    """
    Dependency that requires veterinarian role.
    
    Returns:
        function: Dependency function
    """
    return require_role(UserRole.VETERINARIAN)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    Used for endpoints that work with or without authentication.
    
    Args:
        credentials: Optional JWT token credentials
        db: Database session
        
    Returns:
        User or None: Current user if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        # Verify token
        clerk_service = get_clerk_service()
        token_data = await clerk_service.verify_jwt_token(credentials.credentials)
        
        # Sync user
        user_sync_service = UserSyncService(db)
        clerk_user = await clerk_service.get_user_by_clerk_id(token_data["clerk_id"])
        
        sync_response = await user_sync_service.sync_user_data(clerk_user)
        if not sync_response.success:
            return None
        
        local_user = await user_sync_service.get_user_by_clerk_id(token_data["clerk_id"])
        return local_user if local_user and local_user.is_active else None
        
    except Exception:
        # If any error occurs, just return None (no authentication)
        return None


async def get_redis_client():
    """
    Get Redis client dependency.
    
    Returns:
        RedisClient: Redis client instance
    """
    return redis_client


class RateLimiter:
    """Rate limiting dependency."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def __call__(
        self,
        request,
        redis_client=Depends(get_redis_client)
    ):
        """
        Check rate limit for the request.
        
        Args:
            request: FastAPI request object
            redis_client: Redis client
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Get client IP or user ID
        # 2. Check current request count in Redis
        # 3. Increment counter or raise rate limit error
        
        # For now, just pass through
        return


# Common rate limiters
rate_limit_strict = RateLimiter(max_requests=10, window_seconds=60)  # 10 requests per minute
rate_limit_moderate = RateLimiter(max_requests=100, window_seconds=3600)  # 100 requests per hour
rate_limit_lenient = RateLimiter(max_requests=1000, window_seconds=3600)  # 1000 requests per hour