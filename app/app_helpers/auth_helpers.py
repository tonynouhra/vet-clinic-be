"""
Authentication and authorization helpers for the Veterinary Clinic Backend.
Provides JWT token validation, user authentication, and role-based access control.
"""

from typing import Dict, Any, Optional, Callable
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
import logging

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.logging_config import get_auth_logger
from app.app_helpers.response_helpers import generate_request_id
from app.services.clerk_service import get_clerk_service

logger = logging.getLogger(__name__)
auth_logger = get_auth_logger()
settings = get_settings()

# HTTP Bearer token scheme
security = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
) -> Dict[str, Any]:
    """
    Verify JWT token using Clerk authentication and extract user information.
    
    Args:
        credentials: HTTP Bearer credentials from request
        request: FastAPI request object for context
        
    Returns:
        Dict[str, Any]: Decoded token payload with user information
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    request_id = generate_request_id()
    ip_address = None
    user_agent = None
    
    # Extract request context if available
    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
    
    try:
        clerk_service = get_clerk_service()
        
        # Use Clerk service to verify JWT token with proper signature validation
        token_data = await clerk_service.verify_jwt_token(
            credentials.credentials,
            request_id=request_id
        )
        
        # Return standardized user information
        result = {
            "user_id": token_data.get("user_id"),
            "clerk_id": token_data.get("clerk_id"),
            "email": token_data.get("email"),
            "role": token_data.get("role", "pet_owner"),
            "permissions": token_data.get("permissions", []),
            "exp": token_data.get("exp"),
            "session_id": token_data.get("session_id"),
            "request_id": request_id
        }
        
        return result
        
    except AuthenticationError as e:
        # Log authentication failure with context
        auth_logger.log_authentication_failure(
            reason=str(e),
            error_code=e.error_code,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        raise
    except Exception as e:
        # Log unexpected error
        auth_logger.log_authentication_failure(
            reason="Unexpected token verification error",
            error_code="TOKEN_VERIFICATION_ERROR",
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        logger.error(f"Token verification error: {e}", exc_info=True)
        raise AuthenticationError("Token verification failed")


async def get_current_user(token_data: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    """
    Get current authenticated user information.
    
    Args:
        token_data: Decoded token data from verify_token
        
    Returns:
        Dict[str, Any]: Current user information
        
    Example:
        @router.get("/profile")
        async def get_profile(
            current_user: Dict[str, Any] = Depends(get_current_user)
        ):
            return {"user_id": current_user["user_id"]}
    """
    return token_data


def require_role(required_role: str) -> Callable:
    """
    Create a dependency that requires a specific user role.
    
    Args:
        required_role: Required user role (e.g., "admin", "veterinarian")
        
    Returns:
        Callable: Dependency function that validates user role
        
    Example:
        @router.get("/admin/users")
        async def admin_list_users(
            current_user: Dict[str, Any] = Depends(require_role("admin"))
        ):
            return await list_all_users()
    """
    async def _require_role(
        current_user: Dict[str, Any] = Depends(get_current_user),
        request: Request = None
    ) -> Dict[str, Any]:
        user_role = current_user.get("role")
        
        if user_role != required_role:
            # Log authorization failure
            auth_logger.log_authorization_failure(
                user_id=current_user.get("user_id"),
                clerk_id=current_user.get("clerk_id"),
                required_role=required_role,
                user_role=user_role,
                endpoint=request.url.path if request else None,
                method=request.method if request else None,
                request_id=current_user.get("request_id"),
                ip_address=request.client.host if request and request.client else None
            )
            
            raise AuthorizationError(
                message=f"Access denied. Required role: {required_role}",
                required_role=required_role,
                details={"user_role": user_role}
            )
        
        return current_user
    
    return _require_role


def require_any_role(required_roles: list) -> Callable:
    """
    Create a dependency that requires any of the specified user roles.
    
    Args:
        required_roles: List of acceptable user roles
        
    Returns:
        Callable: Dependency function that validates user has one of the roles
        
    Example:
        @router.get("/staff/appointments")
        async def staff_appointments(
            current_user: Dict[str, Any] = Depends(
                require_any_role(["admin", "veterinarian", "receptionist"])
            )
        ):
            return await get_staff_appointments()
    """
    async def _require_any_role(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role")
        
        if user_role not in required_roles:
            raise AuthorizationError(
                message=f"Access denied. Required roles: {', '.join(required_roles)}",
                details={
                    "user_role": user_role,
                    "required_roles": required_roles
                }
            )
        
        return current_user
    
    return _require_any_role


def require_permission(required_permission: str) -> Callable:
    """
    Create a dependency that requires a specific permission.
    
    Args:
        required_permission: Required permission (e.g., "users:read", "pets:write")
        
    Returns:
        Callable: Dependency function that validates user permission
        
    Example:
        @router.delete("/pets/{pet_id}")
        async def delete_pet(
            pet_id: str,
            current_user: Dict[str, Any] = Depends(require_permission("pets:delete"))
        ):
            return await delete_pet_by_id(pet_id)
    """
    async def _require_permission(
        current_user: Dict[str, Any] = Depends(get_current_user),
        request: Request = None
    ) -> Dict[str, Any]:
        user_permissions = current_user.get("permissions", [])
        user_role = current_user.get("role")
        
        # Admin users have all permissions
        if user_role == "admin":
            return current_user
        
        # Check if user has the specific permission
        if required_permission not in user_permissions:
            # Log authorization failure
            auth_logger.log_authorization_failure(
                user_id=current_user.get("user_id"),
                clerk_id=current_user.get("clerk_id"),
                required_permission=required_permission,
                user_permissions=user_permissions,
                endpoint=request.url.path if request else None,
                method=request.method if request else None,
                request_id=current_user.get("request_id"),
                ip_address=request.client.host if request and request.client else None
            )
            
            raise AuthorizationError(
                message=f"Access denied. Required permission: {required_permission}",
                details={
                    "required_permission": required_permission,
                    "user_permissions": user_permissions
                }
            )
        
        return current_user
    
    return _require_permission


def is_owner_or_admin(resource_owner_id: str) -> Callable:
    """
    Create a dependency that allows access to resource owners or admins.
    
    Args:
        resource_owner_id: ID of the resource owner
        
    Returns:
        Callable: Dependency function that validates ownership or admin role
        
    Example:
        @router.get("/pets/{pet_id}")
        async def get_pet(
            pet_id: str,
            current_user: Dict[str, Any] = Depends(is_owner_or_admin(pet.owner_id))
        ):
            return pet
    """
    async def _is_owner_or_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_id = current_user.get("user_id")
        user_role = current_user.get("role")
        
        # Allow access if user is admin or resource owner
        if user_role == "admin" or user_id == resource_owner_id:
            return current_user
        
        raise AuthorizationError(
            message="Access denied. You can only access your own resources.",
            details={
                "user_id": user_id,
                "resource_owner_id": resource_owner_id
            }
        )
    
    return _is_owner_or_admin


def create_access_token(
    user_id: str,
    email: str,
    role: str = "pet_owner",
    clerk_id: Optional[str] = None,
    permissions: Optional[list] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token for development/testing purposes.
    
    Note: In production, tokens are created by Clerk's frontend SDK.
    This function is only used for development and testing scenarios.
    
    Args:
        user_id: User ID
        email: User email
        role: User role
        clerk_id: Clerk user ID
        permissions: User permissions
        expires_delta: Token expiration time
        
    Returns:
        str: Encoded JWT token
    """
    if settings.ENVIRONMENT == "production":
        logger.warning("create_access_token called in production - tokens should be created by Clerk")
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expire.timestamp(),
        "iat": datetime.utcnow().timestamp(),
        "type": "access_token",
        "iss": settings.CLERK_JWT_ISSUER
    }
    
    if clerk_id:
        payload["clerk_id"] = clerk_id
    
    if permissions:
        payload["permissions"] = permissions
    
    # For development, use simple HS256. In production, Clerk uses RS256
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def get_optional_user() -> Callable:
    """
    Create a dependency that optionally gets the current user.
    Returns None if no valid token is provided.
    
    Returns:
        Callable: Dependency function that returns user or None
        
    Example:
        @router.get("/public-pets")
        async def get_public_pets(
            current_user: Optional[Dict[str, Any]] = Depends(get_optional_user())
        ):
            # Show different data based on whether user is authenticated
            if current_user:
                return await get_personalized_pets(current_user["user_id"])
            else:
                return await get_public_pets()
    """
    async def _get_optional_user(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
    ) -> Optional[Dict[str, Any]]:
        if not credentials:
            return None
        
        try:
            return await verify_token(credentials)
        except (AuthenticationError, HTTPException):
            return None
    
    return _get_optional_user


