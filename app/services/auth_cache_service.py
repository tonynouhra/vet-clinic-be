"""
Authentication caching service for Redis-based performance optimization.
Handles caching of user data, JWT validation results, and cache invalidation.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import hashlib

from app.core.redis import redis_client
from app.core.config import get_settings
from app.models.user import User
from app.schemas.clerk_schemas import ClerkUser

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthCacheService:
    """Service for authentication-related caching operations."""

    def __init__(self):
        self.redis = redis_client
        self.user_cache_ttl = settings.REDIS_USER_CACHE_TTL
        self.jwt_cache_ttl = settings.REDIS_JWT_CACHE_TTL

    # Cache key generators
    def _user_cache_key(self, clerk_id: str) -> str:
        """Generate cache key for user data."""
        return f"auth:user:{clerk_id}"

    def _jwt_cache_key(self, token_hash: str) -> str:
        """Generate cache key for JWT validation results."""
        return f"auth:jwt:{token_hash}"

    def _user_permissions_key(self, user_id: str) -> str:
        """Generate cache key for user permissions."""
        return f"auth:permissions:{user_id}"

    def _user_role_key(self, user_id: str) -> str:
        """Generate cache key for user role."""
        return f"auth:role:{user_id}"

    def _hash_token(self, token: str) -> str:
        """Create a hash of the JWT token for cache key."""
        return hashlib.sha256(token.encode()).hexdigest()[:32]

    # User data caching
    async def cache_user_data(self, user: User) -> bool:
        """
        Cache user data in Redis.

        Args:
            user: User object to cache

        Returns:
            True if caching successful
        """
        try:
            if not user.clerk_id:
                logger.warning("Cannot cache user without clerk_id: %s", user.id)
                return False

            cache_key = self._user_cache_key(user.clerk_id)
            
            # Prepare user data for caching
            user_data = {
                "id": str(user.id),
                "clerk_id": user.clerk_id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "role": user.role.value if user.role else None,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "avatar_url": user.avatar_url,
                "preferences": user.preferences or {},
                "notification_settings": user.notification_settings or {},
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "cached_at": datetime.utcnow().isoformat()
            }

            success = await self.redis.set_json(cache_key, user_data, self.user_cache_ttl)
            
            if success:
                logger.debug("Cached user data for clerk_id: %s", user.clerk_id)
            else:
                logger.warning("Failed to cache user data for clerk_id: %s", user.clerk_id)
            
            return success

        except Exception as e:
            logger.error("Error caching user data for clerk_id %s: %s", user.clerk_id, str(e))
            return False

    async def get_cached_user_data(self, clerk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached user data from Redis.

        Args:
            clerk_id: Clerk user ID

        Returns:
            User data dict or None if not found/expired
        """
        try:
            cache_key = self._user_cache_key(clerk_id)
            user_data = await self.redis.get_json(cache_key)
            
            if user_data:
                logger.debug("Retrieved cached user data for clerk_id: %s", clerk_id)
                return user_data
            
            logger.debug("No cached user data found for clerk_id: %s", clerk_id)
            return None

        except Exception as e:
            logger.error("Error retrieving cached user data for clerk_id %s: %s", clerk_id, str(e))
            return None

    async def invalidate_user_cache(self, clerk_id: str) -> bool:
        """
        Invalidate cached user data.

        Args:
            clerk_id: Clerk user ID

        Returns:
            True if invalidation successful
        """
        try:
            cache_key = self._user_cache_key(clerk_id)
            success = await self.redis.delete(cache_key)
            
            if success:
                logger.debug("Invalidated user cache for clerk_id: %s", clerk_id)
            
            return success

        except Exception as e:
            logger.error("Error invalidating user cache for clerk_id %s: %s", clerk_id, str(e))
            return False

    # JWT token validation caching
    async def cache_jwt_validation(self, token: str, validation_result: Dict[str, Any]) -> bool:
        """
        Cache JWT token validation result.

        Args:
            token: JWT token
            validation_result: Token validation result

        Returns:
            True if caching successful
        """
        try:
            token_hash = self._hash_token(token)
            cache_key = self._jwt_cache_key(token_hash)
            
            # Add caching metadata
            cache_data = {
                **validation_result,
                "cached_at": datetime.utcnow().isoformat(),
                "token_hash": token_hash
            }
            
            # Calculate TTL based on token expiration
            exp_timestamp = validation_result.get("exp")
            if exp_timestamp:
                token_exp = datetime.fromtimestamp(exp_timestamp)
                time_until_exp = (token_exp - datetime.utcnow()).total_seconds()
                # Use shorter of configured TTL or time until token expires
                ttl = min(self.jwt_cache_ttl, max(60, int(time_until_exp)))
            else:
                ttl = self.jwt_cache_ttl

            success = await self.redis.set_json(cache_key, cache_data, ttl)
            
            if success:
                logger.debug("Cached JWT validation result for token hash: %s", token_hash)
            else:
                logger.warning("Failed to cache JWT validation result")
            
            return success

        except Exception as e:
            logger.error("Error caching JWT validation result: %s", str(e))
            return False

    async def get_cached_jwt_validation(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get cached JWT token validation result.

        Args:
            token: JWT token

        Returns:
            Validation result dict or None if not found/expired
        """
        try:
            token_hash = self._hash_token(token)
            cache_key = self._jwt_cache_key(token_hash)
            
            validation_data = await self.redis.get_json(cache_key)
            
            if validation_data:
                # Check if token is still valid (not expired)
                exp_timestamp = validation_data.get("exp")
                if exp_timestamp:
                    token_exp = datetime.fromtimestamp(exp_timestamp)
                    if datetime.utcnow() >= token_exp:
                        # Token has expired, remove from cache
                        await self.redis.delete(cache_key)
                        logger.debug("Removed expired JWT from cache: %s", token_hash)
                        return None
                
                logger.debug("Retrieved cached JWT validation for token hash: %s", token_hash)
                return validation_data
            
            logger.debug("No cached JWT validation found for token hash: %s", token_hash)
            return None

        except Exception as e:
            logger.error("Error retrieving cached JWT validation: %s", str(e))
            return None

    async def invalidate_jwt_cache(self, token: str) -> bool:
        """
        Invalidate cached JWT token validation.

        Args:
            token: JWT token

        Returns:
            True if invalidation successful
        """
        try:
            token_hash = self._hash_token(token)
            cache_key = self._jwt_cache_key(token_hash)
            success = await self.redis.delete(cache_key)
            
            if success:
                logger.debug("Invalidated JWT cache for token hash: %s", token_hash)
            
            return success

        except Exception as e:
            logger.error("Error invalidating JWT cache: %s", str(e))
            return False

    # User permissions and role caching
    async def cache_user_permissions(self, user_id: str, permissions: List[str]) -> bool:
        """
        Cache user permissions.

        Args:
            user_id: User ID
            permissions: List of user permissions

        Returns:
            True if caching successful
        """
        try:
            cache_key = self._user_permissions_key(user_id)
            
            cache_data = {
                "permissions": permissions,
                "cached_at": datetime.utcnow().isoformat()
            }
            
            success = await self.redis.set_json(cache_key, cache_data, self.user_cache_ttl)
            
            if success:
                logger.debug("Cached permissions for user: %s", user_id)
            
            return success

        except Exception as e:
            logger.error("Error caching user permissions for user %s: %s", user_id, str(e))
            return False

    async def get_cached_user_permissions(self, user_id: str) -> Optional[List[str]]:
        """
        Get cached user permissions.

        Args:
            user_id: User ID

        Returns:
            List of permissions or None if not found/expired
        """
        try:
            cache_key = self._user_permissions_key(user_id)
            permissions_data = await self.redis.get_json(cache_key)
            
            if permissions_data:
                logger.debug("Retrieved cached permissions for user: %s", user_id)
                return permissions_data.get("permissions", [])
            
            return None

        except Exception as e:
            logger.error("Error retrieving cached permissions for user %s: %s", user_id, str(e))
            return None

    async def cache_user_role(self, user_id: str, role: str) -> bool:
        """
        Cache user role.

        Args:
            user_id: User ID
            role: User role

        Returns:
            True if caching successful
        """
        try:
            cache_key = self._user_role_key(user_id)
            
            cache_data = {
                "role": role,
                "cached_at": datetime.utcnow().isoformat()
            }
            
            success = await self.redis.set_json(cache_key, cache_data, self.user_cache_ttl)
            
            if success:
                logger.debug("Cached role for user: %s", user_id)
            
            return success

        except Exception as e:
            logger.error("Error caching user role for user %s: %s", user_id, str(e))
            return False

    async def get_cached_user_role(self, user_id: str) -> Optional[str]:
        """
        Get cached user role.

        Args:
            user_id: User ID

        Returns:
            User role or None if not found/expired
        """
        try:
            cache_key = self._user_role_key(user_id)
            role_data = await self.redis.get_json(cache_key)
            
            if role_data:
                logger.debug("Retrieved cached role for user: %s", user_id)
                return role_data.get("role")
            
            return None

        except Exception as e:
            logger.error("Error retrieving cached role for user %s: %s", user_id, str(e))
            return None

    # Bulk cache operations
    async def invalidate_user_related_cache(self, clerk_id: str, user_id: str) -> bool:
        """
        Invalidate all cache entries related to a user.

        Args:
            clerk_id: Clerk user ID
            user_id: Local user ID

        Returns:
            True if all invalidations successful
        """
        try:
            success = True
            
            # Invalidate user data cache
            if not await self.invalidate_user_cache(clerk_id):
                success = False
            
            # Invalidate permissions cache
            permissions_key = self._user_permissions_key(user_id)
            if not await self.redis.delete(permissions_key):
                success = False
            
            # Invalidate role cache
            role_key = self._user_role_key(user_id)
            if not await self.redis.delete(role_key):
                success = False
            
            if success:
                logger.debug("Invalidated all cache for user: clerk_id=%s, user_id=%s", clerk_id, user_id)
            else:
                logger.warning("Partial cache invalidation for user: clerk_id=%s, user_id=%s", clerk_id, user_id)
            
            return success

        except Exception as e:
            logger.error("Error invalidating user-related cache: %s", str(e))
            return False

    async def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics
        """
        try:
            stats = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_cache_ttl": self.user_cache_ttl,
                "jwt_cache_ttl": self.jwt_cache_ttl,
                "cache_keys": {
                    "user_data": 0,
                    "jwt_validation": 0,
                    "permissions": 0,
                    "roles": 0
                }
            }
            
            # Count cache keys by pattern (this is a simplified approach)
            # In production, you might want to use Redis SCAN for better performance
            try:
                # Note: This is a basic implementation. For production,
                # consider using Redis INFO or more efficient key counting methods
                stats["status"] = "active"
            except Exception:
                stats["status"] = "error"
                stats["error"] = "Unable to retrieve detailed statistics"
            
            return stats

        except Exception as e:
            logger.error("Error getting cache statistics: %s", str(e))
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e)
            }

    async def clear_expired_cache(self) -> int:
        """
        Clear expired cache entries (maintenance operation).

        Returns:
            Number of entries cleared
        """
        try:
            # Redis automatically handles TTL expiration, but this method
            # can be used for manual cleanup if needed
            cleared_count = 0
            
            # This is a placeholder for manual cleanup logic
            # In most cases, Redis TTL handles expiration automatically
            
            logger.info("Cache cleanup completed, cleared %d entries", cleared_count)
            return cleared_count

        except Exception as e:
            logger.error("Error during cache cleanup: %s", str(e))
            return 0


# Global cache service instance
auth_cache_service = AuthCacheService()


def get_auth_cache_service() -> AuthCacheService:
    """Get authentication cache service instance."""
    return auth_cache_service