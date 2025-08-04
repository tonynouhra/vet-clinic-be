"""
Unit tests for Clerk service.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import jwt
from datetime import datetime, timedelta

from app.services.clerk_service import ClerkService, ClerkUser
from app.core.exceptions import AuthenticationError


class TestClerkUser:
    """Test ClerkUser data class."""
    
    def test_clerk_user_initialization(self):
        """Test ClerkUser initialization with data."""
        data = {
            "id": "user_123",
            "email_addresses": [{"email_address": "test@example.com", "primary": True}],
            "first_name": "John",
            "last_name": "Doe",
            "public_metadata": {"role": "veterinarian"}
        }
        
        user = ClerkUser(data)
        
        assert user.id == "user_123"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.role == "veterinarian"
    
    def test_primary_email_property(self):
        """Test primary email extraction."""
        data = {
            "email_addresses": [
                {"email_address": "test@example.com", "primary": True},
                {"email_address": "secondary@example.com", "primary": False}
            ]
        }
        
        user = ClerkUser(data)
        assert user.primary_email == "test@example.com"
    
    def test_primary_email_fallback(self):
        """Test primary email fallback to first email."""
        data = {
            "email_addresses": [
                {"email_address": "first@example.com"},
                {"email_address": "second@example.com"}
            ]
        }
        
        user = ClerkUser(data)
        assert user.primary_email == "first@example.com"
    
    def test_role_default(self):
        """Test default role when not specified."""
        data = {"public_metadata": {}}
        
        user = ClerkUser(data)
        assert user.role == "pet_owner"


class TestClerkService:
    """Test ClerkService functionality."""
    
    @pytest.fixture
    def clerk_service(self):
        """Create ClerkService instance for testing."""
        return ClerkService()
    
    @pytest.mark.asyncio
    async def test_verify_jwt_token_success(self, clerk_service):
        """Test successful JWT token verification."""
        # Mock JWT token payload
        token_payload = {
            "sub": "user_123",
            "email": "test@example.com",
            "public_metadata": {"role": "veterinarian"},
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.utcnow().timestamp()),
            "sid": "session_123"
        }
        
        # Mock JWT verification
        with patch('jwt.get_unverified_header') as mock_header, \
             patch('jwt.decode') as mock_decode, \
             patch.object(clerk_service, '_get_public_key') as mock_key:
            
            mock_header.return_value = {"kid": "key_123"}
            mock_decode.return_value = token_payload
            mock_key.return_value = "mock_public_key"
            
            result = await clerk_service.verify_jwt_token("mock_token")
            
            assert result["user_id"] == "user_123"
            assert result["email"] == "test@example.com"
            assert result["role"] == "veterinarian"
            assert result["session_id"] == "session_123"
    
    @pytest.mark.asyncio
    async def test_verify_jwt_token_expired(self, clerk_service):
        """Test JWT token verification with expired token."""
        with patch('jwt.get_unverified_header') as mock_header, \
             patch('jwt.decode') as mock_decode, \
             patch.object(clerk_service, '_get_public_key') as mock_key:
            
            mock_header.return_value = {"kid": "key_123"}
            mock_decode.side_effect = jwt.ExpiredSignatureError("Token expired")
            mock_key.return_value = "mock_public_key"
            
            with pytest.raises(AuthenticationError, match="Token has expired"):
                await clerk_service.verify_jwt_token("expired_token")
    
    @pytest.mark.asyncio
    async def test_verify_jwt_token_invalid(self, clerk_service):
        """Test JWT token verification with invalid token."""
        with patch('jwt.get_unverified_header') as mock_header, \
             patch('jwt.decode') as mock_decode, \
             patch.object(clerk_service, '_get_public_key') as mock_key:
            
            mock_header.return_value = {"kid": "key_123"}
            mock_decode.side_effect = jwt.InvalidTokenError("Invalid token")
            mock_key.return_value = "mock_public_key"
            
            with pytest.raises(AuthenticationError, match="Invalid token"):
                await clerk_service.verify_jwt_token("invalid_token")
    
    @pytest.mark.asyncio
    async def test_get_user_by_clerk_id_success(self, clerk_service):
        """Test successful user retrieval by Clerk ID."""
        mock_user_data = {
            "id": "user_123",
            "email_addresses": [{"email_address": "test@example.com"}],
            "first_name": "John",
            "last_name": "Doe",
            "public_metadata": {"role": "veterinarian"}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_user_data
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            user = await clerk_service.get_user_by_clerk_id("user_123")
            
            assert isinstance(user, ClerkUser)
            assert user.id == "user_123"
            assert user.first_name == "John"
            assert user.role == "veterinarian"
    
    @pytest.mark.asyncio
    async def test_get_user_by_clerk_id_not_found(self, clerk_service):
        """Test user retrieval with non-existent user."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            with pytest.raises(AuthenticationError, match="User not found"):
                await clerk_service.get_user_by_clerk_id("nonexistent_user")
    
    @pytest.mark.asyncio
    @patch('app.core.config.get_settings')
    async def test_create_user_session_development(self, mock_settings, clerk_service):
        """Test development user session creation."""
        mock_settings.return_value.ENVIRONMENT = "development"
        mock_settings.return_value.JWT_SECRET_KEY = "test_secret"
        
        mock_user_data = [{
            "id": "user_123",
            "email_addresses": [{"email_address": "test@example.com"}],
            "first_name": "John",
            "public_metadata": {"role": "veterinarian"}
        }]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_user_data
            
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await clerk_service.create_user_session("test@example.com", "password")
            
            assert "token" in result
            assert "user" in result
            assert result["user"]["email"] == "test@example.com"
            assert result["user"]["role"] == "veterinarian"
    
    @pytest.mark.asyncio
    @patch('app.core.config.get_settings')
    async def test_create_user_session_production_blocked(self, mock_settings, clerk_service):
        """Test that development login is blocked in production."""
        mock_settings.return_value.ENVIRONMENT = "production"
        
        with pytest.raises(AuthenticationError, match="Development login not available"):
            await clerk_service.create_user_session("test@example.com", "password")
    
    def test_validate_webhook_signature_success(self, clerk_service):
        """Test successful webhook signature validation."""
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.CLERK_WEBHOOK_SECRET = "test_secret"
            
            payload = b'{"test": "data"}'
            # This would be the actual signature in a real scenario
            signature = "mock_signature"
            
            with patch('hmac.compare_digest') as mock_compare:
                mock_compare.return_value = True
                
                result = clerk_service.validate_webhook_signature(payload, signature)
                assert result is True
    
    def test_validate_webhook_signature_no_secret(self, clerk_service):
        """Test webhook signature validation without secret."""
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.CLERK_WEBHOOK_SECRET = None
            
            result = clerk_service.validate_webhook_signature(b"payload", "signature")
            assert result is False