# Role hierarchy for permission checking
ROLE_HIERARCHY = {
    "admin": ["admin", "veterinarian", "receptionist", "clinic_manager", "pet_owner"],
    "clinic_manager": ["clinic_manager", "receptionist", "pet_owner"],
    "veterinarian": ["veterinarian", "pet_owner"],
    "receptionist": ["receptionist", "pet_owner"],
    "pet_owner": ["pet_owner"]
}

# Permission mappings for roles
ROLE_PERMISSIONS = {
    "admin": ["*"],  # Admin has all permissions
    "clinic_manager": [
        "users:read", "users:write", "users:delete",
        "pets:read", "appointments:read", "appointments:write",
        "clinics:read", "clinics:write", "reports:read",
        "staff:read", "staff:write"
    ],
    "veterinarian": [
        "pets:read", "pets:write", "appointments:read", "appointments:write",
        "health_records:read", "health_records:write", "users:read",
        "prescriptions:read", "prescriptions:write"
    ],
    "receptionist": [
        "appointments:read", "appointments:write", "users:read", "pets:read",
        "scheduling:read", "scheduling:write"
    ],
    "pet_owner": [
        "pets:read", "pets:write", "appointments:read", "appointments:write",
        "profile:read", "profile:write", "health_records:read"
    ]
}


