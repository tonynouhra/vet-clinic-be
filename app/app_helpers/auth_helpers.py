"""
Enhanced authentication and authorization helper functions with version-aware support.

This module provides comprehensive authentication and authorization utilities that work
across all API versions, including role-based access control, permission checking,
and user context management.
"""
from typing import Optional, List, Dict, Any, Callable, Union
from functools import wraps
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from enum import Enum

from app.core.database import get_db
from app.models import User, UserRole, user_roles

security = HTTPBearer()


class Permission(str, Enum):
    """System permissions enumeration."""
    # User management
    CREATE_USER = "create_user"
    READ_USER = "read_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    
    # Pet management
    CREATE_PET = "create_pet"
    READ_PET = "read_pet"
    UPDATE_PET = "update_pet"
    DELETE_PET = "delete_pet"
    
    # Appointment management
    CREATE_APPOINTMENT = "create_appointment"
    READ_APPOINTMENT = "read_appointment"
    UPDATE_APPOINTMENT = "update_appointment"
    DELETE_APPOINTMENT = "delete_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    
    # Medical records
    CREATE_MEDICAL_RECORD = "create_medical_record"
    READ_MEDICAL_RECORD = "read_medical_record"
    UPDATE_MEDICAL_RECORD = "update_medical_record"
    DELETE_MEDICAL_RECORD = "delete_medical_record"
    
    # System administration
    MANAGE_CLINIC = "manage_clinic"
    MANAGE_SYSTEM = "manage_system"
    VIEW_REPORTS = "view_reports"
    MANAGE_BILLING = "manage_billing"


# Role-based permission mapping
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.PET_OWNER: [
        Permission.READ_USER,
        Permission.UPDATE_USER,
        Permission.CREATE_PET,
        Permission.READ_PET,
        Permission.UPDATE_PET,
        Permission.CREATE_APPOINTMENT,
        Permission.READ_APPOINTMENT,
        Permission.UPDATE_APPOINTMENT,
        Permission.CANCEL_APPOINTMENT,
        Permission.READ_MEDICAL_RECORD,
    ],
    UserRole.VETERINARIAN: [
        Permission.READ_USER,
        Permission.UPDATE_USER,
        Permission.READ_PET,
        Permission.UPDATE_PET,
        Permission.READ_APPOINTMENT,
        Permission.UPDATE_APPOINTMENT,
        Permission.CANCEL_APPOINTMENT,
        Permission.CREATE_MEDICAL_RECORD,
        Permission.READ_MEDICAL_RECORD,
        Permission.UPDATE_MEDICAL_RECORD,
        Permission.DELETE_MEDICAL_RECORD,
    ],
    UserRole.CLINIC_ADMIN: [
        Permission.CREATE_USER,
        Permission.READ_USER,
        Permission.UPDATE_USER,
        Permission.DELETE_USER,
        Permission.CREATE_PET,
        Permission.READ_PET,
        Permission.UPDATE_PET,
        Permission.DELETE_PET,
        Permission.CREATE_APPOINTMENT,
        Permission.READ_APPOINTMENT,
        Permission.UPDATE_APPOINTMENT,
        Permission.DELETE_APPOINTMENT,
        Permission.CANCEL_APPOINTMENT,
        Permission.CREATE_MEDICAL_RECORD,
        Permission.READ_MEDICAL_RECORD,
        Permission.UPDATE_MEDICAL_RECORD,
        Permission.DELETE_MEDICAL_RECORD,
        Permission.MANAGE_CLINIC,
        Permission.VIEW_REPORTS,
        Permission.MANAGE_BILLING,
    ],
    UserRole.SYSTEM_ADMIN: [
        # System admins have all permissions
        *[perm for perm in Permission],
    ],
}


class UserContext:
    """Enhanced user context for version-aware operations."""
    
    def __init__(
        self, 
        user: User, 
        roles: List[UserRole], 
        permissions: List[Permission],
        api_version: Optional[str] = None,
        request_metadata: Optional[Dict[str, Any]] = None
    ):
        self.user = user
        self.roles = roles
        self.permissions = permissions
        self.api_version = api_version
        self.request_metadata = request_metadata or {}
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions
    
    def has_any_role(self, roles: List[UserRole]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if user has all specified permissions."""
        return all(permission in self.permissions for permission in permissions)
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(permission in self.permissions for permission in permissions)
    
    def is_resource_owner(self, resource_user_id: str) -> bool:
        """Check if user owns a specific resource."""
        return str(self.user.id) == str(resource_user_id)
    
    def can_access_resource(self, resource_user_id: str, required_permission: Permission) -> bool:
        """Check if user can access a resource (either owns it or has permission)."""
        return self.is_resource_owner(resource_user_id) or self.has_permission(required_permission)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: JWT token from Authorization header
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    # TODO: Implement JWT token validation with Clerk
    # This is a placeholder implementation
    token = credentials.credentials
    
    # Validate token and extract user info
    # clerk_user_id = validate_jwt_token(token)
    
    # For now, return a placeholder
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authentication not yet implemented"
    )


async def get_user_roles(user_id: str, db: AsyncSession) -> List[UserRole]:
    """
    Get all roles for a specific user.
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        List[UserRole]: List of user roles
    """
    result = await db.execute(
        select(user_roles.c.role).where(user_roles.c.user_id == user_id)
    )
    return [row[0] for row in result.fetchall()]


async def get_user_permissions(roles: List[UserRole]) -> List[Permission]:
    """
    Get all permissions for given roles.
    
    Args:
        roles: List of user roles
        
    Returns:
        List[Permission]: List of permissions
    """
    permissions = set()
    for role in roles:
        if role in ROLE_PERMISSIONS:
            permissions.update(ROLE_PERMISSIONS[role])
    return list(permissions)


async def get_user_context(
    user: User,
    db: AsyncSession,
    api_version: Optional[str] = None,
    request: Optional[Request] = None
) -> UserContext:
    """
    Create enhanced user context with roles, permissions, and metadata.
    
    Args:
        user: Authenticated user
        db: Database session
        api_version: API version being used
        request: FastAPI request object for metadata
        
    Returns:
        UserContext: Enhanced user context
    """
    # Get user roles
    roles = await get_user_roles(str(user.id), db)
    
    # Get user permissions based on roles
    permissions = await get_user_permissions(roles)
    
    # Extract request metadata
    request_metadata = {}
    if request:
        request_metadata = {
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "method": request.method,
            "url": str(request.url),
        }
    
    return UserContext(
        user=user,
        roles=roles,
        permissions=permissions,
        api_version=api_version,
        request_metadata=request_metadata
    )


async def verify_permissions(
    user_context: UserContext,
    required_permissions: List[Permission]
) -> bool:
    """
    Verify if user has required permissions.
    
    Args:
        user_context: User context with roles and permissions
        required_permissions: List of required permissions
        
    Returns:
        bool: True if user has all required permissions
    """
    return user_context.has_all_permissions(required_permissions)


def require_role(required_role: Union[UserRole, List[UserRole]]):
    """
    Enhanced decorator to require specific user role(s) for endpoint access.
    
    Args:
        required_role: Required user role or list of roles (any of which grants access)
        
    Returns:
        Dependency function for FastAPI
    """
    required_roles = [required_role] if isinstance(required_role, UserRole) else required_role
    
    async def role_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> UserContext:
        user_context = await get_user_context(current_user, db)
        
        if not user_context.has_any_role(required_roles):
            role_names = [role.value for role in required_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(role_names)}"
            )
        return user_context
    
    return role_checker


def require_permission(required_permission: Union[Permission, List[Permission]]):
    """
    Decorator to require specific permission(s) for endpoint access.
    
    Args:
        required_permission: Required permission or list of permissions
        
    Returns:
        Dependency function for FastAPI
    """
    required_permissions = [required_permission] if isinstance(required_permission, Permission) else required_permission
    
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> UserContext:
        user_context = await get_user_context(current_user, db)
        
        if not user_context.has_all_permissions(required_permissions):
            permission_names = [perm.value for perm in required_permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required permission(s): {', '.join(permission_names)}"
            )
        return user_context
    
    return permission_checker


def require_any_permission(required_permissions: List[Permission]):
    """
    Decorator to require any of the specified permissions for endpoint access.
    
    Args:
        required_permissions: List of permissions (any of which grants access)
        
    Returns:
        Dependency function for FastAPI
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> UserContext:
        user_context = await get_user_context(current_user, db)
        
        if not user_context.has_any_permission(required_permissions):
            permission_names = [perm.value for perm in required_permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required any of: {', '.join(permission_names)}"
            )
        return user_context
    
    return permission_checker


def require_resource_ownership_or_permission(
    resource_user_id_param: str,
    fallback_permission: Permission
):
    """
    Decorator to require resource ownership OR specific permission.
    
    This allows users to access their own resources, or users with specific
    permissions to access any resource.
    
    Args:
        resource_user_id_param: Name of the parameter containing the resource owner's user ID
        fallback_permission: Permission required if user doesn't own the resource
        
    Returns:
        Dependency function for FastAPI
    """
    async def ownership_or_permission_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> UserContext:
        user_context = await get_user_context(current_user, db, request=request)
        
        # Get resource owner ID from path parameters
        path_params = request.path_params
        resource_user_id = path_params.get(resource_user_id_param)
        
        if not resource_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required parameter: {resource_user_id_param}"
            )
        
        # Check if user owns the resource or has the required permission
        if not user_context.can_access_resource(resource_user_id, fallback_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access your own resources or need appropriate permissions."
            )
        
        return user_context
    
    return ownership_or_permission_checker


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    Useful for endpoints that work for both authenticated and anonymous users.
    
    Args:
        credentials: Optional JWT token
        db: Database session
        
    Returns:
        Optional[User]: Current user if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_optional_user_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
    api_version: Optional[str] = None,
    request: Optional[Request] = None
) -> Optional[UserContext]:
    """
    Get current user context if authenticated, otherwise return None.
    
    Args:
        credentials: Optional JWT token
        db: Database session
        api_version: API version being used
        request: FastAPI request object
        
    Returns:
        Optional[UserContext]: Current user context if authenticated, None otherwise
    """
    user = await get_optional_user(credentials, db)
    if not user:
        return None
    
    return await get_user_context(user, db, api_version, request)


