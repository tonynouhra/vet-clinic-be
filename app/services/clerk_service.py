"""
Clerk authentication service for the Veterinary Clinic Backend.
Handles JWT token validation, user data retrieval, and API integration.
"""

import httpx
import jwt
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from functools import lru_cache
from cryptography.hazmat.primitives import serialization

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)
settings = get_settings()


class ClerkUser:
    """Data class for Clerk user information."""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id")
        self.email_addresses = data.get("email_addresses", [])
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")
        self.phone_numbers = data.get("phone_numbers", [])
        self.public_metadata = data.get("public_metadata", {})
        self.private_metadata = data.get("private_metadata", {})
        self.created_at = data.get("created_at")
        self.updated_at = data.get("updated_at")
        self.last_sign_in_at = data.get("last_sign_in_at")
    
    @property
    def primary_email(self) -> Optional[str]:
        """Get primary email address."""
        for email in self.email_addresses:
            if email.get("id") == email.get("primary_email_address_id"):
                return email.get("email_address")
        # Fallback to first email if no primary found
        if self.email_addresses:
            return self.email_addresses[0].get("email_address")
        return None
    
    @property
    def primary_phone(self) -> Optional[str]:
        """Get primary phone number."""
        for phone in self.phone_numbers:
            if phone.get("primary"):
                return phone.get("phone_number")
        # Fallback to first phone if no primary found
        if self.phone_numbers:
            return self.phone_numbers[0].get("phone_number")
        return None
    
    @property
    def role(self) -> str:
        """Get user role from public metadata."""
        return self.public_metadata.get("role", "pet_owner")


class ClerkService:
    """Service for interacting with Clerk API and handling authentication."""
    
    def __init__(self):
        self.base_url = "https://api.clerk.com/v1"
        self.secret_key = settings.CLERK_SECRET_KEY
        self.jwt_issuer = settings.CLERK_JWT_ISSUER
        self._jwks_cache = {}
        self._jwks_cache_time = None
    
    async def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token with Clerk and extract user information.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Dict containing user information from token
            
        Raises:
            AuthenticationError: If token is invalid or expired
        """
        try:
            # Get JWT header to find the key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                raise AuthenticationError("Token missing key ID")
            
            # Get public key for verification
            public_key = await self._get_public_key(kid)
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=self.jwt_issuer,
                options={"verify_aud": False}  # Clerk doesn't always include audience
            )
            
            # Extract user information
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Token missing user ID")
            
            return {
                "user_id": user_id,
                "clerk_id": user_id,
                "email": payload.get("email"),
                "role": payload.get("public_metadata", {}).get("role", "pet_owner"),
                "permissions": payload.get("public_metadata", {}).get("permissions", []),
                "exp": payload.get("exp"),
                "iat": payload.get("iat"),
                "session_id": payload.get("sid")
            }
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise AuthenticationError("Invalid token")
        except Exception as e:
            logger.error(f"JWT verification error: {e}")
            raise AuthenticationError("Token verification failed")
    
    async def get_user_by_clerk_id(self, clerk_id: str) -> ClerkUser:
        """
        Get user information from Clerk API by user ID.
        
        Args:
            clerk_id: Clerk user ID
            
        Returns:
            ClerkUser object with user information
            
        Raises:
            AuthenticationError: If user not found or API error
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/users/{clerk_id}",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 404:
                    raise AuthenticationError(f"User not found: {clerk_id}")
                
                response.raise_for_status()
                user_data = response.json()
                
                return ClerkUser(user_data)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Clerk API error: {e.response.status_code} - {e.response.text}")
            raise AuthenticationError("Failed to fetch user from Clerk")
        except Exception as e:
            logger.error(f"Error fetching user from Clerk: {e}")
            raise AuthenticationError("User lookup failed")
    
    async def create_user_session(self, email: str, password: str) -> Dict[str, Any]:
        """
        Create a user session for development/testing purposes.
        This method is only for development and should not be used in production.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Dict containing session token and user info
            
        Raises:
            AuthenticationError: If login fails
        """
        if settings.ENVIRONMENT == "production":
            raise AuthenticationError("Development login not available in production")
        
        try:
            async with httpx.AsyncClient() as client:
                # First, try to find user by email
                response = await client.get(
                    f"{self.base_url}/users",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json"
                    },
                    params={"email_address": email}
                )
                
                if response.status_code != 200:
                    raise AuthenticationError("User not found")
                
                users = response.json()
                if not users:
                    raise AuthenticationError("User not found")
                
                user_data = users[0]
                clerk_user = ClerkUser(user_data)
                
                # For development, we'll create a simple JWT token
                # In production, this would be handled by Clerk's frontend SDK
                token_payload = {
                    "sub": clerk_user.id,
                    "email": clerk_user.primary_email,
                    "iat": int(datetime.utcnow().timestamp()),
                    "exp": int(datetime.utcnow().timestamp()) + 3600,  # 1 hour
                    "iss": self.jwt_issuer,
                    "public_metadata": clerk_user.public_metadata
                }
                
                # Create a development token (not a real Clerk token)
                dev_token = jwt.encode(
                    token_payload,
                    settings.JWT_SECRET_KEY,
                    algorithm="HS256"
                )
                
                return {
                    "token": dev_token,
                    "user": {
                        "id": clerk_user.id,
                        "email": clerk_user.primary_email,
                        "first_name": clerk_user.first_name,
                        "last_name": clerk_user.last_name,
                        "role": clerk_user.role
                    }
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Clerk API error during dev login: {e.response.status_code}")
            raise AuthenticationError("Login failed")
        except Exception as e:
            logger.error(f"Development login error: {e}")
            raise AuthenticationError("Login failed")
    
    async def _get_public_key(self, kid: str) -> str:
        """
        Get public key from Clerk's JWKS endpoint for JWT verification.
        
        Args:
            kid: Key ID from JWT header
            
        Returns:
            Public key for verification
        """
        try:
            # Check cache first
            if kid in self._jwks_cache:
                return self._jwks_cache[kid]
            
            # Fetch JWKS from Clerk
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.jwt_issuer}/.well-known/jwks.json")
                response.raise_for_status()
                jwks = response.json()
            
            # Find the key with matching kid
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    # Convert JWK to PEM format
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    pem_key = public_key.public_key().public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    ).decode()
                    
                    # Cache the key
                    self._jwks_cache[kid] = pem_key
                    return pem_key
            
            raise AuthenticationError(f"Public key not found for kid: {kid}")
            
        except Exception as e:
            logger.error(f"Error fetching public key: {e}")
            raise AuthenticationError("Failed to verify token signature")
    
    async def validate_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate webhook signature from Clerk.
        
        Args:
            payload: Raw webhook payload
            signature: Signature from webhook headers
            
        Returns:
            True if signature is valid
        """
        if not settings.CLERK_WEBHOOK_SECRET:
            logger.warning("Webhook secret not configured")
            return False
        
        try:
            import hmac
            import hashlib
            
            expected_signature = hmac.new(
                settings.CLERK_WEBHOOK_SECRET.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Webhook signature validation error: {e}")
            return False


# Global service instance
clerk_service = ClerkService()


def get_clerk_service() -> ClerkService:
    """Get Clerk service instance."""
    return clerk_service