def has_role_access(user_role: str, required_role: str) -> bool:
    """
    Check if user role has access to required role level.
    
    Args:
        user_role: User's current role
        required_role: Required role for access
        
    Returns:
        bool: True if user has access, False otherwise
    """
    allowed_roles = ROLE_HIERARCHY.get(user_role, [])
    return required_role in allowed_roles


def get_user_permissions(user_role: str) -> list:
    """
    Get permissions for a user role.
    
    Args:
        user_role: User's role
        
    Returns:
        list: List of permissions for the role
    """
    return ROLE_PERMISSIONS.get(user_role, [])


def has_permission(user_role: str, required_permission: str) -> bool:
    """
    Check if user role has a specific permission.
    
    Args:
        user_role: User's role
        required_permission: Required permission
        
    Returns:
        bool: True if user has permission
    """
    permissions = get_user_permissions(user_role)
    return "*" in permissions or required_permission in permissions


def require_staff_access() -> Callable:
    """
    Create a dependency that requires staff-level access (admin, clinic_manager, veterinarian, receptionist).
    
    Returns:
        Callable: Dependency function that validates staff access
        
    Example:
        @router.get("/staff/dashboard")
        async def staff_dashboard(
            current_user: Dict[str, Any] = Depends(require_staff_access())
        ):
            return await get_staff_dashboard()
    """
    return require_any_role(["admin", "clinic_manager", "veterinarian", "receptionist"])


def require_management_access() -> Callable:
    """
    Create a dependency that requires management-level access (admin, clinic_manager).
    
    Returns:
        Callable: Dependency function that validates management access
        
    Example:
        @router.get("/management/reports")
        async def management_reports(
            current_user: Dict[str, Any] = Depends(require_management_access())
        ):
            return await get_management_reports()
    """
    return require_any_role(["admin", "clinic_manager"])


