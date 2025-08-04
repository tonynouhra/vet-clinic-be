"""
Authentication endpoints for the Veterinary Clinic Backend.
Includes development endpoints for testing with Postman.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Dict, Any
import logging
import jwt
from datetime import datetime, timedelta

from app.services.clerk_service import get_clerk_service, ClerkService
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

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
    current_user: Dict[str, Any] = Depends(get_current_user_simple)
):
    """
    Test endpoint to verify token authentication is working.
    This endpoint requires a valid JWT token.
    
    Usage:
    1. Get token from /auth/dev-login
    2. Add to Authorization header: Bearer <token>
    3. Call this endpoint to verify token works
    
    Returns:
        Current user information from token
    """
    return {
        "message": "Token authentication successful!",
        "user": current_user,
        "instructions": [
            "Your token is working correctly",
            "You can now use this token to access protected endpoints",
            "Add 'Authorization: Bearer <your-token>' to all API requests"
        ]
    }