def create_version_aware_auth_dependency(api_version: str):
    """
    Create a version-aware authentication dependency.
    
    This allows authentication helpers to be aware of which API version
    is being used, enabling version-specific behavior when needed.
    
    Args:
        api_version: API version (e.g., "v1", "v2")
        
    Returns:
        Dependency function that provides version-aware user context
    """
    async def version_aware_auth(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> UserContext:
        return await get_user_context(current_user, db, api_version, request)
    
    return version_aware_auth


def create_version_aware_optional_auth_dependency(api_version: str):
    """
    Create a version-aware optional authentication dependency.
    
    Args:
        api_version: API version (e.g., "v1", "v2")
        
    Returns:
        Dependency function that provides optional version-aware user context
    """
    async def version_aware_optional_auth(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db: AsyncSession = Depends(get_db)
    ) -> Optional[UserContext]:
        return await get_optional_user_context(credentials, db, api_version, request)
    
    return version_aware_optional_auth


# Convenience functions for common authorization patterns
def admin_required():
    """Require system admin role."""
    return require_role(UserRole.SYSTEM_ADMIN)


def clinic_admin_or_system_admin_required():
    """Require clinic admin or system admin role."""
    return require_role([UserRole.CLINIC_ADMIN, UserRole.SYSTEM_ADMIN])


def veterinarian_or_admin_required():
    """Require veterinarian, clinic admin, or system admin role."""
    return require_role([UserRole.VETERINARIAN, UserRole.CLINIC_ADMIN, UserRole.SYSTEM_ADMIN])


def authenticated_user_required():
    """Require any authenticated user."""
    return require_role([UserRole.PET_OWNER, UserRole.VETERINARIAN, UserRole.CLINIC_ADMIN, UserRole.SYSTEM_ADMIN])


# Utility functions for controllers
def check_resource_access(
    user_context: UserContext,
    resource_owner_id: str,
    required_permission: Permission
) -> bool:
    """
    Check if user can access a specific resource.
    
    Args:
        user_context: Current user context
        resource_owner_id: ID of the resource owner
        required_permission: Permission required for non-owners
        
    Returns:
        bool: True if access is allowed
    """
    return user_context.can_access_resource(resource_owner_id, required_permission)


def ensure_resource_access(
    user_context: UserContext,
    resource_owner_id: str,
    required_permission: Permission,
    resource_type: str = "resource"
) -> None:
    """
    Ensure user can access a specific resource, raise exception if not.
    
    Args:
        user_context: Current user context
        resource_owner_id: ID of the resource owner
        required_permission: Permission required for non-owners
        resource_type: Type of resource for error message
        
    Raises:
        HTTPException: If access is denied
    """
    if not check_resource_access(user_context, resource_owner_id, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. You can only access your own {resource_type} or need {required_permission.value} permission."
        )