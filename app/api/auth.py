"""
Authentication endpoints for the Veterinary Clinic Backend.
Includes development endpoints for testing with Postman and Clerk integration,
plus comprehensive authentication endpoints using the new controller pattern.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional
import logging
import jwt
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.clerk_service import get_clerk_service, ClerkService
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import (
    AuthenticationError, 
    ValidationError, 
    ConflictError, 
    BusinessLogicError
)
from app.api.deps import get_current_user, get_optional_user
from app.models.user import User, UserRole
from app.auth.controller import AuthController
from app.app_helpers.dependency_helpers import get_controller
from app.app_helpers.auth_helpers import (
    get_current_user as get_current_user_helper,
    require_role,
    require_staff_access,
    require_management_access,
    get_user_permissions,
    ROLE_PERMISSIONS
)
from app.api.schemas.v1.auth import (
    LoginRequestV1,
    RegisterRequestV1,
    PasswordResetRequestV1,
    PasswordResetConfirmV1,
    ChangePasswordV1,
    RefreshTokenRequestV1,
    LogoutRequestV1,
    PermissionCheckV1,
    UserProfileV1,
    LoginResponseModelV1,
    RegisterResponseModelV1,
    TokenResponseModelV1,
    ActiveSessionsResponseModelV1,
    PermissionResponseModelV1,
    RolePermissionsModelV1,
    AuthSuccessResponseV1
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


class DevLoginRequest(BaseModel):
    """Request model for development login."""
    email: EmailStr
    password: str = "dev-password"  # Default password for development


class DevLoginResponse(BaseModel):
    """Response model for development login."""
    token: str
    user: Dict[str, Any]
    message: str


async def get_current_user_simple(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Simple token validation for development testing.
    Validates JWT tokens created by the dev-login endpoint.
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"]
        )
        
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role"),
            "exp": payload.get("exp")
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.post("/dev-login", response_model=DevLoginResponse)
async def dev_login(
    request: DevLoginRequest,
    clerk_service: ClerkService = Depends(get_clerk_service)
) -> DevLoginResponse:
    """
    Development-only login endpoint for Postman testing.
    
    This endpoint allows you to get a JWT token for testing without a frontend.
    Only available in development environment.
    
    Usage in Postman:
    1. POST to /api/v1/auth/dev-login
    2. Body: {"email": "user@example.com", "password": "dev-password"}
    3. Copy the returned token
    4. Use token in Authorization header: Bearer <token>
    
    Args:
        request: Login request with email and password
        
    Returns:
        DevLoginResponse with JWT token and user info
        
    Raises:
        HTTPException: If login fails or not in development mode
    """
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in production"
        )
    
    try:
        # For immediate testing, create a mock token without requiring Clerk users
        # This allows you to test right away with Postman
        
        # Mock user data based on email
        mock_users = {
            "admin@vetclinic.com": {"role": "admin", "first_name": "Admin", "last_name": "User"},
            "vet@vetclinic.com": {"role": "veterinarian", "first_name": "Dr.", "last_name": "Smith"},
            "receptionist@vetclinic.com": {"role": "receptionist", "first_name": "Jane", "last_name": "Doe"},
            "owner@example.com": {"role": "pet_owner", "first_name": "John", "last_name": "Owner"}
        }
        
        user_data = mock_users.get(request.email)
        if not user_data:
            raise AuthenticationError("User not found. Use one of the test emails from /auth/dev-users")
        
        # Create JWT token for testing
        token_payload = {
            "sub": f"user_{request.email.split('@')[0]}",
            "email": request.email,
            "role": user_data["role"],
            "iat": int(datetime.utcnow().timestamp()),
            "exp": int((datetime.utcnow() + timedelta(hours=24)).timestamp()),  # 24 hour token
            "iss": "vet-clinic-dev"
        }
        
        token = jwt.encode(token_payload, settings.JWT_SECRET_KEY, algorithm="HS256")
        
        session_data = {
            "token": token,
            "user": {
                "id": f"user_{request.email.split('@')[0]}",
                "email": request.email,
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "role": user_data["role"]
            }
        }
        
        return DevLoginResponse(
            token=session_data["token"],
            user=session_data["user"],
            message="Development token generated successfully. Use this token in Authorization header: Bearer <token>"
        )
        
    except AuthenticationError as e:
        logger.warning(f"Development login failed for {request.email}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {e.message}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during development login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.get("/dev-users")
async def list_dev_users(
    clerk_service: ClerkService = Depends(get_clerk_service)
):
    """
    Development endpoint to list available test users.
    Only available in development environment.
    
    Returns:
        List of available test users for development
    """
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in production"
        )
    
    # Return some example users for development
    return {
        "message": "Available test users for development",
        "users": [
            {
                "email": "admin@vetclinic.com",
                "role": "admin",
                "description": "System administrator with full access"
            },
            {
                "email": "vet@vetclinic.com", 
                "role": "veterinarian",
                "description": "Veterinarian with medical access"
            },
            {
                "email": "receptionist@vetclinic.com",
                "role": "receptionist", 
                "description": "Front desk staff with appointment access"
            },
            {
                "email": "owner@example.com",
                "role": "pet_owner",
                "description": "Pet owner with limited access"
            }
        ],
        "note": "Use any of these emails with password 'dev-password' in /auth/dev-login"
    }


@router.get("/test-token")
async def test_token_endpoint(
    current_user: User = Depends(get_current_user)
):
    """
    Test endpoint to verify Clerk token authentication is working.
    This endpoint requires a valid Clerk JWT token.
    
    Usage:
    1. Get token from Clerk authentication or /auth/dev-login
    2. Add to Authorization header: Bearer <token>
    3. Call this endpoint to verify token works
    
    Returns:
        Current user information from Clerk authentication
    """
    return {
        "message": "Clerk authentication successful!",
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "role": current_user.role.value,
            "is_active": current_user.is_active,
            "clerk_id": current_user.clerk_id
        },
        "authentication_method": "clerk",
        "instructions": [
            "Your Clerk token is working correctly",
            "You can now use this token to access protected endpoints",
            "Add 'Authorization: Bearer <your-token>' to all API requests"
        ]
    }


@router.get("/test-token-dev")
async def test_dev_token_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user_simple)
):
    """
    Test endpoint to verify development token authentication is working.
    This endpoint requires a valid development JWT token from /auth/dev-login.
    
    Usage:
    1. Get token from /auth/dev-login
    2. Add to Authorization header: Bearer <token>
    3. Call this endpoint to verify token works
    
    Returns:
        Current user information from development token
    """
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Development endpoint not available in production"
        )
    
    return {
        "message": "Development token authentication successful!",
        "user": current_user,
        "authentication_method": "development",
        "instructions": [
            "Your development token is working correctly",
            "This is for development/testing only",
            "In production, use Clerk authentication tokens"
        ]
    }


# New authentication endpoints using controller pattern

@router.post("/register", response_model=RegisterResponseModelV1, status_code=status.HTTP_201_CREATED)
async def register_user(
    registration_data: RegisterRequestV1,
    request: Request,
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Register a new user account.
    
    Creates a new user account with email verification required.
    Only pet_owner role is allowed for self-registration.
    """
    try:
        # Get client information
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Convert Pydantic model to dict
        registration_dict = registration_data.dict()
        
        # Restrict self-registration to pet_owner role
        registration_dict["role"] = UserRole.PET_OWNER
        
        result = await controller.register_user(
            registration_data=registration_dict,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return {
            "success": True,
            "data": {
                "user": {
                    "id": result["user"].id,
                    "email": result["user"].email,
                    "first_name": result["user"].first_name,
                    "last_name": result["user"].last_name,
                    "phone_number": result["user"].phone_number,
                    "role": result["user"].role,
                    "is_active": result["user"].is_active,
                    "is_verified": result["user"].is_verified,
                    "last_login": result["user"].last_login,
                    "created_at": result["user"].created_at
                },
                "message": result["message"],
                "verification_required": result["verification_required"]
            },
            "version": "v1"
        }
        
    except (ValidationError, ConflictError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/login", response_model=LoginResponseModelV1)
async def login_user(
    login_data: LoginRequestV1,
    request: Request,
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Authenticate user and create session.
    
    Returns JWT token and user information upon successful authentication.
    """
    try:
        # Get client information
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Convert Pydantic model to dict
        login_dict = login_data.dict()
        
        result = await controller.login_user(
            login_data=login_dict,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return {
            "success": True,
            "data": result,
            "version": "v1"
        }
        
    except (ValidationError, AuthenticationError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/logout", response_model=AuthSuccessResponseV1)
async def logout_user(
    logout_data: LogoutRequestV1,
    current_user: Dict[str, Any] = Depends(get_current_user_helper),
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Logout user from current or all sessions.
    
    Invalidates the specified session or all user sessions.
    """
    try:
        # Convert Pydantic model to dict
        logout_dict = logout_data.dict()
        
        result = await controller.logout_user(
            logout_data=logout_dict,
            current_user_id=current_user.get("user_id")
        )
        
        return {
            "success": result["success"],
            "message": result["message"],
            "data": None
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/refresh", response_model=TokenResponseModelV1)
async def refresh_token(
    refresh_data: RefreshTokenRequestV1,
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Refresh access token using refresh token.
    
    Returns new access token if refresh token is valid.
    """
    try:
        # Convert Pydantic model to dict
        refresh_dict = refresh_data.dict()
        
        result = await controller.refresh_token(refresh_data=refresh_dict)
        
        return {
            "success": True,
            "data": result,
            "version": "v1"
        }
        
    except (ValidationError, AuthenticationError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/change-password", response_model=AuthSuccessResponseV1)
async def change_password(
    password_data: ChangePasswordV1,
    current_user: Dict[str, Any] = Depends(get_current_user_helper),
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Change user password.
    
    Requires current password for verification.
    """
    try:
        # Convert Pydantic model to dict
        password_dict = password_data.dict()
        
        result = await controller.change_password(
            password_data=password_dict,
            current_user_id=current_user.get("user_id")
        )
        
        return {
            "success": result["success"],
            "message": result["message"],
            "data": None
        }
        
    except (ValidationError, AuthenticationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/password-reset", response_model=AuthSuccessResponseV1)
async def request_password_reset(
    reset_data: PasswordResetRequestV1,
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Request password reset.
    
    Sends password reset instructions to the provided email address.
    """
    try:
        # Convert Pydantic model to dict
        reset_dict = reset_data.dict()
        
        result = await controller.request_password_reset(reset_data=reset_dict)
        
        return {
            "success": result["success"],
            "message": result["message"],
            "data": None
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/password-reset/confirm", response_model=AuthSuccessResponseV1)
async def confirm_password_reset(
    reset_data: PasswordResetConfirmV1,
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Confirm password reset with token.
    
    Resets password using the provided reset token.
    """
    try:
        # Convert Pydantic model to dict
        reset_dict = reset_data.dict()
        
        result = await controller.confirm_password_reset(reset_data=reset_dict)
        
        return {
            "success": result["success"],
            "message": result["message"],
            "data": None
        }
        
    except (ValidationError, AuthenticationError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/sessions", response_model=ActiveSessionsResponseModelV1)
async def get_user_sessions(
    current_user: Dict[str, Any] = Depends(get_current_user_helper),
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Get active sessions for current user.
    
    Returns list of active sessions with metadata.
    """
    try:
        result = await controller.get_user_sessions(
            user_id=current_user.get("user_id")
        )
        
        return {
            "success": True,
            "data": result,
            "version": "v1"
        }
        
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/check-permission", response_model=PermissionResponseModelV1)
async def check_permission(
    permission_data: PermissionCheckV1,
    current_user: Dict[str, Any] = Depends(get_current_user_helper),
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Check if current user has a specific permission.
    
    Returns whether the user has the requested permission.
    """
    try:
        result = await controller.check_permission(
            permission=permission_data.permission,
            user_role=current_user.get("role")
        )
        
        return {
            "success": True,
            "data": result,
            "version": "v1"
        }
        
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/roles/{role}/permissions", response_model=RolePermissionsModelV1)
async def get_role_permissions(
    role: UserRole,
    current_user: Dict[str, Any] = Depends(require_staff_access()),
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Get permissions for a specific role.
    
    Requires staff access. Returns list of permissions for the specified role.
    """
    try:
        result = await controller.get_role_permissions(role=role.value)
        
        return {
            "success": True,
            "data": result,
            "version": "v1"
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/user-info")
async def get_user_info(
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get current user information if authenticated, otherwise return public info.
    This endpoint works with or without authentication.
    
    Returns:
        User information if authenticated, or public API info if not
    """
    if current_user:
        return {
            "authenticated": True,
            "user": {
                "id": str(current_user.id),
                "email": current_user.email,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "role": current_user.role.value,
                "is_active": current_user.is_active
            },
            "message": "User is authenticated with Clerk"
        }
    else:
        return {
            "authenticated": False,
            "message": "No authentication provided",
            "api_info": {
                "name": "Veterinary Clinic Backend API",
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT,
                "authentication": "Clerk JWT tokens required for protected endpoints"
            }
        }


# User profile management endpoints

@router.get("/profile", response_model=UserProfileV1)
async def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile information.
    
    Requires authentication. Returns detailed user profile data.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "phone_number": current_user.phone_number,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "last_login": current_user.last_login,
        "created_at": current_user.created_at
    }


@router.put("/profile", response_model=UserProfileV1)
async def update_user_profile(
    profile_data: dict,
    current_user: User = Depends(get_current_user),
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Update current user's profile information.
    
    Allows users to update their own profile data.
    """
    try:
        # Add current user ID to the profile data
        profile_data["user_id"] = str(current_user.id)
        
        result = await controller.update_user_profile(
            profile_data=profile_data,
            current_user_id=str(current_user.id)
        )
        
        return result["user"]
        
    except (ValidationError, BusinessLogicError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/users/{user_id}", response_model=UserProfileV1)
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(require_staff_access()),
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Get user profile by ID.
    
    Requires staff access. Returns user profile information.
    """
    try:
        result = await controller.get_user_by_id(user_id=user_id)
        return result["user"]
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put("/users/{user_id}", response_model=UserProfileV1)
async def update_user_by_id(
    user_id: str,
    profile_data: dict,
    current_user: User = Depends(require_management_access()),
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Update user profile by ID.
    
    Requires admin access. Allows admins to update any user's profile.
    """
    try:
        # Add user ID to the profile data
        profile_data["user_id"] = user_id
        
        result = await controller.update_user_profile(
            profile_data=profile_data,
            current_user_id=str(current_user.id),
            target_user_id=user_id
        )
        
        return result["user"]
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(require_management_access()),
    controller: AuthController = Depends(get_controller(AuthController))
):
    """
    Deactivate user account.
    
    Requires admin access. Deactivates user account (soft delete).
    """
    try:
        result = await controller.deactivate_user(
            user_id=user_id,
            current_user_id=str(current_user.id)
        )
        
        return {
            "success": result["success"],
            "message": result["message"]
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )