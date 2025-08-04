"""
Authentication and authorization helpers for the Veterinary Clinic Backend.
Provides JWT token validation, user authentication, and role-based access control.
"""

from typing import Dict, Any, Optional, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
import logging

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)
settings = get_settings()

# HTTP Bearer token scheme
security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Verify JWT token and extract user information.
    
    Args:
        credentials: HTTP Bearer credentials from request
        
    Returns:
        Dict[str, Any]: Decoded token payload with user information
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise AuthenticationError("Token has expired")
        
        # Extract user information
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token: missing user ID")
        
        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role", "pet_owner"),
            "clerk_id": payload.get("clerk_id"),
            "permissions": payload.get("permissions", []),
            "exp": exp
        }
        
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise AuthenticationError("Invalid token")
    except Exception as e:
        logger.error(f"Token verification error: {e}")
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
    async def _require_role(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role")
        
        if user_role != required_role:
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
    async def _require_permission(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_permissions = current_user.get("permissions", [])
        
        if required_permission not in user_permissions:
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
    Create a JWT access token for a user.
    
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
        "type": "access_token"
    }
    
    if clerk_id:
        payload["clerk_id"] = clerk_id
    
    if permissions:
        payload["permissions"] = permissions
    
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
    "admin": ["admin", "veterinarian", "receptionist", "pet_owner"],
    "veterinarian": ["veterinarian", "pet_owner"],
    "receptionist": ["receptionist", "pet_owner"],
    "pet_owner": ["pet_owner"]
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