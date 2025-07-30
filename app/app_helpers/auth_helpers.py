"""
Authentication and authorization helper functions.
"""
from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User, UserRole

security = HTTPBearer()


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


async def verify_permissions(
    user: User,
    required_permissions: list[str]
) -> bool:
    """
    Verify if user has required permissions.
    
    Args:
        user: Current user
        required_permissions: List of required permissions
        
    Returns:
        bool: True if user has all required permissions
    """
    # TODO: Implement permission checking logic
    # This would check user roles and permissions
    return True


def require_role(required_role: UserRole):
    """
    Decorator to require specific user role for endpoint access.
    
    Args:
        required_role: Required user role
        
    Returns:
        Dependency function for FastAPI
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role.value}"
            )
        return current_user
    
    return role_checker


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