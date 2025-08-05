"""
Integration tests for authentication caching functionality.
Tests the complete authentication flow with Redis caching enabled.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.services.auth_cache_service import AuthCacheService, get_auth_cache_service
from app.services.clerk_service import ClerkService, get_clerk_service
from app.services.user_sync_service import UserSyncService
from app.models.user import User, UserRole
from app.core.redis import redis_client


@pytest.fixture
def mock_redis_for_integration():
    """Mock Redis client for integration testing."""
    mock_redis = AsyncMock()
    
    # Default return values
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.exists.return_value = False
    mock_redis.get_json.return_value = None
    mock_redis.set_json.return_value = True
    
    return mock_redis


@pytest.fixture
def mock_clerk_api():
    """Mock Clerk API responses."""
    return {
        "user_data": {
            "id": "user_test123",
            "email_addresses": [
                {
                    "id": "email_123",
                    "email_address": "test@example.com",
                    "verification": None,
                    "linked_to": None
                }
            ],
            "phone_numbers": [],
            "first_name": "Test",
            "last_name": "User",
            "image_url": None,
            "has_image": False,
            "public_metadata": {"role": "pet_owner"},
            "private_metadata": {},
            "unsafe_metadata": {},
            "created_at": int(datetime.utcnow().timestamp() * 1000),
            "updated_at": int(datetime.utcnow().timestamp() * 1000),
            "last_sign_in_at": None,
            "banned": False,
            "locked": False,
            "lockout_expires_in_seconds": None,
            "verification_attempts_remaining": 3
        },
        "jwt_payload": {
            "sub": "user_test123",
            "email": "test@example.com",
            "public_metadata": {"role": "pet_owner"},
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp()),
            "iss": "https://clerk.dev",
            "sid": "sess_123"
        }
    }


@pytest.fixture
def test_user():
    """Create a test user for testing."""
    return User(
        id=1,
        clerk_id="user_test123",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        role=UserRole.PET_OWNER,
        is_active=True,
        is_verified=True
    )


class TestAuthenticationCachingIntegration:
    """Integration tests for authentication caching."""

    @pytest.mark.asyncio
    async def test_jwt_validation_with_caching(self, mock_redis_for_integration, mock_clerk_api):
        """Test JWT validation with caching enabled."""
        
        with patch('app.services.clerk_service.get_auth_cache_service') as mock_get_cache:
            with patch('app.services.clerk_service.jwt.decode') as mock_jwt_decode:
                with patch('app.services.clerk_service.jwt.get_unverified_header') as mock_header:
                    with patch.object(ClerkService, '_get_public_key') as mock_get_key:
                        
                        # Setup cache service mock
                        cache_service = AuthCacheService()
                        cache_service.redis = mock_redis_for_integration
                        mock_get_cache.return_value = cache_service
                        
                        # Setup mocks
                        mock_header.return_value = {"kid": "key_123"}
                        mock_get_key.return_value = "mock_public_key"
                        mock_jwt_decode.return_value = mock_clerk_api["jwt_payload"]
                        
                        # First call - should hit Clerk API and cache result
                        clerk_service = ClerkService()
                        token = "test.jwt.token"
                        
                        result1 = await clerk_service.verify_jwt_token(token)
                        
                        # Verify result
                        assert result1["clerk_id"] == "user_test123"
                        assert result1["email"] == "test@example.com"
                        
                        # Verify caching was attempted
                        mock_redis_for_integration.set_json.assert_called()
                        
                        # Setup cache hit for second call
                        cached_result = {
                            **result1,
                            "cached_at": datetime.utcnow().isoformat(),
                            "token_hash": "abc123"
                        }
                        mock_redis_for_integration.get_json.return_value = cached_result
                        
                        # Second call - should use cache
                        result2 = await clerk_service.verify_jwt_token(token)
                        
                        # Should get cached result
                        assert result2 == cached_result
                        
                        # JWT decode should only be called once (first time)
                        assert mock_jwt_decode.call_count == 1

    @pytest.mark.asyncio
    async def test_user_data_caching_in_sync_flow(self, mock_redis_for_integration, mock_clerk_api):
        """Test user data caching during user synchronization."""
        
        with patch('app.services.auth_cache_service.redis_client', mock_redis_for_integration):
            with patch('app.services.user_sync_service.get_auth_cache_service') as mock_get_cache:
                with patch('app.services.user_sync_service.UserSyncService.get_user_by_clerk_id') as mock_get_user:
                    with patch('app.services.user_sync_service.UserSyncService.create_user_from_clerk') as mock_create:
                        
                        # Setup cache service mock
                        cache_service = AuthCacheService()
                        cache_service.redis = mock_redis_for_integration
                        mock_get_cache.return_value = cache_service
                        
                        # Mock database operations
                        mock_get_user.return_value = None  # User doesn't exist
                        
                        # Create mock user
                        mock_user = User(
                            id=1,
                            clerk_id="user_test123",
                            email="test@example.com",
                            first_name="Test",
                            last_name="User",
                            role=UserRole.PET_OWNER,
                            is_active=True,
                            is_verified=True
                        )
                        mock_create.return_value = mock_user
                        
                        # Create user sync service with mock db
                        mock_db = AsyncMock()
                        user_sync_service = UserSyncService(mock_db)
                        
                        # Create ClerkUser from mock data
                        from app.schemas.clerk_schemas import ClerkUser
                        clerk_user = ClerkUser(**mock_clerk_api["user_data"])
                        
                        # Sync user (should create new user and cache it)
                        sync_response = await user_sync_service.sync_user_data(clerk_user)
                        
                        assert sync_response.success is True
                        assert sync_response.action == "created"
                        
                        # Verify caching was called
                        mock_redis_for_integration.set_json.assert_called()

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_user_update(self, mock_redis_for_integration, mock_clerk_api, test_user):
        """Test cache invalidation when user is updated."""
        
        with patch('app.services.auth_cache_service.redis_client', mock_redis_for_integration):
            with patch('app.services.user_sync_service.get_auth_cache_service') as mock_get_cache:
                with patch('app.services.user_sync_service.UserSyncService.get_user_by_clerk_id') as mock_get_user:
                    with patch('app.services.user_sync_service.UserSyncService.update_user_from_clerk') as mock_update:
                        
                        # Setup cache service mock
                        cache_service = AuthCacheService()
                        cache_service.redis = mock_redis_for_integration
                        mock_get_cache.return_value = cache_service
                        
                        # Mock database operations
                        mock_get_user.return_value = test_user  # User exists
                        
                        # Create updated user
                        updated_user = User(
                            id=1,
                            clerk_id="user_test123",
                            email="test@example.com",
                            first_name="Updated",
                            last_name="User",
                            role=UserRole.PET_OWNER,
                            is_active=True,
                            is_verified=True
                        )
                        mock_update.return_value = updated_user
                        
                        # Create user sync service with mock db
                        mock_db = AsyncMock()
                        user_sync_service = UserSyncService(mock_db)
                        
                        # Update user data in Clerk mock
                        updated_clerk_data = mock_clerk_api["user_data"].copy()
                        updated_clerk_data["first_name"] = "Updated"
                        updated_clerk_data["updated_at"] = int((datetime.utcnow() + timedelta(minutes=1)).timestamp() * 1000)
                        
                        from app.schemas.clerk_schemas import ClerkUser
                        clerk_user = ClerkUser(**updated_clerk_data)
                        
                        # Update user (should invalidate cache and create new cache entry)
                        sync_response = await user_sync_service.sync_user_data(clerk_user)
                        
                        assert sync_response.success is True
                        
                        # Verify new cache entry was created
                        mock_redis_for_integration.set_json.assert_called()

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_user_deletion(self, mock_redis_for_integration, test_user):
        """Test cache invalidation when user is deleted."""
        
        with patch('app.services.auth_cache_service.redis_client', mock_redis_for_integration):
            with patch('app.services.user_sync_service.get_auth_cache_service') as mock_get_cache:
                with patch('app.services.user_sync_service.UserSyncService.get_user_by_clerk_id') as mock_get_user:
                    
                    # Setup cache service mock
                    cache_service = AuthCacheService()
                    cache_service.redis = mock_redis_for_integration
                    mock_get_cache.return_value = cache_service
                    
                    # Mock database operations
                    mock_get_user.return_value = test_user
                    
                    # Create user sync service with mock db
                    mock_db = AsyncMock()
                    user_sync_service = UserSyncService(mock_db)
                    
                    # Delete user
                    await user_sync_service.handle_user_deletion("user_test123")
                    
                    # Verify cache invalidation was called
                    mock_redis_for_integration.delete.assert_called()
                    
                    # Should have called delete multiple times for different cache keys
                    delete_calls = mock_redis_for_integration.delete.call_args_list
                    assert len(delete_calls) >= 3  # user data, permissions, role

    @pytest.mark.asyncio
    async def test_authentication_flow_with_cache_hit(self, mock_redis_for_integration, mock_clerk_api, test_user):
        """Test complete authentication flow with cache hit."""
        
        with patch('app.services.auth_cache_service.redis_client', mock_redis_for_integration):
            with patch('app.api.deps.get_auth_cache_service') as mock_get_cache:
                
                # Setup cache service mock
                cache_service = AuthCacheService()
                cache_service.redis = mock_redis_for_integration
                mock_get_cache.return_value = cache_service
                
                # Setup cached user data
                cached_user_data = {
                    "id": str(test_user.id),
                    "clerk_id": "user_test123",
                    "email": "test@example.com",
                    "first_name": "Test",
                    "last_name": "User",
                    "role": "pet_owner",
                    "is_active": True,
                    "is_verified": True,
                    "cached_at": datetime.utcnow().isoformat()
                }
                
                # Mock cache hit
                mock_redis_for_integration.get_json.return_value = cached_user_data
                
                # Import and test the dependency
                from app.api.deps import sync_clerk_user, verify_clerk_token
                
                # Mock token verification
                token_data = {
                    "clerk_id": "user_test123",
                    "email": "test@example.com",
                    "role": "pet_owner"
                }
                
                with patch('app.api.deps.verify_clerk_token') as mock_verify:
                    mock_verify.return_value = token_data
                    
                    # Mock the database session and user lookup
                    mock_db = AsyncMock()
                    
                    with patch('app.api.deps.UserSyncService') as mock_sync_service_class:
                        mock_sync_service = AsyncMock()
                        mock_sync_service_class.return_value = mock_sync_service
                        mock_sync_service.get_user_by_clerk_id.return_value = test_user
                        
                        # This would normally be called by FastAPI dependency injection
                        # Here we simulate it directly
                        result_user = await sync_clerk_user(token_data, mock_db)
                        
                        assert result_user.clerk_id == "user_test123"
                        assert result_user.email == "test@example.com"
                        
                        # Verify cache was checked
                        mock_redis_for_integration.get_json.assert_called()

    @pytest.mark.asyncio
    async def test_jwt_cache_expiration_handling(self, mock_redis_for_integration):
        """Test handling of expired JWT tokens in cache."""
        
        with patch('app.services.auth_cache_service.redis_client', mock_redis_for_integration):
            
            cache_service = AuthCacheService()
            
            # Setup expired JWT data in cache
            expired_jwt_data = {
                "user_id": "user_123",
                "clerk_id": "user_123",
                "exp": int((datetime.utcnow() - timedelta(hours=1)).timestamp()),  # Expired
                "cached_at": datetime.utcnow().isoformat(),
                "token_hash": "abc123"
            }
            
            mock_redis_for_integration.get_json.return_value = expired_jwt_data
            mock_redis_for_integration.delete.return_value = True
            
            # Try to get cached JWT validation
            token = "expired.jwt.token"
            result = await cache_service.get_cached_jwt_validation(token)
            
            # Should return None for expired token
            assert result is None
            
            # Should have deleted the expired token from cache
            mock_redis_for_integration.delete.assert_called()

    @pytest.mark.asyncio
    async def test_cache_performance_optimization(self, mock_redis_for_integration, mock_clerk_api):
        """Test that caching provides performance optimization."""
        
        with patch('app.services.clerk_service.get_auth_cache_service') as mock_get_cache:
            with patch('app.services.clerk_service.jwt.decode') as mock_jwt_decode:
                with patch('app.services.clerk_service.jwt.get_unverified_header') as mock_header:
                    with patch.object(ClerkService, '_get_public_key') as mock_get_key:
                        
                        # Setup cache service mock
                        cache_service = AuthCacheService()
                        cache_service.redis = mock_redis_for_integration
                        mock_get_cache.return_value = cache_service
                        
                        # Setup mocks for first call
                        mock_header.return_value = {"kid": "key_123"}
                        mock_get_key.return_value = "mock_public_key"
                        mock_jwt_decode.return_value = mock_clerk_api["jwt_payload"]
                        
                        clerk_service = ClerkService()
                        token = "performance.test.token"
                        
                        # First call - should hit Clerk API
                        result1 = await clerk_service.verify_jwt_token(token)
                        
                        # Setup cache hit for subsequent calls
                        cached_result = {
                            **result1,
                            "cached_at": datetime.utcnow().isoformat(),
                            "token_hash": cache_service._hash_token(token)
                        }
                        mock_redis_for_integration.get_json.return_value = cached_result
                        
                        # Multiple subsequent calls
                        for i in range(5):
                            result = await clerk_service.verify_jwt_token(token)
                            # Just check key fields instead of exact match due to timestamp differences
                            assert result["clerk_id"] == cached_result["clerk_id"]
                            assert result["email"] == cached_result["email"]
                        
                        # JWT decode should only be called once (first time)
                        assert mock_jwt_decode.call_count == 1
                        
                        # Cache get should be called multiple times
                        assert mock_redis_for_integration.get_json.call_count >= 5

    @pytest.mark.asyncio
    async def test_cache_statistics_collection(self, mock_redis_for_integration):
        """Test cache statistics collection functionality."""
        
        with patch('app.services.auth_cache_service.redis_client', mock_redis_for_integration):
            
            cache_service = AuthCacheService()
            
            # Get cache statistics
            stats = await cache_service.get_cache_statistics()
            
            # Verify statistics structure
            assert "timestamp" in stats
            assert "user_cache_ttl" in stats
            assert "jwt_cache_ttl" in stats
            assert "cache_keys" in stats
            
            # Verify TTL values
            assert stats["user_cache_ttl"] == cache_service.user_cache_ttl
            assert stats["jwt_cache_ttl"] == cache_service.jwt_cache_ttl
            
            # Verify cache keys structure
            cache_keys = stats["cache_keys"]
            assert "user_data" in cache_keys
            assert "jwt_validation" in cache_keys
            assert "permissions" in cache_keys
            assert "roles" in cache_keys

    @pytest.mark.asyncio
    async def test_bulk_cache_operations(self, mock_redis_for_integration):
        """Test bulk cache operations for user-related data."""
        
        with patch('app.services.auth_cache_service.redis_client', mock_redis_for_integration):
            
            cache_service = AuthCacheService()
            mock_redis_for_integration.delete.return_value = True
            
            # Test bulk invalidation
            result = await cache_service.invalidate_user_related_cache("clerk_123", "user_456")
            
            assert result is True
            
            # Should have called delete for user data, permissions, and role
            assert mock_redis_for_integration.delete.call_count == 3
            
            # Verify the cache keys that were deleted
            delete_calls = mock_redis_for_integration.delete.call_args_list
            deleted_keys = [call[0][0] for call in delete_calls]
            
            assert "auth:user:clerk_123" in deleted_keys
            assert "auth:permissions:user_456" in deleted_keys
            assert "auth:role:user_456" in deleted_keys

    @pytest.mark.asyncio
    async def test_cache_error_handling_in_auth_flow(self, mock_redis_for_integration, mock_clerk_api, test_user):
        """Test that authentication flow continues to work when cache fails."""
        
        with patch('app.services.auth_cache_service.redis_client', mock_redis_for_integration):
            with patch('app.services.user_sync_service.get_auth_cache_service') as mock_get_cache:
                with patch('app.services.user_sync_service.UserSyncService.get_user_by_clerk_id') as mock_get_user:
                    with patch('app.services.user_sync_service.UserSyncService.create_user_from_clerk') as mock_create:
                        
                        # Setup cache service that fails
                        cache_service = AuthCacheService()
                        cache_service.redis = mock_redis_for_integration
                        mock_get_cache.return_value = cache_service
                        
                        # Make cache operations fail
                        mock_redis_for_integration.get_json.side_effect = Exception("Redis connection error")
                        mock_redis_for_integration.set_json.side_effect = Exception("Redis write error")
                        
                        # Mock database operations
                        mock_get_user.return_value = None  # User doesn't exist
                        mock_create.return_value = test_user
                        
                        # Create user sync service with mock db
                        mock_db = AsyncMock()
                        user_sync_service = UserSyncService(mock_db)
                        
                        # Create ClerkUser from mock data
                        from app.schemas.clerk_schemas import ClerkUser
                        clerk_user = ClerkUser(**mock_clerk_api["user_data"])
                        
                        # Sync should still work despite cache failures
                        sync_response = await user_sync_service.sync_user_data(clerk_user)
                        
                        # Should succeed despite cache errors
                        assert sync_response.success is True
                        
                        # Cache operations should have been attempted but failed gracefully
                        assert mock_redis_for_integration.get_json.called
                        assert mock_redis_for_integration.set_json.called