"""
Unit tests for authentication cache service.
Tests Redis caching functionality for user data, JWT validation, and cache invalidation.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.services.auth_cache_service import AuthCacheService, get_auth_cache_service
from app.models.user import User, UserRole
from app.core.config import get_settings


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.exists.return_value = False
    mock_redis.get_json.return_value = None
    mock_redis.set_json.return_value = True
    return mock_redis


@pytest.fixture
def auth_cache_service(mock_redis_client):
    """Create AuthCacheService instance with mocked Redis."""
    service = AuthCacheService()
    service.redis = mock_redis_client
    return service


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    user = User(
        id=1,
        clerk_id="user_123",
        email="test@example.com",
        first_name="John",
        last_name="Doe",
        phone_number="+1234567890",
        role=UserRole.PET_OWNER,
        is_active=True,
        is_verified=True,
        avatar_url="https://example.com/avatar.jpg",
        preferences={"theme": "dark"},
        notification_settings={"email": True},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    return user


@pytest.fixture
def sample_jwt_validation():
    """Create sample JWT validation result."""
    return {
        "user_id": "user_123",
        "clerk_id": "user_123",
        "email": "test@example.com",
        "role": "pet_owner",
        "permissions": ["read:pets"],
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
        "session_id": "sess_123"
    }


class TestAuthCacheService:
    """Test cases for AuthCacheService."""

    def test_get_auth_cache_service(self):
        """Test getting the global auth cache service instance."""
        service = get_auth_cache_service()
        assert isinstance(service, AuthCacheService)
        
        # Should return the same instance
        service2 = get_auth_cache_service()
        assert service is service2

    def test_cache_key_generators(self, auth_cache_service):
        """Test cache key generation methods."""
        service = auth_cache_service
        
        # Test user cache key
        user_key = service._user_cache_key("user_123")
        assert user_key == "auth:user:user_123"
        
        # Test JWT cache key
        jwt_key = service._jwt_cache_key("token_hash")
        assert jwt_key == "auth:jwt:token_hash"
        
        # Test permissions key
        perm_key = service._user_permissions_key("user_456")
        assert perm_key == "auth:permissions:user_456"
        
        # Test role key
        role_key = service._user_role_key("user_789")
        assert role_key == "auth:role:user_789"

    def test_hash_token(self, auth_cache_service):
        """Test JWT token hashing."""
        service = auth_cache_service
        
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        hash1 = service._hash_token(token)
        hash2 = service._hash_token(token)
        
        # Same token should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 32  # SHA256 truncated to 32 chars
        
        # Different tokens should produce different hashes
        different_token = "different.token.here"
        hash3 = service._hash_token(different_token)
        assert hash1 != hash3

    @pytest.mark.asyncio
    async def test_cache_user_data_success(self, auth_cache_service, sample_user, mock_redis_client):
        """Test successful user data caching."""
        service = auth_cache_service
        mock_redis_client.set_json.return_value = True
        
        result = await service.cache_user_data(sample_user)
        
        assert result is True
        mock_redis_client.set_json.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_redis_client.set_json.call_args
        cache_key = call_args[0][0]
        user_data = call_args[0][1]
        ttl = call_args[0][2]
        
        assert cache_key == "auth:user:user_123"
        assert user_data["clerk_id"] == "user_123"
        assert user_data["email"] == "test@example.com"
        assert user_data["role"] == "pet_owner"
        assert ttl == service.user_cache_ttl

    @pytest.mark.asyncio
    async def test_cache_user_data_no_clerk_id(self, auth_cache_service, sample_user):
        """Test caching user data without clerk_id."""
        service = auth_cache_service
        sample_user.clerk_id = None
        
        result = await service.cache_user_data(sample_user)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_cache_user_data_redis_failure(self, auth_cache_service, sample_user, mock_redis_client):
        """Test user data caching when Redis fails."""
        service = auth_cache_service
        mock_redis_client.set_json.return_value = False
        
        result = await service.cache_user_data(sample_user)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_cached_user_data_success(self, auth_cache_service, mock_redis_client):
        """Test successful retrieval of cached user data."""
        service = auth_cache_service
        cached_data = {
            "clerk_id": "user_123",
            "email": "test@example.com",
            "role": "pet_owner"
        }
        mock_redis_client.get_json.return_value = cached_data
        
        result = await service.get_cached_user_data("user_123")
        
        assert result == cached_data
        mock_redis_client.get_json.assert_called_once_with("auth:user:user_123")

    @pytest.mark.asyncio
    async def test_get_cached_user_data_not_found(self, auth_cache_service, mock_redis_client):
        """Test retrieval when user data is not cached."""
        service = auth_cache_service
        mock_redis_client.get_json.return_value = None
        
        result = await service.get_cached_user_data("user_123")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_user_cache_success(self, auth_cache_service, mock_redis_client):
        """Test successful user cache invalidation."""
        service = auth_cache_service
        mock_redis_client.delete.return_value = True
        
        result = await service.invalidate_user_cache("user_123")
        
        assert result is True
        mock_redis_client.delete.assert_called_once_with("auth:user:user_123")

    @pytest.mark.asyncio
    async def test_cache_jwt_validation_success(self, auth_cache_service, sample_jwt_validation, mock_redis_client):
        """Test successful JWT validation caching."""
        service = auth_cache_service
        mock_redis_client.set_json.return_value = True
        
        token = "sample.jwt.token"
        result = await service.cache_jwt_validation(token, sample_jwt_validation)
        
        assert result is True
        mock_redis_client.set_json.assert_called_once()
        
        # Verify the cached data includes metadata
        call_args = mock_redis_client.set_json.call_args
        cached_data = call_args[0][1]
        assert "cached_at" in cached_data
        assert "token_hash" in cached_data
        assert cached_data["user_id"] == "user_123"

    @pytest.mark.asyncio
    async def test_cache_jwt_validation_with_expiration(self, auth_cache_service, sample_jwt_validation, mock_redis_client):
        """Test JWT validation caching with token expiration consideration."""
        service = auth_cache_service
        mock_redis_client.set_json.return_value = True
        
        # Set token to expire in 30 minutes
        exp_time = datetime.utcnow() + timedelta(minutes=30)
        sample_jwt_validation["exp"] = int(exp_time.timestamp())
        
        token = "sample.jwt.token"
        result = await service.cache_jwt_validation(token, sample_jwt_validation)
        
        assert result is True
        
        # Verify TTL is adjusted based on token expiration
        call_args = mock_redis_client.set_json.call_args
        ttl = call_args[0][2]
        assert ttl < service.jwt_cache_ttl  # Should be less than default TTL

    @pytest.mark.asyncio
    async def test_get_cached_jwt_validation_success(self, auth_cache_service, sample_jwt_validation, mock_redis_client):
        """Test successful retrieval of cached JWT validation."""
        service = auth_cache_service
        
        # Add cache metadata
        cached_data = {
            **sample_jwt_validation,
            "cached_at": datetime.utcnow().isoformat(),
            "token_hash": "abc123"
        }
        mock_redis_client.get_json.return_value = cached_data
        
        token = "sample.jwt.token"
        result = await service.get_cached_jwt_validation(token)
        
        assert result == cached_data

    @pytest.mark.asyncio
    async def test_get_cached_jwt_validation_expired(self, auth_cache_service, sample_jwt_validation, mock_redis_client):
        """Test retrieval of expired JWT validation."""
        service = auth_cache_service
        
        # Set token as expired
        expired_time = datetime.utcnow() - timedelta(minutes=10)
        sample_jwt_validation["exp"] = int(expired_time.timestamp())
        
        cached_data = {
            **sample_jwt_validation,
            "cached_at": datetime.utcnow().isoformat(),
            "token_hash": "abc123"
        }
        mock_redis_client.get_json.return_value = cached_data
        
        token = "sample.jwt.token"
        result = await service.get_cached_jwt_validation(token)
        
        assert result is None
        # Should delete expired token from cache
        mock_redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_user_permissions_success(self, auth_cache_service, mock_redis_client):
        """Test successful user permissions caching."""
        service = auth_cache_service
        mock_redis_client.set_json.return_value = True
        
        permissions = ["read:pets", "write:appointments"]
        result = await service.cache_user_permissions("user_123", permissions)
        
        assert result is True
        mock_redis_client.set_json.assert_called_once()
        
        # Verify cached data structure
        call_args = mock_redis_client.set_json.call_args
        cached_data = call_args[0][1]
        assert cached_data["permissions"] == permissions
        assert "cached_at" in cached_data

    @pytest.mark.asyncio
    async def test_get_cached_user_permissions_success(self, auth_cache_service, mock_redis_client):
        """Test successful retrieval of cached user permissions."""
        service = auth_cache_service
        
        permissions = ["read:pets", "write:appointments"]
        cached_data = {
            "permissions": permissions,
            "cached_at": datetime.utcnow().isoformat()
        }
        mock_redis_client.get_json.return_value = cached_data
        
        result = await service.get_cached_user_permissions("user_123")
        
        assert result == permissions

    @pytest.mark.asyncio
    async def test_cache_user_role_success(self, auth_cache_service, mock_redis_client):
        """Test successful user role caching."""
        service = auth_cache_service
        mock_redis_client.set_json.return_value = True
        
        role = "veterinarian"
        result = await service.cache_user_role("user_123", role)
        
        assert result is True
        mock_redis_client.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_user_role_success(self, auth_cache_service, mock_redis_client):
        """Test successful retrieval of cached user role."""
        service = auth_cache_service
        
        role = "veterinarian"
        cached_data = {
            "role": role,
            "cached_at": datetime.utcnow().isoformat()
        }
        mock_redis_client.get_json.return_value = cached_data
        
        result = await service.get_cached_user_role("user_123")
        
        assert result == role

    @pytest.mark.asyncio
    async def test_invalidate_user_related_cache_success(self, auth_cache_service, mock_redis_client):
        """Test successful invalidation of all user-related cache."""
        service = auth_cache_service
        mock_redis_client.delete.return_value = True
        
        result = await service.invalidate_user_related_cache("clerk_123", "user_456")
        
        assert result is True
        # Should call delete 3 times (user data, permissions, role)
        assert mock_redis_client.delete.call_count == 3

    @pytest.mark.asyncio
    async def test_invalidate_user_related_cache_partial_failure(self, auth_cache_service, mock_redis_client):
        """Test partial failure in user-related cache invalidation."""
        service = auth_cache_service
        # First call succeeds, second fails, third succeeds
        mock_redis_client.delete.side_effect = [True, False, True]
        
        result = await service.invalidate_user_related_cache("clerk_123", "user_456")
        
        assert result is False  # Should return False due to partial failure

    @pytest.mark.asyncio
    async def test_get_cache_statistics(self, auth_cache_service):
        """Test cache statistics retrieval."""
        service = auth_cache_service
        
        stats = await service.get_cache_statistics()
        
        assert "timestamp" in stats
        assert "user_cache_ttl" in stats
        assert "jwt_cache_ttl" in stats
        assert "cache_keys" in stats
        assert stats["user_cache_ttl"] == service.user_cache_ttl
        assert stats["jwt_cache_ttl"] == service.jwt_cache_ttl

    @pytest.mark.asyncio
    async def test_clear_expired_cache(self, auth_cache_service):
        """Test expired cache clearing."""
        service = auth_cache_service
        
        result = await service.clear_expired_cache()
        
        # Should return number of cleared entries (0 in this mock case)
        assert isinstance(result, int)
        assert result >= 0

    @pytest.mark.asyncio
    async def test_error_handling_in_cache_operations(self, auth_cache_service, mock_redis_client):
        """Test error handling in cache operations."""
        service = auth_cache_service
        
        # Mock Redis to raise an exception
        mock_redis_client.get_json.side_effect = Exception("Redis connection error")
        
        # Should handle errors gracefully
        result = await service.get_cached_user_data("user_123")
        assert result is None
        
        # Test error in caching
        mock_redis_client.set_json.side_effect = Exception("Redis write error")
        
        sample_user = MagicMock()
        sample_user.clerk_id = "user_123"
        
        result = await service.cache_user_data(sample_user)
        assert result is False

    @pytest.mark.asyncio
    async def test_jwt_token_hash_consistency(self, auth_cache_service):
        """Test that JWT token hashing is consistent."""
        service = auth_cache_service
        
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        hash1 = service._hash_token(token)
        hash2 = service._hash_token(token)
        
        assert hash1 == hash2
        assert len(hash1) == 32

    @pytest.mark.asyncio
    async def test_cache_ttl_configuration(self, auth_cache_service):
        """Test that cache TTL values are properly configured."""
        service = auth_cache_service
        
        # Should use configured TTL values
        assert service.user_cache_ttl > 0
        assert service.jwt_cache_ttl > 0
        
        # JWT cache TTL should typically be longer than user cache TTL
        # (though this depends on configuration)
        assert isinstance(service.user_cache_ttl, int)
        assert isinstance(service.jwt_cache_ttl, int)


class TestAuthCacheServiceIntegration:
    """Integration tests for AuthCacheService with more realistic scenarios."""

    @pytest.mark.asyncio
    async def test_full_user_cache_lifecycle(self, auth_cache_service, sample_user, mock_redis_client):
        """Test complete user cache lifecycle: cache -> retrieve -> invalidate."""
        service = auth_cache_service
        
        # Setup mock responses
        mock_redis_client.set_json.return_value = True
        mock_redis_client.delete.return_value = True
        
        # Cache user data
        cache_result = await service.cache_user_data(sample_user)
        assert cache_result is True
        
        # Setup mock for retrieval
        cached_data = {
            "clerk_id": "user_123",
            "email": "test@example.com",
            "role": "pet_owner",
            "is_active": True
        }
        mock_redis_client.get_json.return_value = cached_data
        
        # Retrieve cached data
        retrieved_data = await service.get_cached_user_data("user_123")
        assert retrieved_data == cached_data
        
        # Invalidate cache
        invalidate_result = await service.invalidate_user_cache("user_123")
        assert invalidate_result is True

    @pytest.mark.asyncio
    async def test_jwt_validation_cache_with_expiration_logic(self, auth_cache_service, mock_redis_client):
        """Test JWT validation caching with proper expiration handling."""
        service = auth_cache_service
        
        # Create JWT validation data with future expiration
        future_exp = int((datetime.utcnow() + timedelta(hours=2)).timestamp())
        jwt_data = {
            "user_id": "user_123",
            "exp": future_exp,
            "iat": int(datetime.utcnow().timestamp())
        }
        
        mock_redis_client.set_json.return_value = True
        
        # Cache JWT validation
        token = "valid.jwt.token"
        cache_result = await service.cache_jwt_validation(token, jwt_data)
        assert cache_result is True
        
        # Setup mock for retrieval with cached data
        cached_jwt_data = {
            **jwt_data,
            "cached_at": datetime.utcnow().isoformat(),
            "token_hash": service._hash_token(token)
        }
        mock_redis_client.get_json.return_value = cached_jwt_data
        
        # Retrieve should succeed (not expired)
        retrieved_data = await service.get_cached_jwt_validation(token)
        assert retrieved_data == cached_jwt_data
        
        # Now test with expired token
        past_exp = int((datetime.utcnow() - timedelta(hours=1)).timestamp())
        expired_jwt_data = {
            **cached_jwt_data,
            "exp": past_exp
        }
        mock_redis_client.get_json.return_value = expired_jwt_data
        mock_redis_client.delete.return_value = True
        
        # Retrieve should return None and delete expired token
        retrieved_data = await service.get_cached_jwt_validation(token)
        assert retrieved_data is None
        mock_redis_client.delete.assert_called()