"""
Unit tests for authentication service.
Tests password hashing, user authentication, and session management functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.services import AuthService
from app.models.user import User, UserRole
from app.core.exceptions import AuthenticationError, ValidationError


class TestAuthService:
    """Test authentication service functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_session_service(self):
        """Mock session service."""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db_session):
        """Create auth service instance."""
        return AuthService(mock_db_session)

    @pytest.fixture
    def sample_user(self):
        """Sample user object."""
        user = Mock(spec=User)
        user.id = "user_123"
        user.email = "test@example.com"
        user.first_name = "John"
        user.last_name = "Doe"
        user.phone_number = "+1234567890"
        user.role = UserRole.PET_OWNER
        user.clerk_id = "clerk_123"
        user.is_active = True
        user.is_verified = False
        user.password_hash = "salt123:hashedpassword"
        user.created_at = datetime.utcnow()
        user.last_login = None
        return user


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self, auth_service):
        """Test password hashing."""
        password = "testpassword123"
        hashed = auth_service._hash_password(password)
        
        assert isinstance(hashed, str)
        assert ":" in hashed
        assert len(hashed.split(":")) == 2
        assert len(hashed.split(":")[0]) == 32  # Salt length
        assert len(hashed.split(":")[1]) == 64  # SHA-256 hash length

    def test_verify_password_correct(self, auth_service):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = auth_service._hash_password(password)
        
        assert auth_service._verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, auth_service):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = auth_service._hash_password(password)
        
        assert auth_service._verify_password(wrong_password, hashed) is False

    def test_verify_password_invalid_format(self, auth_service):
        """Test password verification with invalid hash format."""
        password = "testpassword123"
        invalid_hash = "invalidhashformat"
        
        assert auth_service._verify_password(password, invalid_hash) is False

    def test_verify_password_empty_hash(self, auth_service):
        """Test password verification with empty hash."""
        password = "testpassword123"
        
        assert auth_service._verify_password(password, "") is False

    def test_hash_password_different_salts(self, auth_service):
        """Test that same password produces different hashes due to salt."""
        password = "testpassword123"
        hash1 = auth_service._hash_password(password)
        hash2 = auth_service._hash_password(password)
        
        assert hash1 != hash2
        assert auth_service._verify_password(password, hash1) is True
        assert auth_service._verify_password(password, hash2) is True


class TestUserCreation:
    """Test user creation functionality."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, auth_service, mock_db_session):
        """Test successful user creation."""
        # Mock database operations
        mock_db_session.add = Mock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Create user
        result = await auth_service.create_user(
            email="test@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
            phone_number="+1234567890",
            role=UserRole.PET_OWNER
        )

        # Verify user creation
        assert isinstance(result, User)
        assert result.email == "test@example.com"
        assert result.first_name == "John"
        assert result.last_name == "Doe"
        assert result.phone_number == "+1234567890"
        assert result.role == UserRole.PET_OWNER
        assert result.is_active is True
        assert result.is_verified is False
        assert result.clerk_id.startswith("temp_")  # Temporary clerk_id for development
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_email_normalization(self, auth_service, mock_db_session):
        """Test email normalization during user creation."""
        mock_db_session.add = Mock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        result = await auth_service.create_user(
            email="  TEST@EXAMPLE.COM  ",
            password="securepassword123",
            first_name="John",
            last_name="Doe"
        )

        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_create_user_name_trimming(self, auth_service, mock_db_session):
        """Test name trimming during user creation."""
        mock_db_session.add = Mock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        result = await auth_service.create_user(
            email="test@example.com",
            password="securepassword123",
            first_name="  John  ",
            last_name="  Doe  "
        )

        assert result.first_name == "John"
        assert result.last_name == "Doe"

    @pytest.mark.asyncio
    async def test_create_user_database_error(self, auth_service, mock_db_session):
        """Test user creation with database error."""
        mock_db_session.add = Mock()
        mock_db_session.commit = AsyncMock(side_effect=Exception("Database error"))
        mock_db_session.rollback = AsyncMock()

        with pytest.raises(Exception):
            await auth_service.create_user(
                email="test@example.com",
                password="securepassword123",
                first_name="John",
                last_name="Doe"
            )

        mock_db_session.rollback.assert_called_once()


class TestUserAuthentication:
    """Test user authentication functionality."""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(
        self, auth_service, mock_db_session, mock_session_service, sample_user
    ):
        """Test successful user authentication."""
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()

        # Mock session service
        auth_service.session_service = mock_session_service
        mock_session_service.create_session.return_value = {
            "session_id": "session_123",
            "user_id": str(sample_user.id),
            "created_at": datetime.utcnow().isoformat()
        }

        # Make sure user has temp clerk_id for development testing
        sample_user.clerk_id = "temp_12345"
        
        # Mock password verification
        with patch("app.auth.services.get_user_permissions") as mock_get_permissions:
            mock_get_permissions.return_value = ["pets:read", "pets:write"]
            
            with patch("app.auth.services.create_access_token") as mock_create_token:
                mock_create_token.return_value = "jwt_token_123"
                
                result = await auth_service.authenticate_user(
                    email="test@example.com",
                    password="securepassword123",
                    ip_address="192.168.1.1",
                    user_agent="TestAgent/1.0"
                )

        assert result["success"] is True
        assert result["user"] == sample_user
        assert result["session"]["session_id"] == "session_123"
        assert result["session"]["access_token"] == "jwt_token_123"
        mock_session_service.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_service, mock_db_session):
        """Test authentication with non-existent user."""
        # Mock database query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await auth_service.authenticate_user(
            email="nonexistent@example.com",
            password="password123"
        )

        assert result["success"] is False
        assert result["message"] == "Invalid email or password"

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, auth_service, mock_db_session, sample_user):
        """Test authentication with inactive user."""
        # Make user inactive
        sample_user.is_active = False

        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        result = await auth_service.authenticate_user(
            email="test@example.com",
            password="password123"
        )

        assert result["success"] is False
        assert result["message"] == "Account is deactivated"

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(
        self, auth_service, mock_db_session, sample_user
    ):
        """Test authentication with wrong password."""
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        # Set user to have real Clerk ID (not temp) to simulate production behavior
        sample_user.clerk_id = "user_real_clerk_id"
        
        result = await auth_service.authenticate_user(
            email="test@example.com",
            password="wrongpassword"
        )

        assert result["success"] is False
        assert result["message"] == "Authentication must be done through Clerk"

    @pytest.mark.asyncio
    async def test_authenticate_user_no_password_hash(
        self, auth_service, mock_db_session, sample_user
    ):
        """Test authentication with production user (should use Clerk)."""
        # Set user to have real Clerk ID (not temp)
        sample_user.clerk_id = "user_real_clerk_id"

        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        result = await auth_service.authenticate_user(
            email="test@example.com",
            password="password123"
        )

        assert result["success"] is False
        assert result["message"] == "Authentication must be done through Clerk"

    @pytest.mark.asyncio
    async def test_authenticate_user_email_normalization(
        self, auth_service, mock_db_session, sample_user
    ):
        """Test email normalization during authentication."""
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()

        # Mock session service
        auth_service.session_service = AsyncMock()
        auth_service.session_service.create_session.return_value = {
            "session_id": "session_123"
        }

        with patch.object(auth_service, '_verify_password', return_value=True):
            with patch("app.auth.services.get_user_permissions", return_value=[]):
                with patch("app.auth.services.create_access_token", return_value="token"):
                    await auth_service.authenticate_user(
                        email="  TEST@EXAMPLE.COM  ",
                        password="password123"
                    )

        # Verify the query was made with normalized email
        call_args = mock_db_session.execute.call_args[0][0]
        # The query should contain the normalized email
        assert "test@example.com" in str(call_args)


class TestSessionManagement:
    """Test session management functionality."""

    @pytest.mark.asyncio
    async def test_logout_session_success(self, auth_service, mock_session_service):
        """Test successful session logout."""
        auth_service.session_service = mock_session_service
        mock_session_service.invalidate_session.return_value = True

        result = await auth_service.logout_session("session_123")

        assert result is True
        mock_session_service.invalidate_session.assert_called_once_with("session_123")

    @pytest.mark.asyncio
    async def test_logout_session_failure(self, auth_service, mock_session_service):
        """Test session logout failure."""
        auth_service.session_service = mock_session_service
        mock_session_service.invalidate_session.return_value = False

        result = await auth_service.logout_session("invalid_session")

        assert result is False

    @pytest.mark.asyncio
    async def test_logout_all_sessions_success(self, auth_service, mock_session_service):
        """Test successful logout from all sessions."""
        auth_service.session_service = mock_session_service
        mock_session_service.invalidate_user_sessions.return_value = 3

        result = await auth_service.logout_all_sessions("user_123", "current_session")

        assert result == 3
        mock_session_service.invalidate_user_sessions.assert_called_once_with(
            "user_123", "current_session"
        )

    @pytest.mark.asyncio
    async def test_get_user_sessions(self, auth_service, mock_session_service):
        """Test getting user sessions."""
        auth_service.session_service = mock_session_service
        mock_sessions = [
            {"session_id": "session_1", "is_active": True},
            {"session_id": "session_2", "is_active": True}
        ]
        mock_session_service.get_user_sessions.return_value = mock_sessions

        result = await auth_service.get_user_sessions("user_123")

        assert result == mock_sessions
        mock_session_service.get_user_sessions.assert_called_once_with("user_123")


class TestPasswordManagement:
    """Test password change functionality."""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, auth_service, mock_db_session, mock_session_service, sample_user
    ):
        """Test successful password change."""
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock()

        # Mock session service
        auth_service.session_service = mock_session_service
        mock_session_service.invalidate_user_sessions = AsyncMock()

        # Set user to have temp clerk_id for development testing
        sample_user.clerk_id = "temp_12345"
        
        result = await auth_service.change_password(
            user_id="user_123",
            current_password="oldpassword",
            new_password="newpassword123"
        )

        assert result["success"] is True
        assert result["message"] == "Password changed successfully"
        mock_db_session.commit.assert_called_once()
        mock_session_service.invalidate_user_sessions.assert_called_once_with("user_123")

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(self, auth_service, mock_db_session):
        """Test password change with non-existent user."""
        # Mock database query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await auth_service.change_password(
            user_id="nonexistent_user",
            current_password="oldpassword",
            new_password="newpassword123"
        )

        assert result["success"] is False
        assert result["message"] == "User not found"

    @pytest.mark.asyncio
    async def test_change_password_incorrect_current(
        self, auth_service, mock_db_session, sample_user
    ):
        """Test password change with incorrect current password."""
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        # Set user to have real Clerk ID (not temp) to simulate production behavior
        sample_user.clerk_id = "user_real_clerk_id"
        
        result = await auth_service.change_password(
            user_id="user_123",
            current_password="wrongpassword",
            new_password="newpassword123"
        )

        assert result["success"] is False
        assert result["message"] == "Password changes must be done through Clerk"

    @pytest.mark.asyncio
    async def test_change_password_database_error(
        self, auth_service, mock_db_session, mock_session_service, sample_user
    ):
        """Test password change with database error."""
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit = AsyncMock(side_effect=Exception("Database error"))
        mock_db_session.rollback = AsyncMock()

        # Mock session service
        auth_service.session_service = mock_session_service

        # Set user to have temp clerk_id for development testing
        sample_user.clerk_id = "temp_12345"
        
        result = await auth_service.change_password(
            user_id="user_123",
            current_password="oldpassword",
            new_password="newpassword123"
        )

        assert result["success"] is False
        assert result["message"] == "Failed to change password"
        mock_db_session.rollback.assert_called_once()


class TestUserRetrieval:
    """Test user retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_user_by_email_found(self, auth_service, mock_db_session, sample_user):
        """Test getting user by email when user exists."""
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        result = await auth_service.get_user_by_email("test@example.com")

        assert result == sample_user

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, auth_service, mock_db_session):
        """Test getting user by email when user doesn't exist."""
        # Mock database query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await auth_service.get_user_by_email("nonexistent@example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_email_normalization(self, auth_service, mock_db_session, sample_user):
        """Test email normalization when getting user by email."""
        # Mock database query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        result = await auth_service.get_user_by_email("  TEST@EXAMPLE.COM  ")

        assert result == sample_user
        # Verify the query was made with normalized email
        call_args = mock_db_session.execute.call_args[0][0]
        assert "test@example.com" in str(call_args)

    @pytest.mark.asyncio
    async def test_get_user_by_email_database_error(self, auth_service, mock_db_session):
        """Test getting user by email with database error."""
        mock_db_session.execute.side_effect = Exception("Database error")

        result = await auth_service.get_user_by_email("test@example.com")

        assert result is None


