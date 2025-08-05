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
from app.core.exceptions import AuthenticationError, ExternalServiceError
from app.core.error_handlers import (
    with_error_handling, 
    error_context, 
    handle_clerk_api_error,
    get_fallback_manager
)
from app.core.logging_config import get_auth_logger
from app.services.auth_cache_service import get_auth_cache_service

logger = logging.getLogger(__name__)
auth_logger = get_auth_logger()
settings = get_settings()
fallback_manager = get_fallback_manager()


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
        self.base_url = f"{settings.CLERK_API_URL}/v1"
        self.secret_key = settings.CLERK_SECRET_KEY
        self.jwt_issuer = settings.CLERK_JWT_ISSUER
        self.jwks_url = (
            settings.CLERK_JWKS_URL
            or f"{settings.CLERK_JWT_ISSUER}/.well-known/jwks.json"
        )
        self._jwks_cache = {}
        self._jwks_cache_time = None
        self.cache_service = get_auth_cache_service()

    @with_error_handling("jwt_token_verification")
    async def verify_jwt_token(self, token: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify JWT token with Clerk and extract user information.
        Uses Redis caching for performance optimization and enhanced error handling.

        Args:
            token: JWT token to verify
            request_id: Request ID for tracking

        Returns:
            Dict containing user information from token

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        async with error_context("jwt_token_verification", request_id=request_id):
            try:
                # Check cache first
                cached_result = await self.cache_service.get_cached_jwt_validation(token)
                if cached_result:
                    logger.debug("Using cached JWT validation result")
                    auth_logger.log_authentication_success(
                        user_id=cached_result.get("user_id"),
                        clerk_id=cached_result.get("clerk_id"),
                        email=cached_result.get("email"),
                        role=cached_result.get("role"),
                        request_id=request_id
                    )
                    return cached_result

                # Get JWT header to find the key ID
                try:
                    unverified_header = jwt.get_unverified_header(token)
                except jwt.DecodeError as e:
                    auth_logger.log_token_validation_error(
                        error_type="malformed_token",
                        error_message="Token header cannot be decoded",
                        request_id=request_id
                    )
                    raise AuthenticationError("Malformed token")

                kid = unverified_header.get("kid")
                if not kid:
                    auth_logger.log_token_validation_error(
                        error_type="missing_key_id",
                        error_message="Token missing key ID",
                        token_info={"header": unverified_header},
                        request_id=request_id
                    )
                    raise AuthenticationError("Token missing key ID")

                # Get public key for verification with fallback
                public_key = await fallback_manager.execute_with_fallback(
                    primary_func=self._get_public_key,
                    fallback_func=self._get_cached_public_key,
                    operation_name="get_public_key",
                    request_id=request_id,
                    kid=kid
                )

                # Verify and decode token
                try:
                    payload = jwt.decode(
                        token,
                        public_key,
                        algorithms=["RS256"],
                        issuer=self.jwt_issuer,
                        options={"verify_aud": False},  # Clerk doesn't always include audience
                    )
                except jwt.ExpiredSignatureError:
                    auth_logger.log_token_validation_error(
                        error_type="expired_token",
                        error_message="Token has expired",
                        request_id=request_id
                    )
                    raise AuthenticationError("Token has expired")
                except jwt.InvalidSignatureError:
                    auth_logger.log_token_validation_error(
                        error_type="invalid_signature",
                        error_message="Token signature is invalid",
                        request_id=request_id
                    )
                    raise AuthenticationError("Invalid token signature")
                except jwt.InvalidIssuerError:
                    auth_logger.log_token_validation_error(
                        error_type="invalid_issuer",
                        error_message=f"Token issuer mismatch. Expected: {self.jwt_issuer}",
                        request_id=request_id
                    )
                    raise AuthenticationError("Invalid token issuer")
                except jwt.InvalidTokenError as e:
                    auth_logger.log_token_validation_error(
                        error_type="invalid_token",
                        error_message=str(e),
                        request_id=request_id
                    )
                    raise AuthenticationError("Invalid token")

                # Extract user information
                user_id = payload.get("sub")
                if not user_id:
                    auth_logger.log_token_validation_error(
                        error_type="missing_user_id",
                        error_message="Token missing user ID",
                        token_info={"payload_keys": list(payload.keys())},
                        request_id=request_id
                    )
                    raise AuthenticationError("Token missing user ID")

                validation_result = {
                    "user_id": user_id,
                    "clerk_id": user_id,
                    "email": payload.get("email"),
                    "role": payload.get("public_metadata", {}).get("role", "pet_owner"),
                    "permissions": payload.get("public_metadata", {}).get(
                        "permissions", []
                    ),
                    "exp": payload.get("exp"),
                    "iat": payload.get("iat"),
                    "session_id": payload.get("sid"),
                }

                # Cache the validation result
                await self.cache_service.cache_jwt_validation(token, validation_result)

                # Log successful authentication
                auth_logger.log_authentication_success(
                    user_id=user_id,
                    clerk_id=user_id,
                    email=validation_result.get("email"),
                    role=validation_result.get("role"),
                    request_id=request_id
                )

                return validation_result

            except AuthenticationError:
                # Re-raise authentication errors as-is
                raise
            except Exception as e:
                auth_logger.log_token_validation_error(
                    error_type="unexpected_error",
                    error_message=str(e),
                    request_id=request_id
                )
                raise AuthenticationError("Token verification failed")

    @with_error_handling("get_user_by_clerk_id")
    async def get_user_by_clerk_id(self, clerk_id: str, request_id: Optional[str] = None) -> ClerkUser:
        """
        Get user information from Clerk API by user ID.
        Uses Redis caching for performance optimization and enhanced error handling.

        Args:
            clerk_id: Clerk user ID
            request_id: Request ID for tracking

        Returns:
            ClerkUser object with user information

        Raises:
            AuthenticationError: If user not found or API error
            ExternalServiceError: If Clerk API is unavailable
        """
        async with error_context("get_user_by_clerk_id", request_id=request_id, clerk_id=clerk_id):
            # Check cache first
            cached_user_data = await self.cache_service.get_cached_user_data(clerk_id)
            if cached_user_data:
                logger.debug("Using cached user data for clerk_id: %s", clerk_id)
                # Convert cached data back to ClerkUser format
                clerk_user_data = self._convert_cached_to_clerk_format(cached_user_data)
                return ClerkUser(clerk_user_data)

            # Fetch from Clerk API with fallback
            return await fallback_manager.execute_with_fallback(
                primary_func=self._fetch_user_from_clerk_api,
                fallback_func=self._get_user_from_cache_fallback,
                operation_name="get_user_by_clerk_id",
                request_id=request_id,
                clerk_id=clerk_id
            )

    async def _fetch_user_from_clerk_api(self, clerk_id: str, request_id: Optional[str] = None) -> ClerkUser:
        """
        Fetch user from Clerk API with proper error handling.
        
        Args:
            clerk_id: Clerk user ID
            request_id: Request ID for tracking
            
        Returns:
            ClerkUser object
            
        Raises:
            ExternalServiceError: If API call fails
            AuthenticationError: If user not found
        """
        try:
            timeout = httpx.Timeout(settings.CLERK_REQUEST_TIMEOUT)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    f"{self.base_url}/users/{clerk_id}",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json",
                    },
                )

                if response.status_code == 404:
                    raise AuthenticationError(f"User not found: {clerk_id}")

                response.raise_for_status()
                user_data = response.json()

                return ClerkUser(user_data)

        except httpx.HTTPStatusError as e:
            raise handle_clerk_api_error(e, "get_user_by_clerk_id", clerk_id, request_id)
        except httpx.TimeoutException as e:
            raise handle_clerk_api_error(e, "get_user_by_clerk_id", clerk_id, request_id)
        except httpx.ConnectError as e:
            raise handle_clerk_api_error(e, "get_user_by_clerk_id", clerk_id, request_id)
        except Exception as e:
            raise handle_clerk_api_error(e, "get_user_by_clerk_id", clerk_id, request_id)

    async def _get_user_from_cache_fallback(self, clerk_id: str, request_id: Optional[str] = None) -> Optional[ClerkUser]:
        """
        Fallback method to get user from cache when Clerk API is unavailable.
        
        Args:
            clerk_id: Clerk user ID
            request_id: Request ID for tracking
            
        Returns:
            ClerkUser object if found in cache, None otherwise
        """
        logger.warning(f"Using cache fallback for user {clerk_id}")
        
        # Try to get from cache with extended search
        cached_user_data = await self.cache_service.get_cached_user_data(clerk_id)
        if cached_user_data:
            clerk_user_data = self._convert_cached_to_clerk_format(cached_user_data)
            return ClerkUser(clerk_user_data)
        
        # If not in cache, we can't provide fallback
        raise AuthenticationError(
            f"User {clerk_id} not found and Clerk API unavailable",
            details={"fallback_attempted": True}
        )

    def _convert_cached_to_clerk_format(self, cached_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert cached user data back to Clerk API format.

        Args:
            cached_data: Cached user data

        Returns:
            Dict in Clerk API format
        """
        # Convert cached data to match ClerkUser expected format
        return {
            "id": cached_data.get("clerk_id"),
            "email_addresses": [
                {
                    "id": "primary",
                    "email_address": cached_data.get("email"),
                    "primary_email_address_id": "primary"
                }
            ] if cached_data.get("email") else [],
            "first_name": cached_data.get("first_name"),
            "last_name": cached_data.get("last_name"),
            "phone_numbers": [
                {
                    "phone_number": cached_data.get("phone_number"),
                    "primary": True
                }
            ] if cached_data.get("phone_number") else [],
            "public_metadata": {
                "role": cached_data.get("role")
            },
            "private_metadata": {},
            "created_at": cached_data.get("created_at"),
            "updated_at": cached_data.get("updated_at"),
            "last_sign_in_at": None,
            "image_url": cached_data.get("avatar_url"),
            "banned": not cached_data.get("is_active", True),
            "locked": not cached_data.get("is_verified", True)
        }

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
                        "Content-Type": "application/json",
                    },
                    params={"email_address": email},
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
                    "public_metadata": clerk_user.public_metadata,
                }

                # Create a development token (not a real Clerk token)
                dev_token = jwt.encode(
                    token_payload, settings.JWT_SECRET_KEY, algorithm="HS256"
                )

                return {
                    "token": dev_token,
                    "user": {
                        "id": clerk_user.id,
                        "email": clerk_user.primary_email,
                        "first_name": clerk_user.first_name,
                        "last_name": clerk_user.last_name,
                        "role": clerk_user.role,
                    },
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"Clerk API error during dev login: {e.response.status_code}")
            raise AuthenticationError("Login failed")
        except Exception as e:
            logger.error(f"Development login error: {e}")
            raise AuthenticationError("Login failed")

    async def _get_public_key(self, kid: str, request_id: Optional[str] = None) -> str:
        """
        Get public key from Clerk's JWKS endpoint for JWT verification.

        Args:
            kid: Key ID from JWT header
            request_id: Request ID for tracking

        Returns:
            Public key for verification
            
        Raises:
            ExternalServiceError: If JWKS endpoint is unavailable
            AuthenticationError: If key not found
        """
        try:
            # Check cache first
            if kid in self._jwks_cache:
                return self._jwks_cache[kid]

            # Fetch JWKS from Clerk
            timeout = httpx.Timeout(settings.CLERK_REQUEST_TIMEOUT)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                jwks = response.json()

            # Find the key with matching kid
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    # Convert JWK to PEM format
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    pem_key = (
                        public_key.public_key()
                        .public_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo,
                        )
                        .decode()
                    )

                    # Cache the key
                    self._jwks_cache[kid] = pem_key
                    return pem_key

            raise AuthenticationError(f"Public key not found for kid: {kid}")

        except httpx.HTTPStatusError as e:
            raise handle_clerk_api_error(e, "get_public_key", None, request_id)
        except httpx.TimeoutException as e:
            raise handle_clerk_api_error(e, "get_public_key", None, request_id)
        except httpx.ConnectError as e:
            raise handle_clerk_api_error(e, "get_public_key", None, request_id)
        except Exception as e:
            auth_logger.log_clerk_api_error(
                operation="get_public_key",
                error_message=str(e),
                request_id=request_id
            )
            raise AuthenticationError("Failed to verify token signature")

    async def _get_cached_public_key(self, kid: str, request_id: Optional[str] = None) -> Optional[str]:
        """
        Fallback method to get public key from cache when JWKS endpoint is unavailable.
        
        Args:
            kid: Key ID from JWT header
            request_id: Request ID for tracking
            
        Returns:
            Cached public key if available, None otherwise
        """
        logger.warning(f"Using cached public key fallback for kid: {kid}")
        
        if kid in self._jwks_cache:
            return self._jwks_cache[kid]
        
        # If no cached key available, we can't verify the token
        raise AuthenticationError(
            f"Public key {kid} not cached and JWKS endpoint unavailable",
            details={"fallback_attempted": True}
        )

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
                settings.CLERK_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
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