def require_medical_access() -> Callable:
    """
    Create a dependency that requires medical access (admin, veterinarian).
    
    Returns:
        Callable: Dependency function that validates medical access
        
    Example:
        @router.post("/medical/prescriptions")
        async def create_prescription(
            current_user: Dict[str, Any] = Depends(require_medical_access())
        ):
            return await create_prescription()
    """
    return require_any_role(["admin", "veterinarian"])


def require_multiple_permissions(required_permissions: list) -> Callable:
    """
    Create a dependency that requires multiple permissions.
    
    Args:
        required_permissions: List of required permissions (all must be present)
        
    Returns:
        Callable: Dependency function that validates multiple permissions
        
    Example:
        @router.post("/pets/{pet_id}/prescriptions")
        async def create_prescription(
            current_user: Dict[str, Any] = Depends(
                require_multiple_permissions(["pets:write", "prescriptions:write"])
            )
        ):
            return await create_prescription()
    """
    async def _require_multiple_permissions(
        current_user: Dict[str, Any] = Depends(get_current_user),
        request: Request = None
    ) -> Dict[str, Any]:
        user_permissions = current_user.get("permissions", [])
        user_role = current_user.get("role")
        
        # Admin users have all permissions
        if user_role == "admin":
            return current_user
        
        # Check if user has all required permissions
        missing_permissions = [
            perm for perm in required_permissions 
            if perm not in user_permissions
        ]
        
        if missing_permissions:
            # Log authorization failure
            auth_logger.log_authorization_failure(
                user_id=current_user.get("user_id"),
                clerk_id=current_user.get("clerk_id"),
                required_permissions=required_permissions,
                missing_permissions=missing_permissions,
                user_permissions=user_permissions,
                endpoint=request.url.path if request else None,
                method=request.method if request else None,
                request_id=current_user.get("request_id"),
                ip_address=request.client.host if request and request.client else None
            )
            
            raise AuthorizationError(
                message=f"Access denied. Missing permissions: {', '.join(missing_permissions)}",
                details={
                    "required_permissions": required_permissions,
                    "missing_permissions": missing_permissions,
                    "user_permissions": user_permissions
                }
            )
        
        return current_user
    
    return _require_multiple_permissions


def require_any_permission(required_permissions: list) -> Callable:
    """
    Create a dependency that requires any of the specified permissions.
    
    Args:
        required_permissions: List of permissions (at least one must be present)
        
    Returns:
        Callable: Dependency function that validates any permission
        
    Example:
        @router.get("/pets/{pet_id}")
        async def get_pet(
            current_user: Dict[str, Any] = Depends(
                require_any_permission(["pets:read", "pets:write"])
            )
        ):
            return await get_pet()
    """
    async def _require_any_permission(
        current_user: Dict[str, Any] = Depends(get_current_user),
        request: Request = None
    ) -> Dict[str, Any]:
        user_permissions = current_user.get("permissions", [])
        user_role = current_user.get("role")
        
        # Admin users have all permissions
        if user_role == "admin":
            return current_user
        
        # Check if user has any of the required permissions
        has_any_permission = any(
            perm in user_permissions for perm in required_permissions
        )
        
        if not has_any_permission:
            # Log authorization failure
            auth_logger.log_authorization_failure(
                user_id=current_user.get("user_id"),
                clerk_id=current_user.get("clerk_id"),
                required_permissions=required_permissions,
                user_permissions=user_permissions,
                endpoint=request.url.path if request else None,
                method=request.method if request else None,
                request_id=current_user.get("request_id"),
                ip_address=request.client.host if request and request.client else None
            )
            
            raise AuthorizationError(
                message=f"Access denied. Required permissions (any): {', '.join(required_permissions)}",
                details={
                    "required_permissions": required_permissions,
                    "user_permissions": user_permissions
                }
            )
        
        return current_user
    
    return _require_any_permission