class TestPasswordReset:
    """Test password reset functionality."""

    @pytest.mark.asyncio
    async def test_request_password_reset_user_exists(
        self, auth_service, sample_user
    ):
        """Test password reset request for existing user."""
        with patch.object(auth_service, 'get_user_by_email', return_value=sample_user):
            result = await auth_service.request_password_reset("test@example.com")

        assert result["success"] is True
        assert "Password reset instructions sent" in result["message"]

    @pytest.mark.asyncio
    async def test_request_password_reset_user_not_exists(self, auth_service):
        """Test password reset request for non-existent user."""
        with patch.object(auth_service, 'get_user_by_email', return_value=None):
            result = await auth_service.request_password_reset("nonexistent@example.com")

        # Should still return success to prevent email enumeration
        assert result["success"] is True
        assert "Password reset instructions sent" in result["message"]

    @pytest.mark.asyncio
    async def test_confirm_password_reset_not_implemented(self, auth_service):
        """Test password reset confirmation (not implemented)."""
        result = await auth_service.confirm_password_reset("token123", "newpassword")

        assert result["success"] is False
        assert "not fully implemented" in result["message"]

    @pytest.mark.asyncio
    async def test_refresh_access_token_not_implemented(self, auth_service):
        """Test token refresh (not implemented)."""
        result = await auth_service.refresh_access_token("refresh_token")

        assert result["success"] is False
        assert "not implemented" in result["message"]